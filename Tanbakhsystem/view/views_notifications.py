# from django.shortcuts import render
# from django.contrib.auth.decorators import login_required
# # from notifications.models import Notification
# from django.core.paginator import Paginator
# from django.http import JsonResponse
# from django.views.decorators.http import require_POST
#
# from accounts.models import CustomUser
# from core.models import UserPost, Post
#
#
# @login_required
# def test_unread_count(request):
#     return JsonResponse({"unread_count": 42})
#
# def notifications_inbox(request):
#     # دریافت تمام اعلان‌های کاربر
#     notifications = request.user.notifications.all().order_by('-timestamp')  # مرتب‌سازی بر اساس تاریخ
#
#     # فیلتر بر اساس وضعیت (اختیاری)
#     status = request.GET.get('status', 'all')
#     if status == 'unread':
#         notifications = notifications.unread()
#     elif status == 'read':
#         notifications = notifications.read()
#
#     # صفحه‌بندی اعلان‌ها (۱۰ مورد در هر صفحه)
#     paginator = Paginator(notifications, 10)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
#
#     context = {
#         'page_obj': page_obj,
#         'title': 'صندوق دریافتی اعلان‌ها',
#         'unread_count': request.user.notifications.unread().count(),
#         'status': status,
#     }
#     return render(request, 'notifications/inbox.html', context)
#
#
# @require_POST
# def delete_notification(request, notification_id):
#     try:
#         notification = request.user.notifications.get(id=notification_id)
#         notification.delete()
#         from django.contrib import messages
#         messages.success(request, 'اعلان با موفقیت حذف شد.')
#         return JsonResponse({'status': 'success'})
#     except Exception as e : #Notification.DoesNotExist:
#         return JsonResponse({'status': 'error', 'message': 'اعلان یافت نشد'},f'{e}', status=404)
#
#
# @login_required
# def unread_notifications(request):
#     # دریافت اعلان‌های خوانده‌نشده کاربر فعلی
#     unread_notifications = request.user.notifications.unread().order_by('-timestamp')
#
#     # صفحه‌بندی اعلان‌ها (۱۰ مورد در هر صفحه)
#     paginator = Paginator(unread_notifications, 10)
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)
#
#     context = {
#         'page_obj': page_obj,
#         'title': 'اعلان‌های خوانده‌نشده',
#     }
#     return render(request, 'notifications/unread.html', context)
#
# @login_required
# def get_notifications(request):
#     notifications = request.user.notifications.all().order_by('-timestamp')[:10]
#     data = {
#         'notifications': [],
#         'unread_count': request.user.notifications.unread().count(),
#     }
#     for notice in notifications:
#         data['notifications'].append({
#             'id': notice.id,
#             'actor': notice.actor.username if notice.actor else '',
#             'verb': notice.verb,
#             'description': notice.description,
#             'target': str(notice.target) if notice.target else '',
#             'timestamp': notice.timestamp.strftime('%Y/%m/%d %H:%M'),
#             'unread': notice.unread,
#         })
#     return JsonResponse(data)
#
#
# from django.utils import timezone
# from datetime import date
# from notifications.signals import notify
#
# #فیلتر کردن کاربران متصل به پست:
# from core.models import UserPost
# def get_users_for_post(post):
#     """
#     کاربرانی که در حال حاضر به یک پست خاص متصل هستند را برمی‌گرداند.
#
#     Args:
#         post: نمونه‌ای از مدل Post
#
#     Returns:
#         لیست کاربران متصل به پست
#     """
#     today = date.today()
#     user_posts = (UserPost.objects.filter(
#         post=post,
#         is_active=True,
#         start_date__lte=today,
#         end_date__gte=today,
#     ) | UserPost.objects.filter(
#         post=post,
#         is_active=True,
#         start_date__lte=today,
#         end_date__isnull=True,
#     )).select_related('user').distinct('user')
#
#     return [user_post.user for user_post in user_posts]
#
#
# """ارسال اعلان: به کاربر """
# def send_notification(sender, users=None, posts=None, verb=None, description=None, target=None):
#     if not users and not posts:
#         print("حداقل باید یک کاربر یا یک پست برای ارسال اعلان مشخص شود.")
#         return
#
#     if not verb:
#         print("فعل اعلان (verb) باید مشخص شود.")
#         return
#
#     recipients = set()
#
#     if users:
#         if isinstance(users, CustomUser):
#             recipients.add(users)
#         else:
#             recipients.update(users)
#
#     if posts:
#         if isinstance(posts, Post):
#             posts = [posts]
#         for post in posts:
#             post_users = get_users_for_post(post)
#             recipients.update(post_users)
#
#     if not recipients:
#         print("هیچ کاربری برای دریافت اعلان پیدا نشد.")
#         return
#
#     notify.send(
#         sender=sender,
#         recipient=list(recipients),
#         verb=verb,
#         description=description,
#         target=target
#     )
#
# #
# # # مثال استفاده
# # sender = CustomUser.objects.get(username='sender_username')
# #
# # # ارسال به یک کاربر خاص
# # specific_user = CustomUser.objects.get(username='specific_user')
# # send_notification(
# #     sender=sender,
# #     users=specific_user,
# #     verb='یک پیام تست ارسال کرد',
# #     description='این یک اعلان آزمایشی است.'
# # )
# #
# # # ارسال به چند کاربر
# # users = CustomUser.objects.filter(username__in=['user1', 'user2'])
# # send_notification(
# #     sender=sender,
# #     users=users,
# #     verb='یک پیام تست برای چند کاربر ارسال کرد',
# #     description='این یک اعلان آزمایشی است.'
# # )
# #
# # # ارسال به یک پست
# # post = Post.objects.get(id=1)
# # send_notification(
# #     sender=sender,
# #     posts=post,
# #     verb='یک پیام تست برای پست ارسال کرد',
# #     description='این یک اعلان آزمایشی است.',
# #     target=post
# # )
# #
# # # ارسال به چند پست
# # posts = Post.objects.filter(organization__id=1, is_active=True)
# # send_notification(
# #     sender=sender,
# #     posts=posts,
# #     verb='یک پیام تست برای چند پست ارسال کرد',
# #     description='این یک اعلان آزمایشی است.',
# #     target=posts.first()
# # )
# #
# # # ارسال به ترکیبی از کاربران و پست‌ها
# # send_notification(
# #     sender=sender,
# #     users=users,
# #     posts=posts,
# #     verb='یک پیام تست برای کاربران و پست‌ها ارسال کرد',
# #     description='این یک اعلان آزمایشی است.',
# #     target=posts.first()
# # )
# #
#
#  # $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# #سناریو 1: ارسال اعلان به یک کاربر خاص
#
# # sender = CustomUser.objects.get(username='sender_username')
# # specific_user = CustomUser.objects.get(username='specific_user')
# #
# # send_notification(
# #     sender=sender,
# #     users=specific_user,
# #     verb='یک پیام تست ارسال کرد',
# #     description='این یک اعلان آزمایشی است.'
# # )
#
# # سناریو 2: ارسال اعلان به چند کاربر خاص
# # sender = CustomUser.objects.get(username='sender_username')
# # users = CustomUser.objects.filter(username__in=['user1', 'user2', 'user3'])
# #
# # send_notification(
# #     sender=sender,
# #     users=users,
# #     verb='یک پیام تست برای چند کاربر ارسال کرد',
# #     description='این یک اعلان آزمایشی است.'
# # )
# # سناریو 3: ارسال اعلان به یک پست
# # sender = CustomUser.objects.get(username='sender_username')
# # post = Post.objects.get(id=1)
# #
# # send_notification(
# #     sender=sender,
# #     posts=post,
# #     verb='یک پیام تست برای پست ارسال کرد',
# #     description='این یک اعلان آزمایشی است.',
# #     target=post
# # )
#
#
# # سناریو 4: ارسال اعلان به چند پست
# #
# # sender = CustomUser.objects.get(username='sender_username')
# # posts = Post.objects.filter(organization__id=1, is_active=True)
# #
# # send_notification(
# #     sender=sender,
# #     posts=posts,
# #     verb='یک پیام تست برای چند پست ارسال کرد',
# #     description='این یک اعلان آزمایشی است.',
# #     target=posts.first()  # یا می‌توانید سازمان را به‌عنوان target تنظیم کنید
# # )
#
#
# # سناریو 5: ارسال اعلان به ترکیبی از کاربران و پست‌ها
# #
# # sender = CustomUser.objects.get(username='sender_username')
# # specific_users = CustomUser.objects.filter(username__in=['user1', 'user2'])
# # posts = Post.objects.filter(organization__id=1, is_active=True)
# #
# # send_notification(
# #     sender=sender,
# #     users=specific_users,
# #     posts=posts,
# #     verb='یک پیام تست برای کاربران و پست‌ها ارسال کرد',
# #     description='این یک اعلان آزمایشی است.',
# #     target=posts.first()
# # )
# """فیلدهای نوتیف پکیچ"""
# # (action_object, action_object_content_type, action_object_content_type_id, action_object_object_id,
# #  actor, actor_content_type, actor_content_type_id, actor_object_id, data, deleted, description, emailed,
# #  id, level, public, recipient, recipient_id, target, target_content_type, target_content_type_id, target_object_id,
# #  timestamp, unread, verb)
#
