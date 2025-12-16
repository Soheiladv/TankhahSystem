import logging
from datetime import date

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_jalali.templatetags.jformat import jformat

from accounts.models import CustomUser
from core.models import Post, UserPost

from .models import Notification, NotificationRule

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
    """حذف اعلان (soft delete) - اعلان دیگر نمایش داده نمی‌شود"""
    try:
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user, deleted=False)
        notification.mark_as_deleted()
        messages.success(request, 'اعلان با موفقیت حذف شد.')
        return JsonResponse({
            'status': 'success',
            'message': 'اعلان حذف شد و دیگر نمایش داده نمی‌شود.'
        })
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'اعلان یافت نشد'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
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
def mark_as_read(request, notification_id):
    """علامت‌گذاری اعلان به عنوان خوانده شده"""
    try:
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user, deleted=False)
        notification.mark_as_read()
        messages.success(request, 'اعلان به عنوان خوانده شده علامت‌گذاری شد.')

        # بازگشت به صفحه قبلی یا inbox
        next_url = request.GET.get('next', reverse('notifications:inbox'))
        return redirect(next_url)
    except Notification.DoesNotExist:
        messages.error(request, 'اعلان یافت نشد.')
        return redirect('notifications:inbox')
    except Exception as e:
        messages.error(request, f'خطا در علامت‌گذاری اعلان: {str(e)}')
        return redirect('notifications:inbox')

@login_required
def mark_notification_viewed(request, notification_id):
    """علامت‌گذاری اعلان به عنوان دیده شده (خوانده شده) بدون redirect"""
    try:
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            recipient=request.user,
            deleted=False
        )
        if notification.unread:
            notification.mark_as_read()
        return JsonResponse({'status': 'success', 'unread': False})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'اعلان یافت نشد'}, status=404)
    except Exception as e:
        logger.error(f"Error marking notification as viewed: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def get_notifications(request):
    notifications = request.user.notifications.filter(deleted=False).order_by('-timestamp')[:10]
    unread_count = request.user.notifications.filter(unread=True, deleted=False).count()

    # 💡 NEW: Define URL patterns once
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
                'read_at': jformat(notice.read_at, "%Y/%m/%d - %H:%M") if notice.read_at else None,
                'actor_username': notice.actor.username if notice.actor else 'سیستم',
                # 💡 NEW: Generate the final URL for the frontend
                'url': _build_notification_url(notice, NOTIFICATIONS_INBOX_URL),
                'mark_viewed_url': reverse('notifications:mark_viewed', args=[notice.id])
            }
            for notice in notifications
        ],
        'unread_count': unread_count,
    }
    return JsonResponse(data)


def _build_notification_url(notice, default_url):
    """ساخت URL برای mark_as_read با next parameter"""
    try:
        mark_as_read_url = reverse('notifications:mark_as_read', args=[notice.id])
        # تعیین URL مقصد
        if notice.target:
            try:
                next_url = notice.target.get_absolute_url()
            except (AttributeError, Exception):
                next_url = default_url
        else:
            next_url = default_url
        return f"{mark_as_read_url}?next={next_url}"
    except Exception as e:
        logger.error(f"Error building notification URL: {e}")
        return default_url


@login_required
def admin_notifications_dashboard(request):
    """داشبورد ادمین برای مدیریت همه اعلان‌ها"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'شما اجازه دسترسی به این صفحه را ندارید.')
        return redirect('core:dashboard')

    # فیلترها
    status_filter = request.GET.get('status', 'all')  # all, unread, read, deleted
    priority_filter = request.GET.get('priority', 'all')
    entity_filter = request.GET.get('entity_type', 'all')
    actor_filter = request.GET.get('actor', '')

    # دریافت اعلان‌ها
    notifications = Notification.objects.all().select_related('recipient', 'actor', 'target_content_type').order_by('-timestamp')

    # اعمال فیلترها
    if status_filter == 'unread':
        notifications = notifications.filter(unread=True, deleted=False)
    elif status_filter == 'read':
        notifications = notifications.filter(unread=False, deleted=False)
    elif status_filter == 'deleted':
        notifications = notifications.filter(deleted=True)
    elif status_filter == 'all':
        notifications = notifications.filter(deleted=False)

    if priority_filter != 'all':
        notifications = notifications.filter(priority=priority_filter)

    if entity_filter != 'all':
        notifications = notifications.filter(entity_type=entity_filter)

    if actor_filter:
        notifications = notifications.filter(actor__username__icontains=actor_filter)

    # آمار کلی
    stats = {
        'total': Notification.objects.filter(deleted=False).count(),
        'unread': Notification.objects.filter(unread=True, deleted=False).count(),
        'read': Notification.objects.filter(unread=False, deleted=False).count(),
        'deleted': Notification.objects.filter(deleted=True).count(),
        'by_priority': {
            'LOW': Notification.objects.filter(priority='LOW', deleted=False).count(),
            'MEDIUM': Notification.objects.filter(priority='MEDIUM', deleted=False).count(),
            'HIGH': Notification.objects.filter(priority='HIGH', deleted=False).count(),
            'WARNING': Notification.objects.filter(priority='WARNING', deleted=False).count(),
            'ERROR': Notification.objects.filter(priority='ERROR', deleted=False).count(),
        },
        'by_entity': {
            entity_type: Notification.objects.filter(entity_type=entity_type, deleted=False).count()
            for entity_type, _ in Notification._meta.get_field('entity_type').choices
        }
    }

    # صفحه‌بندی
    paginator = Paginator(notifications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'stats': stats,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'entity_filter': entity_filter,
        'actor_filter': actor_filter,
        'title': 'داشبورد مدیریت اعلان‌ها',
    }
    return render(request, 'notifications/admin_dashboard.html', context)


@login_required
def creator_notifications_view(request, user_id):
    """نمایش اعلان‌های ایجاد شده توسط یک کاربر خاص"""
    # فقط کاربر خودش یا ادمین می‌تواند ببیند
    if request.user.id != user_id and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'شما اجازه دسترسی به این صفحه را ندارید.')
        return redirect('core:dashboard')

    creator = get_object_or_404(CustomUser, id=user_id)
    notifications = Notification.objects.filter(actor=creator).select_related('recipient', 'target_content_type').order_by('-timestamp')

    # آمار
    stats = {
        'total_created': notifications.count(),
        'unread_count': notifications.filter(unread=True, deleted=False).count(),
        'read_count': notifications.filter(unread=False, deleted=False).count(),
        'deleted_count': notifications.filter(deleted=True).count(),
    }

    # صفحه‌بندی
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'stats': stats,
        'creator': creator,
        'title': f'اعلان‌های ایجاد شده توسط {creator.username}',
    }
    return render(request, 'notifications/creator_view.html', context)


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
