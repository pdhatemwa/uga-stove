from api.permissions import Permission, Role, has_permission


def test_stakeholder_can_only_see_dashboard():
    assert has_permission(Role.STAKEHOLDER, Permission.DASHBOARD_VIEW)
    assert not has_permission(Role.STAKEHOLDER, Permission.RECORD_VIEW)
    assert not has_permission(Role.STAKEHOLDER, Permission.RECORD_EXPORT)


def test_distribution_officer_cannot_change_identifiers():
    assert has_permission(Role.DISTRIBUTION_OFFICER, Permission.RECORD_CREATE)
    assert not has_permission(Role.DISTRIBUTION_OFFICER, Permission.RECORD_CHANGE_IDENTIFIERS)
