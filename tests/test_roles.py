import pytest

from app.core.roles import ALL_DEPARTMENTS, ROLE_PERMISSIONS, get_allowed_departments


@pytest.mark.parametrize(
    "role, expected",
    [
        ("finance", {"finance", "general"}),
        ("marketing", {"marketing", "general"}),
        ("hr", {"hr", "general"}),
        ("engineering", {"engineering", "general"}),
        ("employee", {"general"}),
        ("admin", ALL_DEPARTMENTS),
    ],
)
def test_get_allowed_departments(role, expected):
    assert get_allowed_departments(role) == expected


def test_get_allowed_departments_is_case_insensitive():
    assert get_allowed_departments("FINANCE") == get_allowed_departments("finance")


def test_unknown_role_raises():
    with pytest.raises(ValueError):
        get_allowed_departments("not-a-real-role")


def test_admin_has_full_access_including_general():
    # Regression test: ALL_DEPARTMENTS must include "general", or an
    # admin/C-level user would have LESS access than a plain employee.
    assert "general" in ROLE_PERMISSIONS["admin"]
    assert ROLE_PERMISSIONS["admin"] == ALL_DEPARTMENTS
