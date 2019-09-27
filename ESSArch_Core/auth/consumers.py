import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger('essarch.core.auth.consumers')


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        grp = 'notifications_{}'.format(user.pk)
        await self.accept()
        await self.channel_layer.group_add(grp, self.channel_name)
        logger.info("Added {} channel to {}".format(self.channel_name, grp))

    async def disconnect(self, close_code):
        user = self.scope["user"]
        grp = 'notifications_{}'.format(user.pk)
        await self.channel_layer.group_discard(grp, self.channel_name)
        logger.info("Removed {} channel from {}".format(self.channel_name, grp))

    async def notify(self, event):
        await self.send_json(event)
        logger.info("Notification with id {} sent to channel {}".format(event['id'], self.channel_name))
