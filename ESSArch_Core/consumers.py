from channels.auth import channel_session_user, channel_session_user_from_http
from django.core.cache import cache


# Connected to websocket.connect
@channel_session_user_from_http
def ws_add(message):
    # Accept the connection
    message.reply_channel.send({"accept": True})

    cache_name = 'notification_channel_%s' % message.user.username
    cached = cache.get(cache_name, set())

    # add this reply channel to the set
    cached.add(message.reply_channel.name)

    cache.set(cache_name, cached)

    message.reply_channel.send({'text': 'connected!'})

# Connected to websocket.receive
@channel_session_user
def ws_message(message):
    pass

# Connected to websocket.disconnect
@channel_session_user
def ws_disconnect(message):
    cache_name = 'notification_channel_%s' % message.user.username
    channels = cache.get(cache_name, set([]))
    channels.discard(message.reply_channel.name)
    cache.set(cache_name, channels, 3600)
