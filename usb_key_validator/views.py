import hashlib
import os
import platform
from time import timezone

import pythoncom
import win32file
import win32con
import wmi
from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from requests import request

from accounts.models import TimeLockModel
from .forms import USBKeyForm, write_license_file_to_usb, read_license_file_from_usb
import logging
logger = logging.getLogger(__name__)
#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
from django.shortcuts import render
def find_usb_drives():
    """شناسایی درایوهای USB با wmi (ویندوز)"""
    if os.name != 'nt':
        logger.warning("شناسایی USB فقط در ویندوز پشتیبانی می‌شود.")
        return []
    try:
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
        c = wmi.WMI()
        usb_drives = []
        for disk in c.Win32_DiskDrive():
            if "USB" in disk.MediaType.upper() or disk.InterfaceType == "USB":
                device_id = f"\\\\.\\PhysicalDrive{disk.Index}"
                for partition in disk.associators(wmi_result_class="Win32_DiskPartition"):
                    for logical_disk in partition.associators(wmi_result_class="Win32_LogicalDisk"):
                        drive_letter = logical_disk.DeviceID
                        usb_drives.append({
                            'device_id': device_id,
                            'drive_letter': drive_letter,
                            'caption': disk.Caption,
                            'index': disk.Index
                        })
        if not usb_drives:
            logger.warning("هیچ درایو USB متصلی یافت نشد.")
        return usb_drives
    except Exception as e:
        logger.error(f"خطا در شناسایی USB: {e}")
        return []
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass

def write_to_sector(device, sector_number, data):
    """نوشتن داده در سکتور خاص (ویندوز)"""
    if os.name != 'nt':
        logger.error("نوشتن در سکتور فقط در ویندوز پشتیبانی می‌شود.")
        return False
    try:
        handle = win32file.CreateFile(
            device, win32con.GENERIC_WRITE, win32con.FILE_SHARE_WRITE,
            None, win32con.OPEN_EXISTING, 0, None
        )
        win32file.SetFilePointer(handle, sector_number * 512, win32file.FILE_BEGIN)
        win32file.WriteFile(handle, data, None)
        win32file.CloseHandle(handle)
        logger.info(f"کلید در سکتور {sector_number} نوشته شد: {device}")
        return True
    except Exception as e:
        logger.error(f"خطا در نوشتن سکتور {sector_number}: {e}")
        return False

def read_from_sector(device_path, sector_number, length):
    """خواندن داده از سکتور خاص (همه سیستم‌عامل‌ها)"""
    try:
        if os.name == 'nt':
            handle = win32file.CreateFile(
                device_path, win32con.GENERIC_READ, win32con.FILE_SHARE_READ,
                None, win32con.OPEN_EXISTING, 0, None
            )
            win32file.SetFilePointer(handle, sector_number * 512, win32file.FILE_BEGIN)
            data, _ = win32file.ReadFile(handle, length, None)
            win32file.CloseHandle(handle)
        else:
            with open(device_path, 'rb') as f:
                f.seek(sector_number * 512)
                data = f.read(length)
        return data
    except Exception as e:
        logger.error(f"خطا در خواندن سکتور {sector_number}: {e}")
        return None

def find_writable_sector(device, data, start_sector=100, max_attempts=10):
    """یافتن اولین سکتور قابل نوشتن (ویندوز)"""
    if os.name != 'nt':
        return None
    for sector in range(start_sector, start_sector + max_attempts):
        if write_to_sector(device, sector, data):
            return sector
    return None



