# core/RCMS_Lock/security.py
import datetime
import secrets

from accounts.models import ActiveUser
from accounts.models import TimeLockModel
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings
import logging
logger = logging.getLogger(__name__)
from django.core.cache import cache


class TimeLock:
    _expiry_cache = None
    _max_users_cache = None
    _organization_name_cache = None  # اضافه کردن کش برای نام مجموعه
    CACHE_KEY = "time_lock_status"
    CACHE_TIMEOUT = 10  # 10 ثانیه


    @classmethod
    def set_expiry_date(cls, expiry_date: datetime.date, max_users: int, organization_name: str = "") -> bool:
        try:
            salt = secrets.token_hex(16)
            lock_key = TimeLockModel.create_lock_key(expiry_date, max_users, salt, organization_name)
            hash_value = hashlib.sha256(f"{expiry_date.isoformat()}-{max_users}-{salt}-{organization_name}".encode()).hexdigest()
            TimeLockModel.objects.create(
                lock_key=lock_key,
                hash_value=hash_value,
                salt=salt,
                organization_name=organization_name
            )
            cls._expiry_cache = expiry_date
            cls._max_users_cache = max_users
            cls._organization_name_cache = organization_name  # ذخیره نام مجموعه در کش
            return True
        except Exception as e:
            print(f"🔴 خطا در تنظیم قفل: {str(e)}")
            return False

    @classmethod
    def get_expiry_date(cls, force_refresh=False) -> datetime.date:
        if not force_refresh and cls._expiry_cache:
            return cls._expiry_cache
        expiry_date, max_users, _, organization_name = TimeLockModel.get_latest_lock()
        cls._expiry_cache = expiry_date
        cls._max_users_cache = max_users
        cls._organization_name_cache = organization_name
        return expiry_date if expiry_date else None

    @classmethod
    def get_max_users(cls, force_refresh=False) -> int:
        """
               تعداد حداکثر کاربران را برمی‌گرداند. اولویت با TimeLockModel است، در غیر این صورت از settings استفاده می‌شود.
        """
        if not force_refresh and cls._max_users_cache is not None:
            return cls._max_users_cache

        # گرفتن آخرین قفل از TimeLockModel
        _, max_users, _, organization_name = TimeLockModel.get_latest_lock()

        # اگر مقدار معتبر از TimeLockModel وجود داشت، از آن استفاده کن
        if max_users is not None:
            cls._max_users_cache = max_users
            cls._organization_name_cache = organization_name
            return max_users

        # در غیر این صورت، از تنظیمات پیش‌فرض استفاده کن
        default_max_users = getattr(settings, 'MAX_ACTIVE_USERS', 4)  # مقدار پیش‌فرض 4
        cls._max_users_cache = default_max_users
        return default_max_users

    @classmethod
    def get_organization_name(cls, force_refresh=False) -> str:
        if not force_refresh and cls._organization_name_cache is not None:
            return cls._organization_name_cache
        _, _, _, organization_name = TimeLockModel.get_latest_lock()
        cls._organization_name_cache = organization_name
        return organization_name if organization_name else ""

    @classmethod
    def is_locked(cls, request=None) -> bool:
        # چک کردن کش
        cached_result = cache.get(cls.CACHE_KEY)
        if cached_result is not None:
            # logger.info(f"Using cached lock status: {cached_result}")
            return cached_result
        request_id = getattr(request, 'request_id', 'Unknown') if request else 'NoRequest'
        expiry_date = cls.get_expiry_date()
        max_users = cls.get_max_users()  # استفاده از متد اصلاح‌شده
        today = datetime.date.today()
        active_users_count = ActiveUser.objects.values("user").distinct().count()  # تعداد کاربران یکتا
        # logger.info(
        #     f"Checking lock: expiry={expiry_date}, max_users={max_users}, active_users={active_users_count}, today={today} [Request ID: {request_id}]")

        # اگر قفلی وجود ندارد، سیستم قفل شود
        # if expiry_date is None or max_users is None:
        #     return True  # قفل اجباری در صورت نبود قفل
        if expiry_date is None:
            # logger.warning("No expiry date found, locking system")
            result = True
        else:
            date_locked = today >= expiry_date
            users_locked = active_users_count >= max_users
            # logger.info(f"Date locked: {date_locked}, Users locked: {users_locked} [Request ID: {request_id}]")

            if request and request.user.is_superuser and users_locked and not date_locked:
                # logger.info(f"Superuser bypass: unlocking for user count [Request ID: {request_id}]")
                result = False
            else:
                result = date_locked or users_locked

        # date_locked = expiry_date is not None and today >= expiry_date
        # users_locked = active_users_count >= max_users
        #
        # # اگر کاربر سوپریوزر باشد و فقط محدودیت تعداد کاربران باشد، قفل نشود
        # if request and request.user.is_superuser and users_locked and not date_locked:
        #     return False
                # ذخیره در کش
        cache.set(cls.CACHE_KEY, result, cls.CACHE_TIMEOUT)
        return result

        # return date_locked or users_locked
