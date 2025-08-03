from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from core.models import Post,UserPost
from django.utils import timezone

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_authenticated:
            # دریافت پست‌های کاربر
            user_posts = await self.get_user_posts(user)
            # اضافه کردن کاربر به گروه‌های مرتبط با پست‌هایش
            for post_id in user_posts:
                group_name = f"post_{post_id}"
                await self.channel_layer.group_add(group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        user = self.scope['user']
        if user.is_authenticated:
            user_posts = await self.get_user_posts(user)
            for post_id in user_posts:
                group_name = f"post_{post_id}"
                await self.channel_layer.group_discard(group_name, self.channel_name)

    @database_sync_to_async
    def get_user_posts(self, user):
        return list(UserPost.objects.filter(
            user=user,
            is_active=True,
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        ).values_list('post_id', flat=True))

    async def notify(self, event):
        # ارسال پیام به کلاینت
        await self.send_json({
            'message': event['message'],
            'entity_type': event['entity_type'],
            'action': event['action'],
            'priority': event['priority'],
            'timestamp': event['timestamp']
        })