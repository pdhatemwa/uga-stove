from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    DATA_MANAGER = "data_manager"
    DISTRIBUTION_OFFICER = "distribution_officer"
    AUDITOR = "auditor"
    STAKEHOLDER = "stakeholder"


class Permission(StrEnum):
    DASHBOARD_VIEW = "dashboard:view"
    RECORD_VIEW = "record:view"
    RECORD_CREATE = "record:create"
    RECORD_UPDATE = "record:update"
    RECORD_CHANGE_IDENTIFIERS = "record:change_identifiers"
    RECORD_EXPORT = "record:export"
    PDF_PRINT = "pdf:print"
    SIGNATURE_CAPTURE = "signature:capture"
    SIGNATURE_VERIFY = "signature:verify"
    IMPORT_RUN = "import:run"
    AUDIT_VIEW = "audit:view"
    USER_MANAGE = "user:manage"
    POINT_MANAGE = "point:manage"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),
    Role.DATA_MANAGER: {
        Permission.DASHBOARD_VIEW,
        Permission.RECORD_VIEW,
        Permission.RECORD_CREATE,
        Permission.RECORD_UPDATE,
        Permission.RECORD_CHANGE_IDENTIFIERS,
        Permission.RECORD_EXPORT,
        Permission.PDF_PRINT,
        Permission.SIGNATURE_CAPTURE,
        Permission.SIGNATURE_VERIFY,
        Permission.IMPORT_RUN,
        Permission.AUDIT_VIEW,
        Permission.POINT_MANAGE,
    },
    Role.DISTRIBUTION_OFFICER: {
        Permission.DASHBOARD_VIEW,
        Permission.RECORD_VIEW,
        Permission.RECORD_CREATE,
        Permission.RECORD_UPDATE,
        Permission.PDF_PRINT,
        Permission.SIGNATURE_CAPTURE,
    },
    Role.AUDITOR: {
        Permission.DASHBOARD_VIEW,
        Permission.RECORD_VIEW,
        Permission.RECORD_EXPORT,
        Permission.PDF_PRINT,
        Permission.AUDIT_VIEW,
    },
    Role.STAKEHOLDER: {Permission.DASHBOARD_VIEW},
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
