import wmi
import win32file
import win32con
import pythoncom
import os
import io
import logging
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


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
                drive_letter = ""
                caption = disk.Caption
                for partition in disk.associators(wmi_result_class="Win32_DiskPartition"):
                    for logical_disk in partition.associators(wmi_result_class="Win32_LogicalDisk"):
                        drive_letter = logical_disk.DeviceID
                        break
                    if drive_letter:
                        break
                if drive_letter or "USB" in disk.MediaType.upper():
                    usb_drives.append({
                        'device_id': device_id,
                        'drive_letter': drive_letter or "N/A",
                        'caption': caption,
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



def get_device_path(drive_letter_or_device_id, os_name='nt'):
    """تبدیل drive_letter یا device_id به مسیر دستگاه"""
    if os_name == 'nt':
        return drive_letter_or_device_id  # برای ویندوز، device_id مستقیماً استفاده می‌شود
    else:
        # لینوکس/مک: فرض می‌کنیم device_path به‌صورت /dev/sdX است
        return drive_letter_or_device_id  # باید با ورودی مناسب جایگزین شود

# import wmi
# import win32file
# import win32con
# import logging
#
# logger = logging.getLogger(__name__)
# import wmi
# import win32file
# import win32con
# import pythoncom
# def find_usb_drives():
#     """شناسایی درایوهای USB با wmi"""
#     try:
#         pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
#         c = wmi.WMI()
#         usb_drives = []
#         for disk in c.Win32_DiskDrive():
#             if "USB" in disk.MediaType.upper():
#                 device_id = f"\\\\.\\{disk.DeviceID}"
#                 for partition in disk.associators(wmi_result_class="Win32_DiskPartition"):
#                     for logical_disk in partition.associators(wmi_result_class="Win32_LogicalDisk"):
#                         drive_letter = logical_disk.DeviceID
#                         usb_drives.append({
#                             'device_id': device_id,
#                             'drive_letter': drive_letter,
#                             'caption': disk.Caption
#                         })
#         return usb_drives
#     except Exception as e:
#         logger.error(f"خطا در شناسایی USB: {e}")
#         return []
#     finally:
#         pythoncom.CoUninitialize()
#
# def write_to_sector(device, sector_number, data):
#     """نوشتن داده در سکتور خاص"""
#     try:
#         handle = win32file.CreateFile(
#             device, win32con.GENERIC_WRITE, win32con.FILE_SHARE_WRITE,
#             None, win32con.OPEN_EXISTING, 0, None
#         )
#         win32file.SetFilePointer(handle, sector_number * 512, win32file.FILE_BEGIN)
#         win32file.WriteFile(handle, data, None)
#         win32file.CloseHandle(handle)
#         logger.info(f"کلید در سکتور {sector_number} نوشته شد: {device}")
#         return True
#     except Exception as e:
#         logger.error(f"خطا در نوشتن سکتور {sector_number}: {e}")
#         return False
#
# def read_from_sector(device, sector_number, length):
#     """خواندن داده از سکتور خاص"""
#     try:
#         handle = win32file.CreateFile(
#             device, win32con.GENERIC_READ, win32con.FILE_SHARE_READ,
#             None, win32con.OPEN_EXISTING, 0, None
#         )
#         win32file.SetFilePointer(handle, sector_number * 512, win32file.FILE_BEGIN)
#         data, _ = win32file.ReadFile(handle, length, None)
#         win32file.CloseHandle(handle)
#         return data
#     except Exception as e:
#         logger.error(f"خطا در خواندن سکتور {sector_number}: {e}")
#         return None
#
# def find_writable_sector(device, data, start_sector=100, max_attempts=10):
#     """یافتن اولین سکتور قابل نوشتن"""
#     for sector in range(start_sector, start_sector + max_attempts):
#         if write_to_sector(device, sector, data):
#             return sector
#     return None
#
# # --- OS is Linux
# # usb_key_validator/utils.py
#
# import os
# import subprocess
# import logging
#
# logger = logging.getLogger(__name__)
#
# # اندازه یک سکتور
# SECTOR_SIZE = 512
#
#
# def find_usb_drives():
#     """
#     شناسایی درایوهای USB در لینوکس.
#     این تابع یک لیست از دیکشنری‌ها شامل 'device_path' و 'caption' (برای نمایش به کاربر) برمی‌گرداند.
#     'device_path' معمولا چیزی شبیه '/dev/sdb' است.
#     """
#     usb_drives = []
#     try:
#         # استفاده از lsblk برای لیست کردن دستگاه‌های بلوکی
#         # و grep برای فیلتر کردن USB
#         # خروجی مانند: sdb  8:16   0 14.9G  0 disk /media/usb
#         cmd = "lsblk -dpn -o NAME,SIZE,MOUNTPOINT,TYPE,FSTYPE,MODEL,VENDOR | grep -i usb"
#         result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
#
#         for line in result.stdout.strip().split('\n'):
#             if not line:
#                 continue
#             parts = line.split()
#             device_path = parts[0]
#             size = parts[1]
#             model = parts[5] if len(parts) > 5 else "USB Device"
#             vendor = parts[6] if len(parts) > 6 else ""
#
#             # معمولا دیسک‌های USB بدون پارتیشن نیز /dev/sdX هستند
#             # و removable بودنشان را از /sys/block/sdX/removable بررسی می‌کنیم
#             try:
#                 with open(f"/sys/block/{os.path.basename(device_path)}/removable", 'r') as f:
#                     if f.read().strip() == '1':  # removable device
#                         usb_drives.append({
#                             'device_path': device_path,
#                             'caption': f"{device_path} ({size}) - {vendor} {model}"
#                         })
#             except FileNotFoundError:
#                 continue  # not a block device or not removable
#
#     except subprocess.CalledProcessError as e:
#         logger.error(f"خطا در اجرای lsblk برای شناسایی USB: {e.stderr}")
#     except Exception as e:
#         logger.error(f"خطا در شناسایی USB در لینوکس: {e}")
#
#     return usb_drives
#
#
# def write_to_sector(device_path, sector_number, data):
#     """
#     نوشتن داده در سکتور خاص دستگاه بلوکی در لینوکس.
#     نیاز به دسترسی root دارد.
#     """
#     if not data:
#         logger.error("Data to write cannot be empty.")
#         return False
#
#     # داده را به اندازه کامل سکتور padding می‌کنیم (اگر کوچکتر باشد)
#     padded_data = data.ljust(SECTOR_SIZE, b'\0')  # pad with null bytes
#     if len(padded_data) > SECTOR_SIZE:
#         padded_data = padded_data[:SECTOR_SIZE]  # truncate if too long
#
#     try:
#         # از subprocess و dd استفاده می‌کنیم زیرا دسترسی مستقیم به فایل‌ها
#         # با os.open یا open() در پایتون ممکن است مجوزهای کافی نداشته باشد
#         # و dd ابزار استاندارد برای این کار است.
#         command = [
#             'sudo', 'dd',
#             f'of={device_path}',
#             f'bs={SECTOR_SIZE}',
#             f'seek={sector_number}',
#             'count=1',
#             'conv=notrunc'  # مهم: فقط سکتور مورد نظر را overwrite کند، نه کل فایل
#         ]
#
#         # dd ورودی را از stdin می‌گیرد
#         process = subprocess.run(command, input=padded_data, capture_output=True, check=True)
#         logger.info(f"کلید در سکتور {sector_number} نوشته شد: {device_path}")
#         logger.debug(f"dd stdout: {process.stdout.decode()}")
#         logger.debug(f"dd stderr: {process.stderr.decode()}")
#         return True
#     except subprocess.CalledProcessError as e:
#         logger.error(f"خطا در نوشتن سکتور {sector_number} با dd: {e.stderr.decode()}")
#         return False
#     except Exception as e:
#         logger.error(f"خطا در نوشتن سکتور {sector_number}: {e}")
#         return False
#
#
# def read_from_sector(device_path, sector_number, length):
#     """
#     خواندن داده از سکتور خاص دستگاه بلوکی در لینوکس.
#     نیاز به دسترسی root دارد.
#     """
#     if length > SECTOR_SIZE:
#         logger.warning(f"Requested length {length} exceeds SECTOR_SIZE ({SECTOR_SIZE}). Truncating to SECTOR_SIZE.")
#         length = SECTOR_SIZE
#
#     try:
#         command = [
#             'sudo', 'dd',
#             f'if={device_path}',
#             f'bs={SECTOR_SIZE}',
#             f'skip={sector_number}',
#             f'count=1',
#         ]
#
#         process = subprocess.run(command, capture_output=True, check=True)
#         # فقط به اندازه length از داده خوانده شده برمی‌گردانیم
#         return process.stdout[:length]
#     except subprocess.CalledProcessError as e:
#         logger.error(f"خطا در خواندن سکتور {sector_number} با dd: {e.stderr.decode()}")
#         return None
#     except Exception as e:
#         logger.error(f"خطا در خواندن سکتور {sector_number}: {e}")
#         return None
#
#
# def find_writable_sector(device_path, data_to_write, start_sector=100, max_attempts=100):
#     """
#     یافتن اولین سکتور قابل نوشتن در لینوکس و نوشتن داده در آن.
#     توصیه می‌شود قبل از استفاده از این تابع، از دیسک پشتیبان بگیرید.
#     این تابع داده را در سکتور مورد نظر می‌نویسد و شماره سکتور را برمی‌گرداند.
#     """
#     # اطمینان حاصل کنید که داده به اندازه یک سکتور کامل باشد.
#     padded_data = data_to_write.ljust(SECTOR_SIZE, b'\0')[:SECTOR_SIZE]
#
#     for sector in range(start_sector, start_sector + max_attempts):
#         logger.info(f"تلاش برای نوشتن در سکتور: {sector}")
#         if write_to_sector(device_path, sector, padded_data):
#             # اگر با موفقیت نوشته شد، می‌توانیم تأیید کنیم که داده در آنجا قرار گرفته است.
#             # برای اطمینان بیشتر، می‌توانید بلافاصله بعد از نوشتن، آن سکتور را بخوانید و تطبیق دهید.
#             read_data = read_from_sector(device_path, sector, len(data_to_write))
#             if read_data == data_to_write:
#                 logger.info(f"کلید با موفقیت در سکتور {sector} تأیید شد.")
#                 return sector
#             else:
#                 logger.warning(f"کلید در سکتور {sector} نوشته شد اما تطابق ندارد. ادامه تلاش...")
#     return None
