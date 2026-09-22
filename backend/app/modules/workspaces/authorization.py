from app.modules.workspaces.dependencies import WorkspaceContext
from app.modules.workspaces.exceptions import AuthorizationError

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"

PERM_WORKSPACE_MANAGE = "workspace.manage"
PERM_MEMBERS_READ = "members.read"
PERM_MEMBERS_ADD = "members.add"
PERM_MEMBERS_REMOVE = "members.remove"
PERM_MEMBERS_CHANGE_ROLE = "members.change_role"

PERM_COMPANIES_READ = "companies.read"
PERM_COMPANIES_WRITE = "companies.write"
PERM_PEOPLE_READ = "people.read"
PERM_PEOPLE_WRITE = "people.write"

CRM_PERMISSIONS = {
    PERM_COMPANIES_READ,
    PERM_COMPANIES_WRITE,
    PERM_PEOPLE_READ,
    PERM_PEOPLE_WRITE,
}

ROLE_PERMISSIONS = {
    ROLE_MEMBER: {PERM_MEMBERS_READ, *CRM_PERMISSIONS},
    ROLE_ADMIN: {
        PERM_MEMBERS_READ,
        PERM_MEMBERS_ADD,
        PERM_MEMBERS_REMOVE,
        PERM_MEMBERS_CHANGE_ROLE,
        *CRM_PERMISSIONS,
    },
    ROLE_OWNER: {
        PERM_WORKSPACE_MANAGE,
        PERM_MEMBERS_READ,
        PERM_MEMBERS_ADD,
        PERM_MEMBERS_REMOVE,
        PERM_MEMBERS_CHANGE_ROLE,
        *CRM_PERMISSIONS,
    },
}

def require_permission(context: WorkspaceContext, permission: str) -> None:
    role = context.membership.role
    if permission not in ROLE_PERMISSIONS.get(role, set()):
        raise AuthorizationError(f"Role '{role}' lacks permission '{permission}'")

def can_modify_role(actor_role: str, target_current_role: str, target_new_role: str) -> bool:
    if actor_role == ROLE_OWNER:
        return True
    
    if actor_role == ROLE_ADMIN:
        # Admins cannot modify or remove owners
        if target_current_role == ROLE_OWNER:
            return False
        # Admins cannot assign owner role
        if target_new_role == ROLE_OWNER:
            return False
        return True
        
    return False

def can_remove_member(actor_role: str, target_role: str) -> bool:
    if actor_role == ROLE_OWNER:
        return True
        
    if actor_role == ROLE_ADMIN:
        # Admins cannot remove owners
        if target_role == ROLE_OWNER:
            return False
        return True
        
    return False
