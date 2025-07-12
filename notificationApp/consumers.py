# consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("updates", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("updates", self.channel_name)

    async def factor_update(self, event):
        await self.send_json(event['message'])

    async def tankhah_update(self, event):
        await self.send_json(event['message'])

    async def paymentorder_update(self, event):
        await self.send_json(event['message'])