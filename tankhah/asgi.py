import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import tankhah.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(tankhah.routing.websocket_urlpatterns)
    ),
})