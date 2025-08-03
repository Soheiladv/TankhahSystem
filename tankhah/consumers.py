from channels.generic.websocket import AsyncWebsocketConsumer
import json

class FactorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_authenticated:
            org_ids = set(up.post.organization.id for up in user.userpost_set.filter(is_active=True))
            for org_id in org_ids:
                await self.channel_layer.group_add(f'factor_{org_id}', self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        user = self.scope['user']
        if user.is_authenticated:
            org_ids = set(up.post.organization.id for up in user.userpost_set.filter(is_active=True))
            for org_id in org_ids:
                await self.channel_layer.group_discard(f'factor_{org_id}', self.channel_name)

    async def factor_update(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message']
        }))