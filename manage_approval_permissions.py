#!/usr/bin/env python
import os
import sys
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BudgetsSystem.settings')
django.setup()

from accounts.models import CustomUser
from core.models import UserPost, PostAction, Post, Organization, Status, EntityType
from budgets.models import PaymentOrder

def manage_approval_permissions():
    """مدیریت دسترسی‌های تایید"""
    
    print("🔧 مدیریت دسترسی‌های تایید")
    print("=" * 60)
    
    # دریافت کاربران
    users = CustomUser.objects.filter(is_active=True).order_by('username')
    
    print("👥 کاربران موجود:")
    for i, user in enumerate(users, 1):
        user_posts = UserPost.objects.filter(user=user, is_active=True).count()
        print(f"   {i:2d}. {user.username} ({user.first_name} {user.last_name}) - {user_posts} پست")
    
    print(f"\n🔧 عملیات‌های موجود:")
    print(f"   1. حذف دسترسی تایید از کاربر")
    print(f"   2. اضافه کردن دسترسی تایید به کاربر")
    print(f"   3. نمایش دسترسی‌های فعلی کاربر")
    print(f"   4. نمایش همه دسترسی‌های تایید")
    print(f"   5. خروج")
    
    while True:
        try:
            choice = input(f"\nانتخاب کنید (1-5): ").strip()
            
            if choice == '1':
                remove_approval_access()
            elif choice == '2':
                add_approval_access()
            elif choice == '3':
                show_user_permissions()
            elif choice == '4':
                show_all_permissions()
            elif choice == '5':
                print("👋 خداحافظ!")
                break
            else:
                print("❌ انتخاب نامعتبر!")
                
        except KeyboardInterrupt:
            print("\n👋 خداحافظ!")
            break
        except Exception as e:
            print(f"❌ خطا: {e}")

def remove_approval_access():
    """حذف دسترسی تایید از کاربر"""
    print(f"\n🗑️  حذف دسترسی تایید از کاربر")
    print("-" * 40)
    
    username = input("نام کاربری: ").strip()
    try:
        user = CustomUser.objects.get(username=username)
        print(f"👤 کاربر: {user.username} ({user.first_name} {user.last_name})")
    except CustomUser.DoesNotExist:
        print("❌ کاربر یافت نشد")
        return
    
    # نمایش پست‌های کاربر
    user_posts = UserPost.objects.filter(
        user=user,
        is_active=True,
        end_date__isnull=True
    ).select_related('post', 'post__organization')
    
    if not user_posts.exists():
        print("❌ کاربر هیچ پست فعالی ندارد")
        return
    
    print(f"\n📋 پست‌های فعال کاربر:")
    for i, user_post in enumerate(user_posts, 1):
        print(f"   {i}. {user_post.post.name} (سازمان: {user_post.post.organization.name})")
    
    # انتخاب پست برای حذف
    try:
        post_choice = int(input("شماره پست برای حذف دسترسی: ")) - 1
        if 0 <= post_choice < len(user_posts):
            selected_userpost = user_posts[post_choice]
            print(f"📌 پست انتخاب شده: {selected_userpost.post.name}")
            
            # تأیید حذف
            confirm = input("آیا مطمئن هستید؟ (y/N): ").strip().lower()
            if confirm == 'y':
                selected_userpost.is_active = False
                selected_userpost.end_date = date.today()
                selected_userpost.save()
                print(f"✅ دسترسی تایید از کاربر {user.username} حذف شد")
            else:
                print("❌ عملیات لغو شد")
        else:
            print("❌ انتخاب نامعتبر")
    except ValueError:
        print("❌ لطفاً عدد وارد کنید")