########################%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def validate_usb_key(request):
    usb_drives = find_usb_drives() if os.name == 'nt' else []

    if request.method == 'POST':
        form = USBKeyForm(request.POST)
        if form.is_valid():
            device = form.cleaned_data['usb_device']
            if not device:
                messages.error(request, _("لطفاً یک USB انتخاب کنید."))
                return HttpResponseRedirect(reverse('usb_key_validator:validate'))
            try:
                # دریافت آخرین قفل از دیتابیس
                latest_lock = TimeLockModel.objects.filter(is_active=True).order_by('-created_at').first()
                if not latest_lock:
                    messages.error(request, _("هیچ قفل فعالی در دیتابیس یافت نشد."))
                    logger.warning("No active lock found in TimeLockModel")
                    return HttpResponseRedirect(reverse('usb_key_validator:validate'))

                # اعتبارسنجی کلید با هش
                db_key = latest_lock.lock_key.encode()
                logging.info(f'db_key {db_key}')
                hash_value = latest_lock.hash_value
                logger.info(f'hash_value {hash_value}')
                expected_hash = hashlib.sha256(db_key).hexdigest()
                logger.info(f'expected_hash {expected_hash}')
                if hash_value != expected_hash:
                    messages.error(request, _("هش کلید دیتابیس نامعتبر است."))
                    logger.error(f"Hash mismatch for lock ID {latest_lock.id}")
                    return HttpResponseRedirect(reverse('usb_key_validator:validate'))

                # استخراج اطلاعات رمزگشایی‌شده
                expiry_date, max_users, organization_name = latest_lock.get_decrypted_data()
                decrypted_data = {
                    'expiry_date': expiry_date if expiry_date else _("نامعتبر"),
                    'max_users': max_users if max_users is not None else _("نامعتبر"),
                    'organization_name': organization_name if organization_name else _("نامعتبر")
                }

                # نوشتن کلید در USB (ویندوز)
                write_result = False
                write_message = ""
                sector = None
                if os.name == 'nt':
                    sector = find_writable_sector(device, db_key)
                    write_result = sector is not None
                    write_message = f"کلید در سکتور {sector} نوشته شد." if write_result else "خطا در نوشتن کلید در USB."
                else:
                    write_message = "نوشتن کلید فقط در ویندوز پشتیبانی می‌شود."
                    messages.error(request, _(write_message))
                    return HttpResponseRedirect(reverse('usb_key_validator:validate'))

                # خواندن کلید از USB
                usb_key = read_from_sector(device, sector if sector else 100, 1024) if write_result else None
                if not usb_key:
                    messages.error(request, _("خطا در خواندن کلید از USB."))
                    logger.error(f"Failed to read key from sector {sector or 100}: {device}")
                    return HttpResponseRedirect(reverse('usb_key_validator:validate'))

                # تطبیق کلیدها
                is_valid = usb_key == db_key
                # کوتاه کردن کلید برای نمایش امن
                db_key_display = latest_lock.lock_key[:10] + "..." if len(
                    latest_lock.lock_key) > 10 else latest_lock.lock_key
                usb_key_display = usb_key.decode('utf-8', errors='ignore')[:10] + "..." if usb_key else _("خوانده نشد")

                return render(request, 'usb_key_validator/validate_key.html', {
                    'form': form,
                    'title': _('بررسی کلید USB'),
                    'usb_drives': usb_drives,
                    'result': {
                        'write_result': write_result,
                        'write_message': write_message,
                        'is_valid': is_valid,
                        'decrypted_data': decrypted_data,
                        'db_key': db_key_display,
                        'usb_key': usb_key_display
                    }
                })

            except Exception as e:
                messages.error(request, _("خطا در پردازش: {}").format(str(e)))
                logger.error(f"Error processing USB key: {e}")
                return HttpResponseRedirect(reverse('usb_key_validator:validate'))
    else:
        form = USBKeyForm()

    return render(request, 'usb_key_validator/validate_key.html', {
        'form': form,
        'title': _('بررسی کلید USB'),
        'usb_drives': usb_drives
    })

