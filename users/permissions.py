from rest_framework.permissions import BasePermission


class IsChefStockOrAdmin(BasePermission):
    """
    Allow access only to stock manager and admin roles.
    """

    allowed_roles = {"chefstock", "admin"}

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) in self.allowed_roles
        )


class IsFournisseur(BasePermission):
    """
    Allow access only to supplier users.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == "fournisseur"
        )


class IsFournisseurOrAdmin(BasePermission):
    """
    Allow access only to suppliers and admins.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) in {"fournisseur", "admin"}
        )