def add_approval_access():
    """اضافه کردن دسترسی تایید به کاربر"""
    print(f"\n➕ اضافه کردن دسترسی تایید به کاربر")
    print("-" * 40)
    
    username = input("نام کاربری: ").strip()
    try:
        user = CustomUser.objects.get(username=username)
        print(f"👤 کاربر: {user.username} ({user.first_name} {user.last_name})")
    except CustomUser.DoesNotExist:
        print("❌ کاربر یافت نشد")
        return
    
    # نمایش پست‌های سطح بالا
    high_level_posts = Post.objects.filter(
        name__in=['هیئت مدیره', 'مدیر عامل شرکت', 'معاونت مالی/اداری دفتر مرکزی'],
        is_active=True
    ).order_by('level', 'name')
    
    print(f"\n📋 پست‌های سطح بالا:")
    for i, post in enumerate(high_level_posts, 1):
        print(f"   {i}. {post.name} (سطح: {post.level}, سازمان: {post.organization.name})")
    
    # انتخاب پست
    try:
        post_choice = int(input("شماره پست: ")) - 1
        if 0 <= post_choice < len(high_level_posts):
            selected_post = high_level_posts[post_choice]
            print(f"📌 پست انتخاب شده: {selected_post.name}")
            
            # بررسی وجود قبلی
            existing_userpost = UserPost.objects.filter(
                user=user,
                post=selected_post,
                is_active=True
            ).exists()
            
            if existing_userpost:
                print("⚠️  کاربر قبلاً در این پست است")
                return
            
            # تأیید اضافه کردن
            confirm = input("آیا مطمئن هستید؟ (y/N): ").strip().lower()
            if confirm == 'y':
                UserPost.objects.create(
                    user=user,
                    post=selected_post,
                    start_date=date.today(),
                    is_active=True
                )
                print(f"✅ دسترسی تایید به کاربر {user.username} اضافه شد")
            else:
                print("❌ عملیات لغو شد")
        else:
            print("❌ انتخاب نامعتبر")
    except ValueError:
        print("❌ لطفاً عدد وارد کنید")

def show_user_permissions():
    """نمایش دسترسی‌های فعلی کاربر"""
    print(f"\n👤 نمایش دسترسی‌های کاربر")
    print("-" * 40)
    
    username = input("نام کاربری: ").strip()
    try:
        user = CustomUser.objects.get(username=username)
        print(f"👤 کاربر: {user.username} ({user.first_name} {user.last_name})")
    except CustomUser.DoesNotExist:
        print("❌ کاربر یافت نشد")
        return
    
    # نمایش پست‌های کاربر
    user_posts = UserPost.objects.filter(
        user=user,
        is_active=True,
        end_date__isnull=True
    ).select_related('post', 'post__organization')
    
    if not user_posts.exists():
        print("❌ کاربر هیچ پست فعالی ندارد")
        return
    
    print(f"\n📋 پست‌های فعال:")
    for user_post in user_posts:
        print(f"   📌 {user_post.post.name}")
        print(f"      سازمان: {user_post.post.organization.name}")
        print(f"      سطح: {user_post.post.level}")
        
        # نمایش اقدامات مجاز
        post_actions = PostAction.objects.filter(
            post=user_post.post,
            entity_type='PAYMENTORDER',
            is_active=True
        ).select_related('stage')
        
        if post_actions.exists():
            print(f"      ⚡ اقدامات مجاز:")
            for action in post_actions:
                print(f"         - {action.action_type} در {action.stage.name}")
        else:
            print(f"      ❌ هیچ اقدام مجازی برای دستور پرداخت ندارد")

def show_all_permissions():
    """نمایش همه دسترسی‌های تایید"""
    print(f"\n📋 همه دسترسی‌های تایید")
    print("-" * 40)
    
    # نمایش PostAction ها
    post_actions = PostAction.objects.filter(
        entity_type='PAYMENTORDER',
        is_active=True
    ).select_related('post', 'stage').order_by('post__name', 'action_type')
    
    print(f"📋 PostAction ها ({post_actions.count()}):")
    for action in post_actions:
        print(f"   📌 {action.post.name}: {action.action_type} در {action.stage.name}")
    
    # نمایش کاربران مجاز
    print(f"\n👥 کاربران مجاز برای تایید:")
    high_level_posts = Post.objects.filter(
        name__in=['هیئت مدیره', 'مدیر عامل شرکت', 'معاونت مالی/اداری دفتر مرکزی'],
        is_active=True
    )
    
    for post in high_level_posts:
        users_in_post = UserPost.objects.filter(
            post=post,
            is_active=True,
            end_date__isnull=True
        ).select_related('user')
        
        if users_in_post.exists():
            print(f"   📌 {post.name}:")
            for user_post in users_in_post:
                print(f"      👤 {user_post.user.username} ({user_post.user.first_name} {user_post.user.last_name})")

if __name__ == "__main__":
    manage_approval_permissions()


