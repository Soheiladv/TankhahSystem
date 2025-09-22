import wmi
import win32file
import win32con
import pythoncom
import os
import io
import logging
import hashlib
import random
import time
from datetime import datetime, timedelta
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)

class USBDongleManager:
    """مدیر پیشرفته USB Dongle با چند سکتور مخفی"""
    
    def __init__(self):
        self.sector_size = 512
        self.hidden_sectors = []  # لیست سکتورهای مخفی
        self.master_sector = 100  # سکتور اصلی
        self.backup_sectors = [101, 102, 103, 104, 105]  # سکتورهای پشتیبان
        self.validation_cache_key = 'usb_dongle_validation'
        self.cache_timeout = 3600  # 1 ساعت
    
    def check_admin_privileges(self):
        """بررسی دسترسی ادمین"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def find_usb_drives(self):
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
                            'index': disk.Index,
                            'size': disk.Size if hasattr(disk, 'Size') else 0
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
    
    def write_to_sector(self, device, sector_number, data):
        """نوشتن داده در سکتور خاص (ویندوز)"""
        if os.name != 'nt':
            logger.error("نوشتن در سکتور فقط در ویندوز پشتیبانی می‌شود.")
            return False
        try:
            # اطمینان از اینکه داده به اندازه سکتور باشد
            if len(data) < self.sector_size:
                data = data.ljust(self.sector_size, b'\0')
            elif len(data) > self.sector_size:
                data = data[:self.sector_size]
            
            # تلاش برای دسترسی با مجوزهای مختلف
            access_flags = [
                win32con.GENERIC_WRITE,
                win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                win32con.GENERIC_ALL
            ]
            
            share_flags = [
                win32con.FILE_SHARE_WRITE,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                0
            ]
            
            for access, share in zip(access_flags, share_flags):
                try:
                    handle = win32file.CreateFile(
                        device, access, share,
                        None, win32con.OPEN_EXISTING, 0, None
                    )
                    win32file.SetFilePointer(handle, sector_number * self.sector_size, win32file.FILE_BEGIN)
                    win32file.WriteFile(handle, data, None)
                    win32file.CloseHandle(handle)
                    logger.info(f"کلید در سکتور {sector_number} نوشته شد: {device}")
                    return True
                except Exception as e:
                    logger.warning(f"تلاش دسترسی با flags {access}/{share} ناموفق: {e}")
                    continue
            
            logger.error(f"همه تلاش‌های دسترسی برای سکتور {sector_number} ناموفق بود")
            return False
            
        except Exception as e:
            logger.error(f"خطا در نوشتن سکتور {sector_number}: {e}")
            return False
    
    def read_from_sector(self, device_path, sector_number, length=None):
        """خواندن داده از سکتور خاص"""
        if length is None:
            length = self.sector_size
            
        try:
            if os.name == 'nt':
                # تلاش برای دسترسی با مجوزهای مختلف
                access_flags = [
                    win32con.GENERIC_READ,
                    win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                    win32con.GENERIC_ALL
                ]
                
                share_flags = [
                    win32con.FILE_SHARE_READ,
                    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                    0
                ]
                
                for access, share in zip(access_flags, share_flags):
                    try:
                        handle = win32file.CreateFile(
                            device_path, access, share,
                            None, win32con.OPEN_EXISTING, 0, None
                        )
                        win32file.SetFilePointer(handle, sector_number * self.sector_size, win32file.FILE_BEGIN)
                        data, _ = win32file.ReadFile(handle, length, None)
                        win32file.CloseHandle(handle)
                        return data
                    except Exception as e:
                        logger.warning(f"تلاش خواندن با flags {access}/{share} ناموفق: {e}")
                        continue
                
                logger.error(f"همه تلاش‌های خواندن برای سکتور {sector_number} ناموفق بود")
                return None
            else:
                with open(device_path, 'rb') as f:
                    f.seek(sector_number * self.sector_size)
                    data = f.read(length)
                return data
        except Exception as e:
            logger.error(f"خطا در خواندن سکتور {sector_number}: {e}")
            return None
    
    def create_dongle_signature(self, key_data, organization_name="", software_id="RCMS", expiry_date=None):
        """ایجاد امضای منحصر به فرد برای dongle با اطلاعات شرکت"""
        timestamp = str(int(time.time()))
        device_id = hashlib.md5(key_data + timestamp.encode()).hexdigest()[:16]
        signature = {
            'device_id': device_id,
            'created_at': timestamp,
            'version': '2.0',
            'sector_count': len(self.backup_sectors) + 1,
            'checksum': hashlib.sha256(key_data).hexdigest()[:32],
            'organization_name': organization_name,
            'software_id': software_id,
            'expiry_date': expiry_date.isoformat() if expiry_date else None,
            'dongle_type': 'multi_company'
        }
        return signature
    
    def write_dongle_to_multiple_sectors(self, device, key_data, organization_name="", software_id="RCMS", expiry_date=None):
        """نوشتن کلید در چند سکتور مخفی با پشتیبانی از چندین شرکت"""
        try:
            # بررسی دسترسی ادمین
            if not self.check_admin_privileges():
                return False, "نیاز به دسترسی ادمین برای نوشتن در سکتورها. لطفاً Django را به عنوان Administrator اجرا کنید."
            
            # دریافت اطلاعات از RCMS_Lock اگر موجود باشد
            from accounts.models import TimeLockModel
            latest_lock = TimeLockModel.objects.filter(is_active=True).order_by('-created_at').first()
            
            if latest_lock:
                lock_expiry, lock_max_users, lock_org_name = latest_lock.get_decrypted_data()
                if not organization_name:
                    organization_name = lock_org_name or "Default Organization"
                if not expiry_date:
                    expiry_date = lock_expiry
                # استفاده از کلید اصلی از دیتابیس
                key_data = latest_lock.lock_key.encode()
                
                # لاگ اطلاعات قفل برای دیباگ
                logger.info(f"اطلاعات قفل از دیتابیس:")
                logger.info(f"  - نام شرکت: {lock_org_name}")
                logger.info(f"  - تاریخ انقضا: {lock_expiry}")
                logger.info(f"  - حداکثر کاربران: {lock_max_users}")
                logger.info(f"  - کلید قفل: {latest_lock.lock_key[:50]}...")
            else:
                if not organization_name:
                    organization_name = "Default Organization"
                if not expiry_date:
                    from datetime import date, timedelta
                    expiry_date = date.today() + timedelta(days=365)
                # ایجاد کلید تست
                key_data = f"test_key_{organization_name}_{int(time.time())}".encode()
            
            # ایجاد امضای dongle با اطلاعات شرکت
            signature = self.create_dongle_signature(key_data, organization_name, software_id, expiry_date)
            signature_data = str(signature).encode()
            
            # نوشتن در سکتور اصلی
            master_data = key_data + b'|MASTER|' + signature_data
            if not self.write_to_sector(device, self.master_sector, master_data):
                return False, "خطا در نوشتن سکتور اصلی - ممکن است دسترسی محدود باشد"
            
            # نوشتن در سکتورهای پشتیبان
            success_count = 1
            for i, sector in enumerate(self.backup_sectors):
                # تغییر جزئی در هر سکتور برای تشخیص
                backup_data = key_data + f'|BACKUP_{i}|'.encode() + signature_data
                if self.write_to_sector(device, sector, backup_data):
                    success_count += 1
                    self.hidden_sectors.append(sector)
            
            logger.info(f"Dongle برای شرکت '{organization_name}' در {success_count} سکتور نوشته شد")
            return True, f"Dongle برای شرکت '{organization_name}' با موفقیت در {success_count} سکتور ایجاد شد"
            
        except Exception as e:
            logger.error(f"خطا در ایجاد dongle: {e}")
            return False, f"خطا در ایجاد dongle: {str(e)}"
    
    def read_dongle_from_sectors(self, device):
        """خواندن کلید از سکتورهای مخفی با اطلاعات شرکت"""
        try:
            # تلاش برای خواندن از سکتور اصلی
            master_data = self.read_from_sector(device, self.master_sector)
            if master_data and b'|MASTER|' in master_data:
                key_data = master_data.split(b'|MASTER|')[0]
                signature_data = master_data.split(b'|MASTER|')[1]
                try:
                    import json
                    signature = json.loads(signature_data.decode())
                    logger.info(f"کلید از سکتور اصلی {self.master_sector} خوانده شد")
                    return key_data, signature, self.master_sector
                except Exception as e:
                    logger.warning(f"خطا در parse کردن signature از سکتور اصلی: {e}")
                    return key_data, signature_data, self.master_sector
            
            # اگر سکتور اصلی خراب بود، از سکتورهای پشتیبان بخوان
            for i, sector in enumerate(self.backup_sectors):
                backup_data = self.read_from_sector(device, sector)
                if backup_data and f'|BACKUP_{i}|'.encode() in backup_data:
                    key_data = backup_data.split(f'|BACKUP_{i}|'.encode())[0]
                    signature_data = backup_data.split(f'|BACKUP_{i}|'.encode())[1]
                    try:
                        import json
                        signature = json.loads(signature_data.decode())
                        logger.info(f"کلید از سکتور پشتیبان {sector} خوانده شد")
                        return key_data, signature, sector
                    except Exception as e:
                        logger.warning(f"خطا در parse کردن signature از سکتور پشتیبان {sector}: {e}")
                        logger.info(f"کلید از سکتور پشتیبان {sector} خوانده شد (فرمت قدیمی)")
                        return key_data, signature_data, sector
            
            logger.warning("هیچ سکتور معتبری یافت نشد")
            return None, None, None
            
        except Exception as e:
            logger.error(f"خطا در خواندن dongle: {e}")
            return None, None, None
    
    def validate_dongle_integrity(self, device):
        """اعتبارسنجی یکپارچگی dongle با اطلاعات شرکت"""
        try:
            key_data, signature_data, source_sector = self.read_dongle_from_sectors(device)
            if not key_data or not signature_data:
                return False, "Dongle یافت نشد"
            
            # بررسی checksum
            expected_checksum = hashlib.sha256(key_data).hexdigest()[:32]
            
            # اگر signature_data یک dictionary است
            if isinstance(signature_data, dict):
                if signature_data.get('checksum') != expected_checksum:
                    return False, "Checksum نامعتبر"
                
                # بررسی تاریخ انقضا
                if signature_data.get('expiry_date'):
                    from datetime import datetime, date
                    try:
                        expiry_date = datetime.fromisoformat(signature_data['expiry_date']).date()
                        if date.today() > expiry_date:
                            return False, f"Dongle منقضی شده (انقضا: {expiry_date})"
                    except:
                        pass
                
                # اطلاعات شرکت
                org_name = signature_data.get('organization_name', 'نامشخص')
                software_id = signature_data.get('software_id', 'نامشخص')
                
                return True, f"Dongle معتبر از سکتور {source_sector} - شرکت: {org_name} - نرم‌افزار: {software_id}"
            else:
                # فرمت قدیمی
                if expected_checksum not in signature_data.decode('utf-8', errors='ignore'):
                    return False, "Checksum نامعتبر"
                return True, f"Dongle معتبر از سکتور {source_sector} (فرمت قدیمی)"
            
        except Exception as e:
            logger.error(f"خطا در اعتبارسنجی dongle: {e}")
            return False, f"خطا در اعتبارسنجی: {str(e)}"
    
    def daily_validation_check(self):
        """بررسی روزانه اعتبار dongle"""
        try:
            # بررسی cache
            cached_result = cache.get(self.validation_cache_key)
            if cached_result:
                return cached_result
            
            usb_drives = self.find_usb_drives()
            if not usb_drives:
                result = {
                    'valid': False,
                    'message': 'هیچ USB متصلی یافت نشد',
                    'timestamp': timezone.now().isoformat()
                }
                cache.set(self.validation_cache_key, result, self.cache_timeout)
                return result
            
            # بررسی اولین USB
            device = usb_drives[0]['device_id']
            is_valid, message = self.validate_dongle_integrity(device)
            
            result = {
                'valid': is_valid,
                'message': message,
                'device': usb_drives[0]['caption'],
                'timestamp': timezone.now().isoformat()
            }
            
            # cache نتیجه
            cache.set(self.validation_cache_key, result, self.cache_timeout)
            
            # لاگ نتیجه
            if is_valid:
                logger.info(f"اعتبارسنجی روزانه موفق: {message}")
            else:
                logger.warning(f"اعتبارسنجی روزانه ناموفق: {message}")
            
            return result
            
        except Exception as e:
            logger.error(f"خطا در اعتبارسنجی روزانه: {e}")
            return {
                'valid': False,
                'message': f'خطا در اعتبارسنجی: {str(e)}',
                'timestamp': timezone.now().isoformat()
            }
    
    def repair_dongle_sectors(self, device):
        """تعمیر سکتورهای خراب dongle"""
        try:
            key_data, signature_data, source_sector = self.read_dongle_from_sectors(device)
            if not key_data:
                return False, "هیچ کلید معتبری برای تعمیر یافت نشد"
            
            # بازنویسی سکتور اصلی
            master_data = key_data + b'|MASTER|' + signature_data
            if not self.write_to_sector(device, self.master_sector, master_data):
                return False, "خطا در تعمیر سکتور اصلی"
            
            # بازنویسی سکتورهای پشتیبان
            repaired_count = 1
            for i, sector in enumerate(self.backup_sectors):
                backup_data = key_data + f'|BACKUP_{i}|'.encode() + signature_data
                if self.write_to_sector(device, sector, backup_data):
                    repaired_count += 1
            
            return True, f"{repaired_count} سکتور تعمیر شد"
            
        except Exception as e:
            logger.error(f"خطا در تعمیر dongle: {e}")
            return False, f"خطا در تعمیر: {str(e)}"
    
    def get_dongle_statistics(self, device):
        """دریافت آمار dongle با اطلاعات شرکت"""
        try:
            stats = {
                'total_sectors': len(self.backup_sectors) + 1,
                'master_sector': self.master_sector,
                'backup_sectors': self.backup_sectors,
                'sector_size': self.sector_size
            }
            
            # بررسی وضعیت هر سکتور
            sector_status = {}
            
            # سکتور اصلی
            master_data = self.read_from_sector(device, self.master_sector)
            sector_status[self.master_sector] = {
                'status': 'valid' if master_data and b'|MASTER|' in master_data else 'invalid',
                'size': len(master_data) if master_data else 0
            }
            
            # سکتورهای پشتیبان
            for i, sector in enumerate(self.backup_sectors):
                backup_data = self.read_from_sector(device, sector)
                sector_status[sector] = {
                    'status': 'valid' if backup_data and f'|BACKUP_{i}|'.encode() in backup_data else 'invalid',
                    'size': len(backup_data) if backup_data else 0
                }
            
            stats['sector_status'] = sector_status
            stats['valid_sectors'] = sum(1 for s in sector_status.values() if s['status'] == 'valid')
            
            # دریافت اطلاعات شرکت از dongle
            key_data, signature_data, source_sector = self.read_dongle_from_sectors(device)
            if signature_data and isinstance(signature_data, dict):
                stats['organization_name'] = signature_data.get('organization_name', 'نامشخص')
                stats['software_id'] = signature_data.get('software_id', 'نامشخص')
                stats['expiry_date'] = signature_data.get('expiry_date', 'نامشخص')
                stats['dongle_type'] = signature_data.get('dongle_type', 'قدیمی')
                stats['created_at'] = signature_data.get('created_at', 'نامشخص')
                stats['device_id'] = signature_data.get('device_id', 'نامشخص')
            else:
                stats['organization_name'] = 'نامشخص (فرمت قدیمی)'
                stats['software_id'] = 'نامشخص'
                stats['expiry_date'] = 'نامشخص'
                stats['dongle_type'] = 'قدیمی'
                stats['created_at'] = 'نامشخص'
                stats['device_id'] = 'نامشخص'
            
            return stats
            
        except Exception as e:
            logger.error(f"خطا در دریافت آمار dongle: {e}")
            return None

# نمونه سراسری
dongle_manager = USBDongleManager()
