from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from datetime import date

from django_jalali.templatetags.jformat import jformat

from .models import Notification, NotificationRule
from accounts.models import CustomUser
from core.models import UserPost, Post
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
logger = logging.getLogger(__name__)

@login_required
def test_unread_count(request):
    unread_count = request.user.notifications.filter(unread=True, deleted=False).count()
    return JsonResponse({"unread_count": unread_count})

@login_required
def notifications_inbox(request):
    # دریافت تمام اعلان‌های کاربر
    notifications = request.user.notifications.filter(deleted=False).order_by('-timestamp')

    # فیلتر بر اساس وضعیت (اختیاری)
    status = request.GET.get('status', 'all')
    if status == 'unread':
        notifications = notifications.filter(unread=True)
    elif status == 'read':
        notifications = notifications.filter(unread=False)

    # صفحه‌بندی اعلان‌ها (۱۰ مورد در هر صفحه)
    paginator = Paginator(notifications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'title': 'صندوق دریافتی اعلان‌ها',
        'unread_count': request.user.notifications.filter(unread=True, deleted=False).count(),
        'status': status,
    }
    return render(request, 'notifications/inbox.html', context)

@require_POST
@login_required
def delete_notification(request, notification_id):
    try:
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user, deleted=False)
        notification.mark_as_deleted()
        messages.success(request, 'اعلان با موفقیت حذف شد.')
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'اعلان یافت نشد'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def unread_notifications(request):
    # دریافت اعلان‌های خوانده‌نشده کاربر فعلی
    unread_notifications = request.user.notifications.filter(unread=True, deleted=False).order_by('-timestamp')

    # صفحه‌بندی اعلان‌ها (۱۰ مورد در هر صفحه)
    paginator = Paginator(unread_notifications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'title': 'اعلان‌های خوانده‌نشده',
    }
    return render(request, 'notifications/unread.html', context)

@login_required
def get_notifications(request):
    notifications = request.user.notifications.filter(deleted=False).order_by('-timestamp')[:10]
    unread_count = request.user.notifications.filter(unread=True, deleted=False).count()

    # 💡 NEW: Define URL patterns once
    MARK_AS_READ_URL_PATTERN = reverse('notifications:mark_as_read', args=[0])
    NOTIFICATIONS_INBOX_URL = reverse('notifications:inbox')

    data = {
        'notifications': [
            {
                'id': notice.id,
                'actor': str(notice.actor) if notice.actor else 'سیستم',
                'verb': notice.verb,
                'description': notice.description or '',
                'target': str(notice.target) if notice.target else '',
                'timestamp': jformat(notice.timestamp, "%Y/%m/%d - %H:%M"),  # Use jformat for consistency
                'unread': notice.unread,
                'priority': notice.get_priority_display(),
                # 💡 NEW: Generate the final URL for the frontend
                'url': f"{MARK_AS_READ_URL_PATTERN.replace('0', str(notice.id))}?next={getattr(notice.target, 'get_absolute_url', lambda: NOTIFICATIONS_INBOX_URL)()}"
            }
            for notice in notifications
        ],
        'unread_count': unread_count,
    }
    return JsonResponse(data)


def get_users_for_post(post):
    """
    کاربرانی که در حال حاضر به یک پست خاص متصل هستند را برمی‌گرداند.
    """
    today = date.today()
    user_posts = (UserPost.objects.filter(
        post=post,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today,
    ) | UserPost.objects.filter(
        post=post,
        is_active=True,
        start_date__lte=today,
        end_date__isnull=True,
    )).select_related('user').distinct('user')

    return [user_post.user for user_post in user_posts]

def send_notification(sender, users=None, posts=None, verb=None, description=None, target=None, entity_type=None, priority='MEDIUM'):
    """
    ارسال اعلان به کاربران یا پست‌ها بر اساس قوانین اعلان.
    """
    if not users and not posts:
        print("حداقل باید یک کاربر یا یک پست برای ارسال اعلان مشخص شود.")
        return

    if not verb or not entity_type:
        print("فعل اعلان (verb) و نوع موجودیت (entity_type) باید مشخص شوند.")
        return

    recipients = set()

    if users:
        if isinstance(users, CustomUser):
            recipients.add(users)
        else:
            recipients.update(users)

    if posts:
        if isinstance(posts, Post):
            posts = [posts]
        for post in posts:
            post_users = get_users_for_post(post)
            recipients.update(post_users)

    if not recipients:
        print("هیچ کاربری برای دریافت اعلان پیدا نشد.")
        return

    # بررسی قوانین اعلان
    rules = NotificationRule.objects.filter(
        entity_type=entity_type,
        action=verb,
        is_active=True
    )

    channel_layer = get_channel_layer()
    timestamp = timezone.now().isoformat()
    notifications = []

    for recipient in recipients:
        for rule in rules:
            if rule.recipients.filter(id__in=[p.id for p in posts or []]).exists() or recipient in recipients:
                notification = Notification(
                    recipient=recipient,
                    actor=sender,
                    verb=verb,
                    description=description,
                    target=target,
                    entity_type=entity_type,
                    priority=rule.priority if rule.priority else priority,
                )
                notifications.append(notification)
                # ارسال اعلان از طریق WebSocket
                for post in rule.recipients.all():
                    group_name = f"post_{post.id}"
                    async_to_sync(channel_layer.group_send)(
                        group_name,
                        {
                            'type': 'notify',
                            'message': description or f"{entity_type} {verb} شد.",
                            'entity_type': entity_type,
                            'action': verb,
                            'priority': rule.priority if rule.priority else priority,
                            'timestamp': timestamp
                        }
                    )

    if notifications:
        Notification.objects.bulk_create(notifications)
        logger.info(f"Successfully sent {len(notifications)} notifications.")

    # 💡 IMPROVEMENT: Send a single WebSocket message after creating notifications
    # This is more efficient than sending one message per recipient in the loop
    for recipient in recipients:
        group_name = f"user_{recipient.id}"  # Send to a user-specific channel
        async_to_sync(get_channel_layer().group_send)(
            group_name,
            {
                'type': 'new_notification',
                'message': 'شما یک اعلان جدید دارید.'
            }
        )
