from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification, NotificationRule
from accounts.models import CustomUser
from core.models import Post
from tankhah.models import Tankhah, Factor
from budgets.models import BudgetTransaction

def get_users_for_post(post):
    """
    کاربرانی که در حال حاضر به یک پست خاص متصل هستند را برمی‌گرداند.
    """
    from core.models import UserPost
    from datetime import date
    today = date.today()
    active_user_posts = UserPost.objects.filter(
        post=post,
        is_active=True,
        start_date__lte=date.today()
    ).filter(
        Q(end_date__gte=date.today()) | Q(end_date__isnull=True)
    ).select_related('user')

    # 2. **اصلاح کلیدی:** به جای .distinct('user')، ما شناسه‌های کاربران را
    # استخراج کرده و آنها را منحصر به فرد می‌کنیم.
    user_ids = active_user_posts.values_list('user_id', flat=True).distinct()

    return list(CustomUser.objects.filter(id__in=user_ids))

def send_notification(sender, users=None, posts=None, verb=None, description=None, target=None, entity_type=None, priority='MEDIUM'):
    """
    تابع کلی برای ارسال اعلان به کاربران یا پست‌ها بر اساس قوانین اعلان.

    پارامترها:
        sender: کاربر یا موجودیت ارسال‌کننده اعلان (CustomUser یا None)
        users: لیست یا یک نمونه از CustomUser برای دریافت اعلان
        posts: لیست یا یک نمونه از Post برای دریافت اعلان
        verb: فعل اعلان (مانند 'CREATED', 'APPROVED')
        description: توضیحات اعلان
        target: شیء هدف اعلان (مانند Factor, Tankhah, PaymentOrder)
        entity_type: نوع موجودیت ('FACTOR', 'TANKHAH', 'PAYMENTORDER', 'BUDGET')
        priority: اولویت اعلان ('LOW', 'MEDIUM', 'HIGH')
    """
    if not users and not posts:
        print("حداقل باید یک کاربر یا یک پست برای ارسال اعلان مشخص شود.")
        return

    if not verb or not entity_type:
        print("فعل اعلان (verb) و نوع موجودیت (entity_type) باید مشخص شوند.")
        return

    # تعیین گیرندگان
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

    if not rules.exists():
        print(f"هیچ قانون اعلانی برای entity_type={entity_type} و action={verb} یافت نشد.")
        return

    # آماده‌سازی برای WebSocket
    channel_layer = get_channel_layer()
    timestamp = timezone.now().isoformat()
    notifications = []

    for recipient in recipients:
        for rule in rules:
            # بررسی اینکه آیا پست‌های گیرنده در قانون اعلان وجود دارند یا خیر
            if rule.recipients.filter(id__in=[p.id for p in posts or []]).exists() or recipient in recipients:
                # ایجاد اعلان
                notification = Notification(
                    recipient=recipient,
                    actor=sender,
                    verb=verb,
                    description=description,
                    target=target,
                    entity_type=entity_type,
                    priority=rule.priority if rule.priority else priority,
                    target_content_type=ContentType.objects.get_for_model(target) if target else None,
                    target_object_id=target.id if target else None
                )
                notifications.append(notification)

                # ارسال ایمیل اگر کانال شامل EMAIL باشد
                if rule.channel == 'EMAIL' and recipient.email:
                    send_mail(
                        subject=f"اعلان جدید: {verb}",
                        message=description or f"{sender.username if sender else 'سیستم'} {verb} {target or ''}",
                        from_email='soheiladv@gmail.com',
                        recipient_list=[recipient.email],
                        fail_silently=True,
                    )

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

    # ذخیره دسته‌جمعی اعلان‌ها
    if notifications:
        Notification.objects.bulk_create(notifications, batch_size=100)