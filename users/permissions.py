from rest_framework.permissions import BasePermission, SAFE_METHODS

ADMIN_ROLE = 'admin'


class RoleWritePermission(BasePermission):
    """
    Read access for any authenticated user; write access restricted to the
    roles declared on the view via `write_roles`. Admin can always write.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False

        if request.method in SAFE_METHODS:
            return True

        role = getattr(user, 'role', None)
        if role == ADMIN_ROLE:
            return True

        write_roles = getattr(view, 'write_roles', set())
        return role in write_roles


class IsAdmin(BasePermission):
    """Allow access only to admin users."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, 'role', None) == ADMIN_ROLE
        )


class IsChefStockOrAdmin(BasePermission):
    """Allow access only to stock manager and admin roles."""

    allowed_roles = {'chefstock', ADMIN_ROLE}

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, 'role', None) in self.allowed_roles
        )


class IsFournisseur(BasePermission):
    """Allow access only to supplier users."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, 'role', None) == 'fournisseur'
        )


class IsFournisseurOrAdmin(BasePermission):
    """Allow access only to suppliers and admins."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, 'role', None) in {'fournisseur', ADMIN_ROLE}
        )
