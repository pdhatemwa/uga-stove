from pathlib import Path

from api.importers.kobo_csv import import_kobo_csv, parse_point_mapping
from api.models import DistributionPoint


def test_sample_import_dry_run_and_commit(db, admin):
    point_one = DistributionPoint(code="POINT-1", name="Point One")
    point_two = DistributionPoint(code="POINT-2", name="Point Two")
    db.add_all([point_one, point_two])
    db.commit()
    raw = Path("data/sample/kobo_sample.csv").read_bytes()
    mapping = parse_point_mapping(Path("config/distribution_points.sample.csv").read_bytes())

    dry_run = import_kobo_csv(
        db,
        csv_bytes=raw,
        source_filename="sample.csv",
        actor=admin,
        point_mapping=mapping,
        commit=False,
    )
    assert dry_run.total_rows == 2
    assert dry_run.rejected_rows == 0
    assert dry_run.skipped_rows == 2

    committed = import_kobo_csv(
        db,
        csv_bytes=raw,
        source_filename="sample.csv",
        actor=admin,
        point_mapping=mapping,
        commit=True,
    )
    assert committed.inserted_rows == 2
    assert committed.rejected_rows == 0
