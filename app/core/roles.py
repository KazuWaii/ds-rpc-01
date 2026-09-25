ALL_DEPARTMENTS = { "engineering", "finance", "hr", "marketing", "general" }

ROLE_PERMISSIONS = {
    "engineering" : {"engineering", "general"},
    "finance" : {"finance", "general"},
    "hr" : {"hr", "general"},
    "marketing" : {"marketing", "general"},
    "employee" : {"general"},
    "admin" : ALL_DEPARTMENTS
}

def get_allowed_departments(role):
    role = role.lower()
    if role in ROLE_PERMISSIONS:
        return ROLE_PERMISSIONS[role]
    else:
        raise ValueError(f"Role '{role}' is not defined in ROLE_PERMISSIONS.")