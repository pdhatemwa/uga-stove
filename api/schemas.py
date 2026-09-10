from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from api.models import SignatureStatus
from api.normalization import clean_text
from api.permissions import Role


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @model_validator(mode="after")
    def password_must_change(self):
        if self.current_password == self.new_password:
            raise ValueError("The new password must be different")
        return self


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    full_name: str
    role: Role
    distribution_point_id: str | None
    active: bool


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=128)
    role: Role
    distribution_point_id: str | None = None

    @model_validator(mode="after")
    def officer_requires_point(self):
        if self.role == Role.DISTRIBUTION_OFFICER and not self.distribution_point_id:
            raise ValueError("A distribution officer must be assigned to a distribution point")
        return self


class DistributionPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    active: bool


class DistributionPointCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=160)


class RecordCreate(BaseModel):
    household_uid: str = Field(min_length=2, max_length=80)
    household_head_name: str = Field(min_length=2, max_length=180)
    family_name: str | None = Field(default=None, max_length=180)
    household_size: int = Field(ge=1, le=100)
    phone_number: str = Field(min_length=7, max_length=40)
    additional_contact: str | None = Field(default=None, max_length=180)
    district: str = Field(default="Ntungamo", min_length=2, max_length=120)
    subcounty: str = Field(min_length=2, max_length=120)
    parish: str = Field(min_length=2, max_length=120)
    village: str = Field(min_length=2, max_length=160)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    altitude_m: float | None = None
    gps_precision_m: float | None = Field(default=None, ge=0)
    existing_stove_type_1: str | None = Field(default=None, max_length=160)
    existing_stove_type_2: str | None = Field(default=None, max_length=160)
    fuel_type: str | None = Field(default=None, max_length=100)
    fuel_amount_per_week: str | None = Field(default=None, max_length=120)
    existing_stove_units: int | None = Field(default=None, ge=0, le=20)
    existing_stoves_removed: bool | None = None
    serial_number: str = Field(min_length=3, max_length=100)
    stove_type: str = Field(default="Improved Cook Stove", min_length=2, max_length=120)
    stove_size: str = Field(min_length=2, max_length=40)
    distribution_point_id: str
    distributed_on: date
    receiver_type: str = Field(min_length=2, max_length=40)
    receiver_name: str | None = Field(default=None, max_length=180)
    receiver_relationship: str | None = Field(default=None, max_length=100)
    carbon_waiver_accepted: bool
    conditions_accepted: bool
    ambassador_name: str = Field(min_length=2, max_length=160)
    legacy_source: str | None = Field(default=None, max_length=40)
    legacy_record_id: str | None = Field(default=None, max_length=120)
    legacy_uuid: str | None = Field(default=None, max_length=120)
    legacy_photo_url: str | None = None

    @field_validator(
        "household_uid",
        "household_head_name",
        "family_name",
        "phone_number",
        "additional_contact",
        "district",
        "subcounty",
        "parish",
        "village",
        "existing_stove_type_1",
        "existing_stove_type_2",
        "fuel_type",
        "fuel_amount_per_week",
        "serial_number",
        "stove_type",
        "stove_size",
        "receiver_type",
        "receiver_name",
        "receiver_relationship",
        "ambassador_name",
        mode="before",
    )
    @classmethod
    def clean_strings(cls, value):
        return clean_text(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def receiver_rules(self):
        if self.receiver_type.lower() != "household head" and not self.receiver_name:
            raise ValueError("Receiver name is required when a representative receives the stove")
        return self


class RecordUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=8, max_length=500)
    household_uid: str | None = Field(default=None, min_length=2, max_length=80)
    serial_number: str | None = Field(default=None, min_length=3, max_length=100)
    household_head_name: str | None = Field(default=None, min_length=2, max_length=180)
    family_name: str | None = Field(default=None, max_length=180)
    household_size: int | None = Field(default=None, ge=1, le=100)
    phone_number: str | None = Field(default=None, min_length=7, max_length=40)
    additional_contact: str | None = Field(default=None, max_length=180)
    subcounty: str | None = Field(default=None, min_length=2, max_length=120)
    parish: str | None = Field(default=None, min_length=2, max_length=120)
    village: str | None = Field(default=None, min_length=2, max_length=160)
    stove_size: str | None = Field(default=None, min_length=2, max_length=40)
    distributed_on: date | None = None
    receiver_type: str | None = Field(default=None, min_length=2, max_length=40)
    receiver_name: str | None = Field(default=None, max_length=180)
    receiver_relationship: str | None = Field(default=None, max_length=100)
    ambassador_name: str | None = Field(default=None, min_length=2, max_length=160)
    distribution_point_id: str | None = None


class HouseholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    household_uid: str
    household_head_name: str
    family_name: str | None
    household_size: int
    phone_number: str
    additional_contact: str | None
    district: str
    subcounty: str
    parish: str
    village: str
    latitude: float | None
    longitude: float | None
    altitude_m: float | None
    gps_precision_m: float | None
    existing_stove_type_1: str | None
    existing_stove_type_2: str | None
    fuel_type: str | None
    fuel_amount_per_week: str | None
    existing_stove_units: int | None
    existing_stoves_removed: bool | None
    row_version: int


class StoveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    serial_number: str
    stove_type: str
    stove_size: str
    row_version: int


class SignatureEvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    method: str
    beneficiary_name: str
    witness_name: str
    signed_at: datetime
    original_filename: str
    size_bytes: int
    sha256: str
    verified_at: datetime | None
    rejected_reason: str | None
    created_at: datetime


class RecordOut(BaseModel):
    id: str
    household: HouseholdOut
    stove: StoveOut
    distribution_point: DistributionPointOut
    distributed_on: date
    receiver_type: str
    receiver_name: str | None
    receiver_relationship: str | None
    carbon_waiver_accepted: bool
    conditions_accepted: bool
    ambassador_name: str
    verification_code: str
    signature_status: SignatureStatus
    row_version: int
    signature_evidence: list[SignatureEvidenceOut] = Field(default_factory=list)


class DuplicateCheckOut(BaseModel):
    household_exists: bool
    serial_exists: bool
    message: str | None = None


class DashboardPointRow(BaseModel):
    distribution_point: str
    total: int
    signed: int
    verified: int


class DashboardSummaryOut(BaseModel):
    total_distributions: int
    unique_households: int
    unique_stoves: int
    captured_signatures: int
    verified_signatures: int
    unsigned_records: int
    large_stoves: int
    medium_stoves: int
    small_stoves: int
    by_distribution_point: list[DashboardPointRow]
    by_date: list[dict]


class SignatureReview(BaseModel):
    approve: bool
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def rejection_requires_reason(self):
        if not self.approve and not self.reason:
            raise ValueError("A rejection reason is required")
        return self


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: str | None
    action: str
    entity_type: str
    entity_id: str
    before_json: dict | None
    after_json: dict | None
    reason: str | None
    occurred_at: datetime