# class TimeLock:
#     _expiry_cache = None  # برای کش کردن تاریخ انقضا
#
#     @classmethod
#     def set_expiry_date(cls, expiry_date: datetime.date) -> bool:
#         try:
#             os.makedirs(os.path.dirname(settings.TIME_LOCK_FILE), exist_ok=True)
#             fernet = Fernet(settings.RCMS_SECRET_KEY.encode())
#
#             date_str = expiry_date.isoformat().encode()
#             encrypted_date = fernet.encrypt(date_str)
#
#             with open(settings.TIME_LOCK_FILE, 'wb') as f:
#                 f.write(encrypted_date)
#
#             cls._expiry_cache = expiry_date  # آپدیت کش
#             print(f"✅ تاریخ قفل با موفقیت تنظیم شد: {expiry_date}")
#             return True
#         except Exception as e:
#             print(f"🔴 خطا در تنظیم تاریخ قفل: {str(e)}")
#             return False
#
#     @classmethod
#     def get_expiry_date(cls, force_refresh=False) -> datetime.date:
#         if not force_refresh and cls._expiry_cache:
#             return cls._expiry_cache
#
#         try:
#             if not os.path.exists(settings.TIME_LOCK_FILE):
#                 return None
#
#             fernet = Fernet(settings.RCMS_SECRET_KEY.encode())
#
#             with open(settings.TIME_LOCK_FILE, 'rb') as f:
#                 encrypted_date = f.read()
#
#             date_str = fernet.decrypt(encrypted_date).decode()
#             cls._expiry_cache = datetime.date.fromisoformat(date_str)
#             return cls._expiry_cache
#         except Exception as e:
#             print(f"🔴 خطا در دریافت تاریخ قفل: {e}")
#             return None
#
#     @classmethod
#     def is_locked(cls) -> bool:
#         expiry_date = cls.get_expiry_date()
#         today = datetime.date.today()
#         return expiry_date is not None and today >= expiry_date

'''
python manage.py shell 
1- 
from cryptography.fernet import Fernet
# تولید کلید ایمن
key = Fernet.generate_key()
# نمایش کلید تولید شده
print(key.decode())  

##############
from core.RCMS_Lock.security import TimeLock
import datetime

# تنظیم تاریخ جدید
TimeLock.set_expiry_date(datetime.date(2025, 2, 10))

# بررسی وضعیت قفل
print(TimeLock.get_expiry_date())
print(TimeLock.is_locked())

##############
 
🔹 برای امنیت بیشتر، می‌توان دسترسی به فایل را محدود کرد:
 chmod 600 /etc/myapp/lock.dat  # فقط کاربر root دسترسی دارد
 
  
 
from django.conf import settings
from core.RCMS_Lock.security import TimeLock
import datetime
import os

# دسترسی به متغیر TIME_LOCK_FILE
TIME_LOCK_FILE = settings.TIME_LOCK_FILE
print("مسیر فایل قفل:", TIME_LOCK_FILE)

# تنظیم تاریخ انقضا
TimeLock.set_expiry_date(datetime.date(2025, 2, 5))  # ✅ فایل جدید تولید میشود

# بررسی وجود فایل
if os.path.exists(TIME_LOCK_FILE):
    print("✅ فایل timelock.dat با موفقیت تولید شد!")
else:
    print("🔴 فایل تولید نشد! مشکل در کلید یا مسیر فایل است.")

'''
