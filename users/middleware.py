from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


def _anonymous_user():
    from django.contrib.auth.models import AnonymousUser
    return AnonymousUser()


@database_sync_to_async
def _get_user_by_id(user_id):
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return _anonymous_user()

    if getattr(user, "is_deleted", False):
        return _anonymous_user()

    return user


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        token = self._extract_token(scope)
        if not token:
            raise DenyConnection("Missing JWT token")

        try:
            access_token = AccessToken(token)
            user_id = access_token.get("user_id")
            if not user_id:
                raise DenyConnection("Invalid JWT payload")

            user = await _get_user_by_id(user_id)
            if not user or user.is_anonymous:
                raise DenyConnection("Invalid user")

            scope["user"] = user
        except TokenError as exc:
            raise DenyConnection("Invalid JWT token") from exc

        return await super().__call__(scope, receive, send)

    def _extract_token(self, scope):
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization")

        if auth_header:
            raw_value = auth_header.decode("utf-8", errors="ignore")
            parts = raw_value.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1]

        query_params = parse_qs(scope.get("query_string", b"").decode("utf-8", errors="ignore"))
        token_list = query_params.get("token")
        if token_list:
            return token_list[0]

        return None


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
