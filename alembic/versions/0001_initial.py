"""Initial UGA Stove schema.

Revision ID: 0001_initial
Revises: None
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "distribution_points",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("code", name="uq_distribution_points_code"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("username_norm", sa.String(100), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "ADMIN",
                "DATA_MANAGER",
                "DISTRIBUTION_OFFICER",
                "AUDITOR",
                "STAKEHOLDER",
                name="role",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "distribution_point_id",
            sa.String(36),
            sa.ForeignKey("distribution_points.id", ondelete="SET NULL"),
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("username_norm", name="uq_users_username_norm"),
    )
    op.create_table(
        "households",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("household_uid", sa.String(80), nullable=False),
        sa.Column("household_uid_norm", sa.String(80), nullable=False),
        sa.Column("household_head_name", sa.String(180), nullable=False),
        sa.Column("family_name", sa.String(180)),
        sa.Column("household_size", sa.Integer(), nullable=False),
        sa.Column("phone_number", sa.String(40), nullable=False),
        sa.Column("additional_contact", sa.String(180)),
        sa.Column("district", sa.String(120), nullable=False),
        sa.Column("subcounty", sa.String(120), nullable=False),
        sa.Column("parish", sa.String(120), nullable=False),
        sa.Column("village", sa.String(160), nullable=False),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("altitude_m", sa.Float()),
        sa.Column("gps_precision_m", sa.Float()),
        sa.Column("existing_stove_type_1", sa.String(160)),
        sa.Column("existing_stove_type_2", sa.String(160)),
        sa.Column("fuel_type", sa.String(100)),
        sa.Column("fuel_amount_per_week", sa.String(120)),
        sa.Column("existing_stove_units", sa.Integer()),
        sa.Column("existing_stoves_removed", sa.Boolean()),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("household_uid_norm", name="uq_households_uid_norm"),
    )
    op.create_index("ix_households_head_name", "households", ["household_head_name"])
    op.create_table(
        "stoves",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("serial_number", sa.String(100), nullable=False),
        sa.Column("serial_number_norm", sa.String(100), nullable=False),
        sa.Column("stove_type", sa.String(120), nullable=False),
        sa.Column("stove_size", sa.String(40), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("serial_number_norm", name="uq_stoves_serial_norm"),
    )
    op.create_table(
        "distributions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "household_id",
            sa.String(36),
            sa.ForeignKey("households.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "stove_id",
            sa.String(36),
            sa.ForeignKey("stoves.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "distribution_point_id",
            sa.String(36),
            sa.ForeignKey("distribution_points.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("distributed_on", sa.Date(), nullable=False),
        sa.Column("receiver_type", sa.String(40), nullable=False),
        sa.Column("receiver_name", sa.String(180)),
        sa.Column("receiver_relationship", sa.String(100)),
        sa.Column("carbon_waiver_accepted", sa.Boolean(), nullable=False),
        sa.Column("conditions_accepted", sa.Boolean(), nullable=False),
        sa.Column("ambassador_name", sa.String(160), nullable=False),
        sa.Column("verification_code", sa.String(32), nullable=False),
        sa.Column(
            "signature_status",
            sa.Enum(
                "UNSIGNED",
                "CAPTURED",
                "VERIFIED",
                "REJECTED",
                name="signaturestatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("legacy_source", sa.String(40)),
        sa.Column("legacy_record_id", sa.String(120)),
        sa.Column("legacy_uuid", sa.String(120)),
        sa.Column("legacy_photo_url", sa.Text()),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("row_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("household_id", name="uq_distributions_household"),
        sa.UniqueConstraint("stove_id", name="uq_distributions_stove"),
        sa.UniqueConstraint("verification_code", name="uq_distributions_verification_code"),
    )
    op.create_index("ix_distributions_date", "distributions", ["distributed_on"])
    op.create_table(
        "signature_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "distribution_id",
            sa.String(36),
            sa.ForeignKey("distributions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("method", sa.String(40), nullable=False),
        sa.Column("beneficiary_name", sa.String(180), nullable=False),
        sa.Column("witness_name", sa.String(180), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("object_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("notes", sa.Text()),
        sa.Column("captured_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("verified_by_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("rejected_reason", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_signature_evidence_distribution_id", "signature_evidence", ["distribution_id"]
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(80), nullable=False),
        sa.Column("before_json", sa.JSON()),
        sa.Column("after_json", sa.JSON()),
        sa.Column("reason", sa.Text()),
        sa.Column("request_id", sa.String(80)),
        sa.Column("client_ip", sa.String(80)),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_audit_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_table(
        "import_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_filename", sa.String(255), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("inserted_rows", sa.Integer(), nullable=False),
        sa.Column("skipped_rows", sa.Integer(), nullable=False),
        sa.Column("rejected_rows", sa.Integer(), nullable=False),
        sa.Column("report_json", sa.JSON()),
        sa.Column("run_by_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("source_sha256", name="uq_import_batches_source_sha256"),
    )


def downgrade() -> None:
    op.drop_table("import_batches")
    op.drop_index("ix_audit_entity", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_signature_evidence_distribution_id", table_name="signature_evidence")
    op.drop_table("signature_evidence")
    op.drop_index("ix_distributions_date", table_name="distributions")
    op.drop_table("distributions")
    op.drop_table("stoves")
    op.drop_index("ix_households_head_name", table_name="households")
    op.drop_table("households")
    op.drop_table("users")
    op.drop_table("distribution_points")
