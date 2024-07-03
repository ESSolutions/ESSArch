import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        logger = logging.getLogger('essarch.core.auth.consumers')
        user = self.scope["user"]
        grp = 'notifications_{}'.format(user.pk)
        await self.accept()
        await self.channel_layer.group_add(grp, self.channel_name)
        logger.info("Added {} channel to {}".format(self.channel_name, grp))

    async def disconnect(self, close_code):
        logger = logging.getLogger('essarch.core.auth.consumers')
        user = self.scope["user"]
        grp = 'notifications_{}'.format(user.pk)
        await self.channel_layer.group_discard(grp, self.channel_name)
        logger.info("Removed {} channel from {}".format(self.channel_name, grp))

    async def notify(self, event):
        logger = logging.getLogger('essarch.core.auth.consumers')
        await self.send_json(event)
        logger.info("Notification with id {} sent to channel {}".format(event['id'], self.channel_name))
