"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from users.middleware import JWTAuthMiddlewareStack
from users.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
	{
		'http': django_asgi_app,
		'websocket': JWTAuthMiddlewareStack(
			URLRouter(websocket_urlpatterns)
		),
	}
)
