from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import ESSArch_Core.auth.routing as essauth_routing


application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            essauth_routing.websocket_urlpatterns
        )
    ),
})
