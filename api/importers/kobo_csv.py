import csv
import hashlib
import io
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import DistributionPoint, ImportBatch, User
from api.normalization import clean_text, normalize_identifier
from api.schemas import RecordCreate
from api.services import create_record, duplicate_check


@dataclass
class RejectedRow:
    row_number: int
    household_uid: str
    serial_number: str
    reason: str


@dataclass
class ImportResult:
    total_rows: int = 0
    inserted_rows: int = 0
    skipped_rows: int = 0
    rejected_rows: int = 0
    source_sha256: str = ""
    dry_run: bool = True
    rejects: list[RejectedRow] = field(default_factory=list)
    unknown_distribution_labels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["rejects"] = [asdict(item) for item in self.rejects]
        return data


def normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def parse_point_mapping(raw: bytes | None) -> dict[str, str]:
    """Return normalized legacy label to canonical point code."""
    if not raw:
        return {}
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    required = {"source_label", "point_code"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("Mapping CSV requires source_label and point_code columns")
    mapping: dict[str, str] = {}
    for row in reader:
        source = normalize_label(row.get("source_label", ""))
        code = (row.get("point_code") or "").strip().upper()
        if source and code:
            mapping[source] = code
    return mapping


def _bool(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"1", "yes", "true", "accepted", "agree"}


def _float(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def _int(value: str | None) -> int | None:
    try:
        return int(float(value)) if value not in (None, "") else None
    except ValueError:
        return None


def _date(value: str | None) -> date:
    if not value:
        raise ValueError("Date of distribution is missing")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def _payload(row: dict[str, str], point_id: str) -> RecordCreate:
    receiver_type = clean_text(row.get("Stove received by;")) or "Household Head"
    head_name = clean_text(row.get("Name of the household head")) or ""
    receiver_name = clean_text(row.get("Name of the receiver"))
    if receiver_type.casefold() == "household head":
        receiver_name = receiver_name or head_name
    return RecordCreate(
        household_uid=row.get("HH ID", ""),
        household_head_name=head_name,
        household_size=_int(row.get("Household Size")) or 0,
        phone_number=clean_text(row.get("Telephone number")) or "",
        district=clean_text(row.get("District")) or "Ntungamo",
        subcounty=clean_text(row.get("Sub-county")) or "",
        parish=clean_text(row.get("Parish")) or "",
        village=clean_text(row.get("Village")) or "",
        latitude=_float(row.get("_GPS Coordinates_latitude")),
        longitude=_float(row.get("_GPS Coordinates_longitude")),
        altitude_m=_float(row.get("_GPS Coordinates_altitude")),
        gps_precision_m=_float(row.get("_GPS Coordinates_precision")),
        existing_stove_type_1=clean_text(row.get("Existing stove size")),
        fuel_type=clean_text(row.get("Fuel type used")),
        fuel_amount_per_week=clean_text(row.get("Amount of fuel used per week")),
        serial_number=row.get("Serial number", ""),
        stove_size=clean_text(row.get("Stove size")) or "Unspecified",
        distribution_point_id=point_id,
        distributed_on=_date(row.get("Date of distribution")),
        receiver_type=receiver_type,
        receiver_name=receiver_name,
        receiver_relationship=clean_text(row.get("Relationship to the household head?")),
        carbon_waiver_accepted=_bool(
            row.get(
                "I confirm that I received the project ICS (GS13031) from Pro Sphera free "
                "of charge due to carbon finance. I agree to use the project ICS and "
                "unconditionally transfer all carbon credits generated from its use to Pro Sphera."
            )
        ),
        conditions_accepted=_bool(
            row.get(
                "I agree to use the project ICS only for my householdâ€™s personal use, allow Pro "
                "Sphera weekly access to verify its use, and return it to Pro Sphera if damaged or "
                "malfunctioning or call +256782401544. I will not dispose of or transfer the ICS "
                "to another user. I understand that the ICS reduces firewood use, household "
                "costs, smoke exposure, and pressure on forests."
            )
        ),
        ambassador_name=clean_text(row.get("Ambassador")) or "Unknown",
        legacy_source="kobo",
        legacy_record_id=clean_text(row.get("_id")),
        legacy_uuid=clean_text(row.get("_uuid")),
        legacy_photo_url=clean_text(row.get("Take a picture_URL")),
    )


def import_kobo_csv(
    db: Session,
    *,
    csv_bytes: bytes,
    source_filename: str,
    actor: User,
    point_mapping: dict[str, str],
    commit: bool = False,
) -> ImportResult:
    digest = hashlib.sha256(csv_bytes).hexdigest()
    result = ImportResult(source_sha256=digest, dry_run=not commit)
    existing_batch = db.scalar(select(ImportBatch).where(ImportBatch.source_sha256 == digest))
    if existing_batch and commit:
        raise ValueError("This exact source file has already been imported")

    text = csv_bytes.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text), delimiter=";"))
    result.total_rows = len(rows)
    uid_counts = Counter(
        normalize_identifier(row.get("HH ID", "")) for row in rows if row.get("HH ID", "").strip()
    )
    serial_counts = Counter(
        normalize_identifier(row.get("Serial number", ""))
        for row in rows
        if row.get("Serial number", "").strip()
    )
    points = {
        point.code.upper(): point
        for point in db.scalars(
            select(DistributionPoint).where(DistributionPoint.active.is_(True))
        ).all()
    }
    unknown_labels: set[str] = set()

    for index, row in enumerate(rows, start=2):
        uid = clean_text(row.get("HH ID")) or ""
        serial = clean_text(row.get("Serial number")) or ""
        reasons: list[str] = []
        try:
            uid_norm = normalize_identifier(uid)
            serial_norm = normalize_identifier(serial)
        except ValueError as exc:
            reasons.append(str(exc))
            uid_norm = serial_norm = ""

        if uid_norm and uid_counts[uid_norm] > 1:
            reasons.append("Household ID is duplicated within the source file")
        if serial_norm and serial_counts[serial_norm] > 1:
            reasons.append("Stove serial number is duplicated within the source file")

        source_label = clean_text(row.get("Distribution Center")) or ""
        code = point_mapping.get(normalize_label(source_label))
        point = points.get(code or "")
        if not point:
            reasons.append(f"Distribution point is not mapped: {source_label}")
            unknown_labels.add(source_label)

        if uid_norm and serial_norm:
            conflicts = duplicate_check(db, uid, serial)
            if conflicts.message:
                reasons.append(conflicts.message)

        payload = None
        if not reasons and point:
            try:
                payload = _payload(row, point.id)
            except (ValidationError, ValueError) as exc:
                reasons.append(str(exc).replace("\n", " ")[:500])

        if reasons:
            result.rejects.append(
                RejectedRow(
                    row_number=index,
                    household_uid=uid,
                    serial_number=serial,
                    reason="; ".join(dict.fromkeys(reasons)),
                )
            )
            result.rejected_rows += 1
            continue

        if commit and payload:
            try:
                create_record(db, payload, actor)
                result.inserted_rows += 1
            except HTTPException as exc:
                result.rejects.append(RejectedRow(index, uid, serial, str(exc.detail)))
                result.rejected_rows += 1
        else:
            result.skipped_rows += 1

    result.unknown_distribution_labels = sorted(unknown_labels)
    if commit:
        batch = ImportBatch(
            source_filename=source_filename[:255],
            source_sha256=digest,
            status="completed_with_rejects" if result.rejected_rows else "completed",
            total_rows=result.total_rows,
            inserted_rows=result.inserted_rows,
            skipped_rows=result.skipped_rows,
            rejected_rows=result.rejected_rows,
            report_json=result.to_dict(),
            run_by_user_id=actor.id,
            completed_at=datetime.now(UTC),
        )
        db.add(batch)
        db.commit()
    return result