########################%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#
# def write_to_sector(device, sector_number, data):
#     """نوشتن داده در سکتور خاص USB"""
#     try:
#         handle = win32file.CreateFile(
#             device, win32con.GENERIC_WRITE, win32con.FILE_SHARE_WRITE,
#             None, win32con.OPEN_EXISTING, 0, None
#         )
#         win32file.SetFilePointer(handle, sector_number * 512, win32file.FILE_BEGIN)
#         win32file.WriteFile(handle, data, None)
#         win32file.CloseHandle(handle)
#         return True
#     except Exception as e:
#         logger.error(f"خطا در نوشتن سکتور: {e}")
#         return False
#
# def read_from_sector(device, sector_number, length):
#     """خواندن داده از سکتور خاص USB"""
#     try:
#         # در validate_usb_key
#         device = find_usb_drives()
#         if not device:
#             messages.error(request, ("هیچ USB متصلی یافت نشد."))
#             logger.error("No USB device found")
#             return HttpResponseRedirect(reverse('usb_key_validator:validate'))
#
#         handle = win32file.CreateFile(
#             device, win32con.GENERIC_READ, win32con.FILE_SHARE_READ,
#             None, win32con.OPEN_EXISTING, 0, None
#         )
#         win32file.SetFilePointer(handle, sector_number * 512, win32file.FILE_BEGIN)
#         data, _ = win32file.ReadFile(handle, length, None)
#         win32file.CloseHandle(handle)
#         return data
#     except Exception as e:
#         logger.error(f"خطا در خواندن سکتور: {e}")
#         return None
#
# # -Linux View
#
#
# # کلید Fernet اصلی که در settings.py مقداردهی شده
# try:
#     # این cipher برای رمزگشایی lock_key از TimeLockModel استفاده می‌شود
#     cipher = settings.RCMS_SECRET_KEY
# except AttributeError:
#     logger.error("settings.RCMS_SECRET_KEY_CIPHER not set. Functionality will be limited.")
#     cipher = None  # Fallback for development, will cause decryption errors
#
#
#
# #----
# # licensing/views.py
#
# from django.shortcuts import render, redirect
# from django.contrib.auth.decorators import user_passes_test
# from django.contrib import messages
# from datetime import date, datetime
# import os
# import json
# import logging
# from cryptography.fernet import Fernet  # برای تولید کلید در زمان نیاز
#
# from django.conf import settings
# from django.utils.translation import gettext_lazy as _
#
# # از accounts.models برای دسترسی به TimeLockModel و ActiveUser
# from accounts.models import TimeLockModel, ActiveUser
# from core.RCMS_Lock.security import TimeLock  # کلاس TimeLock
#
# # ایمپورت فرم‌ها
# from .forms import TimeLockForm, USBManagementForm
#
# # برای استفاده از تابع get_removable_drives در این ویو (که در forms.py تعریف شده)
# from .forms import get_removable_drives
#
# logger = logging.getLogger(__name__)
#
#
# # ... (superuser_required decorator شما) ...
# # دکوراتور برای اطمینان از دسترسی فقط توسط سوپریوزر
# def superuser_required(function=None, redirect_field_name=None, login_url='/admin/login/'):
#     actual_decorator = user_passes_test(
#         lambda u: u.is_active and u.is_superuser,
#         login_url=login_url,
#         redirect_field_name=redirect_field_name
#     )
#     if function:
#         return actual_decorator(function)
#     return actual_decorator
#
# # ویو set_lock_view (بدون تغییر عمده)
# @superuser_required
# def set_lock_view(request):
#     latest_lock_expiry, latest_lock_users, _, latest_org_name = TimeLockModel.get_latest_lock()
#
#     default_max_users_from_settings = getattr(settings, 'MAX_ACTIVE_USERS', 2)
#     default_org_name_from_settings = getattr(settings, 'ORGANIZATION_NAME', _("پیش‌فرض"))
#
#     if request.method == 'POST':
#         form = TimeLockForm(request.POST)
#         if form.is_valid():
#             try:
#                 form.save()
#                 messages.success(request, _("قفل سیستم با موفقیت تنظیم شد و قفل‌های قبلی غیرفعال شدند."))
#                 return redirect('licensing:lock_status')
#             except Exception as e:
#                 messages.error(request, _(f"خطا در تنظیم قفل سیستم: {str(e)}"))
#         else:
#             messages.error(request, _("خطا در اطلاعات ورودی فرم."))
#     else:
#         initial_data = {}
#         if latest_lock_expiry and latest_lock_users is not None:
#             initial_data = {
#                 'expiry_date': latest_lock_expiry,
#                 'max_users': latest_lock_users,
#                 'organization_name': latest_org_name
#             }
#         else:
#             initial_data = {
#                 'max_users': default_max_users_from_settings,
#                 'organization_name': default_org_name_from_settings
#             }
#         form = TimeLockForm(initial=initial_data)
#
#     context = {
#         'form': form,
#         'latest_lock_expiry': latest_lock_expiry,
#         'latest_lock_users': latest_lock_users,
#         'latest_org_name': latest_org_name,
#         'default_max_users_from_settings': default_max_users_from_settings,
#         'default_org_name_from_settings': default_org_name_from_settings,
#     }
#     return render(request, 'licensing/set_lock.html', context)
#
#
# # ویو lock_status_view (بدون تغییر عمده)
# @superuser_required
# def lock_status_view(request):
#     is_locked = TimeLock.is_locked(request=request)
#     expiry_date = TimeLock.get_expiry_date()
#     max_users = TimeLock.get_max_users()
#     organization_name = TimeLock.get_organization_name()
#     hash_value = TimeLock._hash_value_cache
#
#     active_users_count = ActiveUser.objects.filter(
#         last_activity__gte=timezone.now() - datetime.timedelta(
#             minutes=getattr(settings, 'ACTIVE_USER_INACTIVITY_THRESHOLD_MINUTES', 10))
#     ).values("user").distinct().count()
#
#     context = {
#         'is_locked': is_locked,
#         'expiry_date': expiry_date,
#         'max_users': max_users,
#         'organization_name': organization_name,
#         'current_date': date.today(),
#         'hash_value': hash_value,
#         'active_users_count': active_users_count,
#     }
#     return render(request, 'licensing/lock_status.html', context)
#
#
# # ----------------------------------------------------------------------
# # ویو جدید برای مدیریت لایسنس USB
# # ----------------------------------------------------------------------
#
# # از توابع ذخیره و لود از اسکریپت usb_license_manager.py استفاده می‌کنیم.
# # این توابع را در اینجا import می‌کنیم تا در views.py قابل دسترسی باشند.
# # این توابع به دسترسی ادمین/روت نیاز دارند، اما ما در اینجا از طریق ویو جنگو اجرا می‌کنیم.
# # این یعنی کاربر جنگو که این ویو را اجرا می‌کند، باید دسترسی کافی در سیستم عامل را داشته باشد.
# # در لینوکس، این یعنی کاربر Gunicorn باید توانایی نوشتن در فلش داشته باشد،
# # یا نیاز به یک سرویس کمکی (Helper Service) با پرمیژن‌های محدود دارید.
# # برای سادگی، فعلاً فرض می‌کنیم کاربر Gunicorn به فلش دسترسی دارد.
#
# # همان توابعی که در scripts/usb_license_manager.py تعریف کردیم را اینجا دوباره تعریف می‌کنیم
# # چون نمی‌خواهیم به آن اسکریپت مستقیماً وابسته باشیم.
# # البته اگر آن اسکریپت را به عنوان یک پکیج در دسترس قرار دهیم، بهتر است import شود.
#
# # نام فایل و دایرکتوری مخفی برای ذخیره لایسنس روی فلش (باید با اسکریپت CLI یکسان باشد)
# LICENSE_DIR_NAME = ".rcms_license"
# LICENSE_FILE_NAME = "rcms_license.dat"
#
#
# def _save_license_data_to_usb(drive_path, fernet_key, max_users, organization_name):
#     """ذخیره کلید Fernet و اطلاعات لایسنس در فایل JSON روی فلش."""
#     try:
#         license_data = {
#             "fernet_key": fernet_key,
#             "max_active_users": max_users,
#             "organization_name": organization_name,
#             "created_at": datetime.now().isoformat()
#         }
#
#         license_dir = os.path.join(drive_path, LICENSE_DIR_NAME)
#         os.makedirs(license_dir, exist_ok=True)
#
#         license_file_path = os.path.join(license_dir, LICENSE_FILE_NAME)
#
#         with open(license_file_path, 'w') as f:
#             json.dump(license_data, f, indent=4)
#
#         # تنظیم پرمیژن‌های فایل (برای لینوکس) - این کار نیاز به دسترسی Root در زمان اجرای django/gunicorn دارد
#         # که در محیط‌های پروداکشن معمولا انجام نمی‌شود.
#         # فرض می‌کنیم دایرکتوری mount شده قبلاً مجوزهای درستی دارد.
#         if os.name == "posix":  # فقط برای سیستم عامل‌های شبه یونیکس (لینوکس)
#             os.chmod(license_file_path, 0o600)
#             os.chmod(license_dir, 0o700)
#             logger.info(f"Permissions set for {license_file_path} and {license_dir}")
#
#         logger.info(f"داده‌های لایسنس با موفقیت در '{license_file_path}' ذخیره شد.")
#         return True
#     except Exception as e:
#         logger.error(f"خطا در ذخیره داده‌های لایسنس به USB: {e}", exc_info=True)
#         return False
#
#
# def _load_license_data_from_usb(drive_path):
#     """خواندن کلید Fernet و اطلاعات لایسنس از فایل JSON روی فلش."""
#     license_file_path = os.path.join(drive_path, LICENSE_DIR_NAME, LICENSE_FILE_NAME)
#     if not os.path.exists(license_file_path):
#         logger.warning(f"فایل لایسنس در '{license_file_path}' یافت نشد.")
#         return None
#
#     try:
#         with open(license_file_path, 'r') as f:
#             license_data = json.load(f)
#         logger.info(f"داده‌های لایسنس با موفقیت از '{license_file_path}' خوانده شد.")
#         return license_data
#     except json.JSONDecodeError as e:
#         logger.error(f"خطا در خواندن فایل JSON لایسنس: {e}. فایل ممکن است خراب باشد.", exc_info=True)
#         return None
#     except Exception as e:
#         logger.error(f"خطا در خواندن داده‌های لایسنس از USB: {e}", exc_info=True)
#         return None
#
#
# @superuser_required
# def manage_usb_license_view(request):
#     form = USBManagementForm()
#     usb_drives = get_removable_drives()  # لیست درایوهای شناسایی شده
#
#     current_fernet_key_from_settings = getattr(settings, 'RCMS_SECRET_KEY', _("یافت نشد"))
#     current_max_users_from_settings = getattr(settings, 'MAX_ACTIVE_USERS', 2)
#     current_org_name_from_settings = getattr(settings, 'ORGANIZATION_NAME', _("پیش‌فرض"))
#     current_license_file_path_from_settings = getattr(settings, 'RCMS_LICENSE_CONFIG_PATH', _("مسیر نامشخص"))
#
#     if request.method == 'POST':
#         action = request.POST.get('action')
#         selected_drive_path = request.POST.get('usb_device')
#
#         if not selected_drive_path:
#             messages.error(request, _("لطفاً یک درایو USB را انتخاب کنید."))
#             # فرم را با مقادیر پر می‌کنیم تا کاربر دوباره پر نکند
#             form = USBManagementForm(request.POST)
#             # اما فیلد usb_device دوباره پر شود
#             form.fields['usb_device'].choices = [(d['path'], d['caption']) for d in usb_drives] if usb_drives else [
#                 ('', _('هیچ درایو Removable (USB) یافت نشد.'))]
#             if not usb_drives: form.fields['usb_device'].disabled = True
#
#             return render(request, 'usb_key_validator/manage_usb_license.html', {
#                 'form': form,
#                 'usb_drives': usb_drives,
#                 'current_fernet_key_from_settings': current_fernet_key_from_settings,
#                 'current_max_users_from_settings': current_max_users_from_settings,
#                 'current_org_name_from_settings': current_org_name_from_settings,
#                 'current_license_file_path_from_settings': current_license_file_path_from_settings,
#             })
#
#         if action == 'generate_and_save':
#             # تولید یک کلید Fernet جدید
#             new_fernet_key = Fernet.generate_key().decode()
#
#             # خواندن مقادیر max_users و organization_name از تنظیمات فعلی
#             # اینها مقادیری هستند که در فایل config/license_config.json ذخیره خواهند شد
#             max_users_to_save = current_max_users_from_settings
#             org_name_to_save = current_org_name_from_settings
#
#             if _save_license_data_to_usb(selected_drive_path, new_fernet_key, max_users_to_save, org_name_to_save):
#                 messages.success(request,
#                                  _(f"لایسنس جدید با کلید '{new_fernet_key}' و تنظیمات فعلی سیستم، با موفقیت در USB ذخیره شد."))
#                 messages.info(request,
#                               _("**توجه:** برای اعمال تغییرات در سیستم اصلی، لطفاً فایل 'rcms_license.dat' را از این فلش به مسیر اصلی کانفیگ سیستم (`{}`) کپی کنید و سرویس را راه‌اندازی مجدد کنید.").format(
#                                   current_license_file_path_from_settings))
#             else:
#                 messages.error(request,
#                                _("خطا در تولید و ذخیره لایسنس جدید در USB. از دسترسی نوشتن به درایو اطمینان حاصل کنید."))
#
#         elif action == 'read_and_display':
#             license_data_from_usb = _load_license_data_from_usb(selected_drive_path)
#             if license_data_from_usb:
#                 messages.success(request, _("لایسنس از USB با موفقیت خوانده شد:"))
#                 messages.info(request, _(f"  کلید Fernet: {license_data_from_usb.get('fernet_key', 'N/A')}<br>"
#                                          f"  حداکثر کاربران: {license_data_from_usb.get('max_active_users', 'N/A')}<br>"
#                                          f"  نام مجموعه: {license_data_from_usb.get('organization_name', 'N/A')}<br>"
#                                          f"  زمان ایجاد: {license_data_from_usb.get('created_at', 'N/A')}"))
#             else:
#                 messages.error(request, _("خطا در خواندن لایسنس از USB یا فایل یافت نشد."))
#
#         elif action == 'copy_to_system_config':
#             license_data_from_usb = _load_license_data_from_usb(selected_drive_path)
#             if license_data_from_usb:
#                 try:
#                     with open(settings.RCMS_LICENSE_CONFIG_PATH, 'w') as f:
#                         json.dump(license_data_from_usb, f, indent=4)
#
#                     # تنظیم پرمیژن‌ها برای فایل کانفیگ سیستم
#                     if os.name == "posix":
#                         os.chmod(settings.RCMS_LICENSE_CONFIG_PATH, 0o600)
#                         # os.chown(settings.RCMS_LICENSE_CONFIG_PATH, owner_uid, group_gid) # اگر نیاز به تغییر مالکیت دقیق دارید
#
#                     messages.success(request,
#                                      _(f"لایسنس از USB با موفقیت به مسیر کانفیگ سیستم ('{settings.RCMS_LICENSE_CONFIG_PATH}') کپی شد."))
#                     messages.info(request,
#                                   _("**توجه:** برای اعمال تغییرات، لطفاً سرویس اصلی نرم‌افزار را راه‌اندازی مجدد کنید (مثلاً gunicorn)."))
#                 except Exception as e:
#                     messages.error(request, _(f"خطا در کپی لایسنس به مسیر کانفیگ سیستم: {str(e)}"))
#             else:
#                 messages.error(request, _("خطا در خواندن لایسنس از USB برای کپی به سیستم."))
#
#     context = {
#         'form': form,
#         'usb_drives': usb_drives,
#         'current_fernet_key_from_settings': current_fernet_key_from_settings,
#         'current_max_users_from_settings': current_max_users_from_settings,
#         'current_org_name_from_settings': current_org_name_from_settings,
#         'current_license_file_path_from_settings': current_license_file_path_from_settings,
#     }
#     return render(request, 'usb_key_validator/manage_usb_license.html', context)
# #---
# # ویو set_lock_view (بدون تغییر عمده)
# @superuser_required
# def set_lock_view(request):
#     latest_lock_expiry, latest_lock_users, _, latest_org_name = TimeLockModel.get_latest_lock()
#
#     default_max_users_from_settings = getattr(settings, 'MAX_ACTIVE_USERS', 2)
#     default_org_name_from_settings = getattr(settings, 'ORGANIZATION_NAME', _("پیش‌فرض"))
#
#     if request.method == 'POST':
#         form = TimeLockForm(request.POST)
#         if form.is_valid():
#             try:
#                 form.save()
#                 messages.success(request, _("قفل سیستم با موفقیت تنظیم شد و قفل‌های قبلی غیرفعال شدند."))
#                 return redirect('licensing:lock_status')
#             except Exception as e:
#                 messages.error(request, _(f"خطا در تنظیم قفل سیستم: {str(e)}"))
#         else:
#             messages.error(request, _("خطا در اطلاعات ورودی فرم."))
#     else:
#         initial_data = {}
#         if latest_lock_expiry and latest_lock_users is not None:
#             initial_data = {
#                 'expiry_date': latest_lock_expiry,
#                 'max_users': latest_lock_users,
#                 'organization_name': latest_org_name
#             }
#         else:
#             initial_data = {
#                 'max_users': default_max_users_from_settings,
#                 'organization_name': default_org_name_from_settings
#             }
#         form = TimeLockForm(initial=initial_data)
#
#     context = {
#         'form': form,
#         'latest_lock_expiry': latest_lock_expiry,
#         'latest_lock_users': latest_lock_users,
#         'latest_org_name': latest_org_name,
#         'default_max_users_from_settings': default_max_users_from_settings,
#         'default_org_name_from_settings': default_org_name_from_settings,
#     }
#     return render(request, 'licensing/set_lock.html', context)
#
#
# # ویو lock_status_view (بدون تغییر عمده)
# @superuser_required
# def lock_status_view(request):
#     is_locked = TimeLock.is_locked(request=request)
#     expiry_date = TimeLock.get_expiry_date()
#     max_users = TimeLock.get_max_users()
#     organization_name = TimeLock.get_organization_name()
#     hash_value = TimeLock._hash_value_cache
#
#     active_users_count = ActiveUser.objects.filter(
#         last_activity__gte=timezone.now() - datetime.timedelta(
#             minutes=getattr(settings, 'ACTIVE_USER_INACTIVITY_THRESHOLD_MINUTES', 10))
#     ).values("user").distinct().count()
#
#     context = {
#         'is_locked': is_locked,
#         'expiry_date': expiry_date,
#         'max_users': max_users,
#         'organization_name': organization_name,
#         'current_date': date.today(),
#         'hash_value': hash_value,
#         'active_users_count': active_users_count,
#     }
#     return render(request, 'usb_key_validator/lock_status.html', context)
#
#
# # ----------------------------------------------------------------------
# # ویو جدید برای مدیریت لایسنس USB (هم در ویندوز و هم در لینوکس)
# # ----------------------------------------------------------------------
#
# @superuser_required
# def manage_usb_license_view(request):
#     usb_drives = get_removable_drives()  # لیست درایوهای شناسایی شده
#     form = USBManagementForm(initial={'new_max_users': getattr(settings, 'MAX_ACTIVE_USERS', 5),
#                                       'new_organization_name': getattr(settings, 'ORGANIZATION_NAME', _("پیش‌فرض"))})
#
#     current_fernet_key_from_settings = getattr(settings, 'RCMS_SECRET_KEY',
#                                                _("یافت نشد (خطا در لود)").encode())   # Decode to string
#     current_max_users_from_settings = getattr(settings, 'MAX_ACTIVE_USERS', 2)
#     current_org_name_from_settings = getattr(settings, 'ORGANIZATION_NAME', _("پیش‌فرض"))
#     current_license_config_path_from_settings = getattr(settings, 'RCMS_LICENSE_CONFIG_PATH', _("مسیر نامشخص"))
#
#     if request.method == 'POST':
#         form = USBManagementForm(request.POST)
#         action = request.POST.get('action')
#         selected_drive_path = request.POST.get('usb_device')
#
#         # اگر هیچ درایوی انتخاب نشده بود (درایوهای غیرفعال شده در فرم)
#         if not usb_drives and selected_drive_path == '':
#             messages.error(request, _("هیچ درایو USB متصلی یافت نشد."))
#             return render(request, 'usb_key_validator/manage_usb_license.html', {
#                 'form': form,
#                 'usb_drives': usb_drives,
#                 'current_fernet_key_from_settings': current_fernet_key_from_settings,
#                 'current_max_users_from_settings': current_max_users_from_settings,
#                 'current_org_name_from_settings': current_org_name_from_settings,
#                 'current_license_config_path_from_settings': current_license_config_path_from_settings,
#             })
#
#         if not form.is_valid() and action == 'generate_and_save':
#             messages.error(request, _("خطا در اطلاعات ورودی برای تولید لایسنس جدید."))
#         elif selected_drive_path:  # اطمینان حاصل شود که درایوی انتخاب شده است
#             if action == 'generate_and_save':
#                 new_fernet_key = Fernet.generate_key().decode()
#                 max_users_to_save = form.cleaned_data['new_max_users']
#                 org_name_to_save = form.cleaned_data['new_organization_name']
#
#                 license_data = {
#                     "fernet_key": new_fernet_key,
#                     "max_active_users": max_users_to_save,
#                     "organization_name": org_name_to_save,
#                     "created_at": datetime.now().isoformat()
#                 }
#
#                 if write_license_file_to_usb(selected_drive_path, license_data):
#                     messages.success(request, _(f"لایسنس جدید با موفقیت در USB '{selected_drive_path}' ذخیره شد."))
#                     messages.info(request,
#                                   _("**نکته:** برای اعمال این لایسنس در سیستم اصلی، لطفاً فایل 'rcms_license.dat' را از دایرکتوری '.rcms_license' در این فلش به مسیر کانفیگ سیستم (`{}`) کپی کنید و سرویس اصلی را راه‌اندازی مجدد کنید.").format(
#                                       current_license_config_path_from_settings))
#                 else:
#                     messages.error(request,
#                                    _("خطا در ذخیره لایسنس جدید در USB. از دسترسی نوشتن به درایو اطمینان حاصل کنید."))
#
#             elif action == 'read_and_display':
#                 license_data_from_usb = read_license_file_from_usb(selected_drive_path)
#                 if license_data_from_usb:
#                     messages.success(request, _("لایسنس از USB با موفقیت خوانده شد:"))
#                     messages.info(request, _(f"  کلید Fernet: {license_data_from_usb.get('fernet_key', 'N/A')}<br>"
#                                              f"  حداکثر کاربران: {license_data_from_usb.get('max_active_users', 'N/A')}<br>"
#                                              f"  نام مجموعه: {license_data_from_usb.get('organization_name', 'N/A')}<br>"
#                                              f"  زمان ایجاد: {license_data_from_usb.get('created_at', 'N/A')}"))
#                 else:
#                     messages.error(request, _("خطا در خواندن لایسنس از USB یا فایل یافت نشد."))
#
#             elif action == 'copy_to_system_config':
#                 license_data_from_usb = read_license_file_from_usb(selected_drive_path)
#                 if license_data_from_usb:
#                     try:
#                         # مسیر فایل کانفیگ سیستم (در سرور اصلی)
#                         system_config_path = settings.RCMS_LICENSE_CONFIG_PATH
#
#                         # در اینجا نیازی به `sudo` نیست اگر django_user مالک `RCMS_LICENSE_CONFIG_PATH` باشد.
#                         # اما ممکن است در محیط سرور اصلی، این عملیات نیاز به سطح دسترسی بالاتری داشته باشد.
#                         # این بخش باید در سرور اصلی لینوکس با دسترسی کافی اجرا شود.
#                         # روی لپ‌تاپ ویندوزی (محیط dev) معمولا مجوزها مشکلی ندارند.
#                         with open(system_config_path, 'w', encoding='utf-8') as f:
#                             json.dump(license_data_from_usb, f, indent=4, ensure_ascii=False)
#
#                         # تنظیم مجوزها برای فایل کانفیگ سیستم
#                         if platform.system() == "Linux":
#                             # این عملیات در محیط پروداکشن لینوکس نیاز به sudo دارد.
#                             # اگر این ویو در لپ‌تاپ ویندوزی اجرا می‌شود، این بخش تاثیری ندارد.
#                             # اگر این ویو در سرور لینوکسی اجرا شود، کاربر gunicorn باید دسترسی root برای chown/chmod داشته باشد که امن نیست.
#                             # بهترین کار این است که این "کپی به سیستم" به صورت دستی یا با یک اسکریپت root در سرور لینوکس انجام شود.
#                             os.chmod(system_config_path, 0o600)
#                             # os.chown(system_config_path, owner_uid, group_gid) # اگر نیاز به تغییر مالکیت دقیق دارید
#
#                         messages.success(request,
#                                          _(f"لایسنس از USB با موفقیت به مسیر کانفیگ سیستم ('{system_config_path}') کپی شد."))
#                         messages.info(request,
#                                       _("**توجه:** برای اعمال تغییرات، لطفاً سرویس اصلی نرم‌افزار را راه‌اندازی مجدد کنید (مثلاً gunicorn)."))
#                     except Exception as e:
#                         messages.error(request, _(f"خطا در کپی لایسنس به مسیر کانفیگ سیستم: {str(e)}"))
#                         logger.error(f"خطا در کپی لایسنس به سیستم کانفیگ: {e}", exc_info=True)
#                 else:
#                     messages.error(request, _("خطا در خواندن لایسنس از USB برای کپی به سیستم."))
#
#         # فرم را دوباره پر می‌کنیم تا وضعیت فعلی درایوها را نمایش دهد
#         form = USBManagementForm(initial={'new_max_users': form.cleaned_data.get('new_max_users', 5),
#                                           'new_organization_name': form.cleaned_data.get('new_organization_name',
#                                                                                          _("پیش‌فرض"))})
#
#     context = {
#         'form': form,
#         'usb_drives': usb_drives,
#         'current_fernet_key_from_settings': current_fernet_key_from_settings,
#         'current_max_users_from_settings': current_max_users_from_settings,
#         'current_org_name_from_settings': current_org_name_from_settings,
#         'current_license_config_path_from_settings': current_license_config_path_from_settings,
#     }
#     return render(request, 'usb_key_validator/manage_usb_license.html', context)