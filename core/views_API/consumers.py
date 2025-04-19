from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ChartUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('chart_updates', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('chart_updates', self.channel_name)

    async def chart_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chart_update',
            'message': event['message']
        }))