from django.urls import re_path
from tankhah import consumers

websocket_urlpatterns = [
    re_path(r'ws/factor/$', consumers.FactorConsumer.as_asgi()),
]