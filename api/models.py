import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base
from api.permissions import Role


def new_uuid() -> str:
    return str(uuid.uuid4())


class SignatureStatus(StrEnum):
    UNSIGNED = "unsigned"
    CAPTURED = "captured"
    VERIFIED = "verified"
    REJECTED = "rejected"


class DistributionPoint(Base):
    __tablename__ = "distribution_points"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="distribution_point")
    distributions: Mapped[list["Distribution"]] = relationship(back_populates="distribution_point")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    username_norm: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False), nullable=False)
    distribution_point_id: Mapped[str | None] = mapped_column(
        ForeignKey("distribution_points.id", ondelete="SET NULL"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    distribution_point: Mapped[DistributionPoint | None] = relationship(back_populates="users")


class Household(Base):
    __tablename__ = "households"
    __table_args__ = (
        UniqueConstraint("household_uid_norm", name="uq_households_uid_norm"),
        Index("ix_households_head_name", "household_head_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    household_uid: Mapped[str] = mapped_column(String(80), nullable=False)
    household_uid_norm: Mapped[str] = mapped_column(String(80), nullable=False)
    household_head_name: Mapped[str] = mapped_column(String(180), nullable=False)
    family_name: Mapped[str | None] = mapped_column(String(180))
    household_size: Mapped[int] = mapped_column(Integer, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(40), nullable=False)
    additional_contact: Mapped[str | None] = mapped_column(String(180))
    district: Mapped[str] = mapped_column(String(120), nullable=False, default="Ntungamo")
    subcounty: Mapped[str] = mapped_column(String(120), nullable=False)
    parish: Mapped[str] = mapped_column(String(120), nullable=False)
    village: Mapped[str] = mapped_column(String(160), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    altitude_m: Mapped[float | None] = mapped_column(Float)
    gps_precision_m: Mapped[float | None] = mapped_column(Float)
    existing_stove_type_1: Mapped[str | None] = mapped_column(String(160))
    existing_stove_type_2: Mapped[str | None] = mapped_column(String(160))
    fuel_type: Mapped[str | None] = mapped_column(String(100))
    fuel_amount_per_week: Mapped[str | None] = mapped_column(String(120))
    existing_stove_units: Mapped[int | None] = mapped_column(Integer)
    existing_stoves_removed: Mapped[bool | None] = mapped_column(Boolean)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    distribution: Mapped["Distribution | None"] = relationship(back_populates="household")


class Stove(Base):
    __tablename__ = "stoves"
    __table_args__ = (UniqueConstraint("serial_number_norm", name="uq_stoves_serial_norm"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number_norm: Mapped[str] = mapped_column(String(100), nullable=False)
    stove_type: Mapped[str] = mapped_column(
        String(120), nullable=False, default="Improved Cook Stove"
    )
    stove_size: Mapped[str] = mapped_column(String(40), nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    distribution: Mapped["Distribution | None"] = relationship(back_populates="stove")


class Distribution(Base):
    __tablename__ = "distributions"
    __table_args__ = (
        UniqueConstraint("household_id", name="uq_distributions_household"),
        UniqueConstraint("stove_id", name="uq_distributions_stove"),
        UniqueConstraint("verification_code", name="uq_distributions_verification_code"),
        Index("ix_distributions_date", "distributed_on"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    household_id: Mapped[str] = mapped_column(
        ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    stove_id: Mapped[str] = mapped_column(
        ForeignKey("stoves.id", ondelete="RESTRICT"), nullable=False
    )
    distribution_point_id: Mapped[str] = mapped_column(
        ForeignKey("distribution_points.id", ondelete="RESTRICT"), nullable=False
    )
    distributed_on: Mapped[date] = mapped_column(Date, nullable=False)
    receiver_type: Mapped[str] = mapped_column(String(40), nullable=False)
    receiver_name: Mapped[str | None] = mapped_column(String(180))
    receiver_relationship: Mapped[str | None] = mapped_column(String(100))
    carbon_waiver_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    conditions_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ambassador_name: Mapped[str] = mapped_column(String(160), nullable=False)
    verification_code: Mapped[str] = mapped_column(String(32), nullable=False)
    signature_status: Mapped[SignatureStatus] = mapped_column(
        Enum(SignatureStatus, native_enum=False), nullable=False, default=SignatureStatus.UNSIGNED
    )
    legacy_source: Mapped[str | None] = mapped_column(String(40))
    legacy_record_id: Mapped[str | None] = mapped_column(String(120))
    legacy_uuid: Mapped[str | None] = mapped_column(String(120))
    legacy_photo_url: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    household: Mapped[Household] = relationship(back_populates="distribution")
    stove: Mapped[Stove] = relationship(back_populates="distribution")
    distribution_point: Mapped[DistributionPoint] = relationship(back_populates="distributions")
    signature_evidence: Mapped[list["SignatureEvidence"]] = relationship(
        back_populates="distribution", cascade="all, delete-orphan"
    )


class SignatureEvidence(Base):
    __tablename__ = "signature_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    distribution_id: Mapped[str] = mapped_column(
        ForeignKey("distributions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(String(40), nullable=False, default="signed_form_photo")
    beneficiary_name: Mapped[str] = mapped_column(String(180), nullable=False)
    witness_name: Mapped[str] = mapped_column(String(180), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    captured_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    verified_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    distribution: Mapped[Distribution] = relationship(back_populates="signature_evidence")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    before_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(80))
    client_ip: Mapped[str | None] = mapped_column(String(80))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    report_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    run_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
