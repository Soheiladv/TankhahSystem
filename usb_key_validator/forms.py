from django import forms
import os
from django.utils.translation import gettext_lazy as _
from .utils import find_usb_drives
#$$$$$$$$$$$$$$$$$$$$$$$$
from django import forms
from .utils import find_usb_drives
from django.utils.translation import gettext_lazy as _

class USBKeyForm(forms.Form):
    usb_device = forms.ChoiceField(
        label=_("انتخاب USB"),
        help_text=_("یک درایو USB را از جدول انتخاب کنید."),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usb_drives = find_usb_drives()
        choices = [(drive['device_id'], f"{drive['drive_letter']} - {drive['caption']}") for drive in usb_drives]
        if not choices:
            choices = [('', _('هیچ USB متصلی یافت نشد'))]
        self.fields['usb_device'].choices = choices

    def clean_usb_device(self):
        device = self.cleaned_data['usb_device']
        usb_drives = find_usb_drives()
        valid_devices = [drive['device_id'] for drive in usb_drives]
        if device and device not in valid_devices and device != '':
            raise forms.ValidationError(_("گزینه انتخاب‌شده معتبر نیست."))
        return device


#$$$$$$$$$$$$$$$$$$$$$$$$

class USBKeyFormLinux(forms.Form):
    usb_device = forms.ChoiceField(
        label=_("انتخاب USB"),
        help_text=_("یک درایو USB را از لیست انتخاب کنید."),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usb_drives = find_usb_drives()
        choices = [(drive['device_path'], drive['caption']) for drive in usb_drives]
        if not choices:
            choices = [('', _('هیچ USB متصلی یافت نشد'))]
        self.fields['usb_device'].choices = choices

#################################################################################################
# licensing/forms.py

from django import forms
from accounts.models import TimeLockModel
from datetime import date
from django.utils.translation import gettext_lazy as _
import platform
import  json
# توابع شناسایی درایو (از فایل utils.py قبلی)
if platform.system() == "Windows":
    import wmi, win32file, win32con, pythoncom


    def get_removable_drives():
        drives = []
        try:
            pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
            c = wmi.WMI()
            for drive in c.Win32_LogicalDisk():
                if drive.DriveType == 2:  # 2 = Removable Disk
                    drives.append({
                        'path': drive.Name + "\\",  # E.g., 'D:\\'
                        'caption': f"{drive.Name} - {drive.VolumeName or 'No Label'} ({round(drive.Size / (1024 ** 3), 2) if drive.Size else 'N/A'} GB)"
                    })
        except Exception as e:
            # logger.error(f"خطا در شناسایی درایوهای ویندوز: {e}")
            pass
        finally:
            pythoncom.CoUninitialize()
        return drives
else:  # Linux
    import subprocess


    def get_removable_drives():
        drives = []
        try:
            cmd = "lsblk -dpn -o NAME,SIZE,MOUNTPOINT,TYPE,FSTYPE,MODEL,VENDOR | grep -i removable=1"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                    check=False)  # check=False if grep returns nothing

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split()
                # Assuming parts: [NAME, SIZE, MOUNTPOINT, TYPE, FSTYPE, MODEL, VENDOR]
                device_path = parts[0]  # /dev/sdX
                mount_point = parts[2] if len(parts) > 2 else ""  # /mnt/usb
                size = parts[1]  # e.g., 14.9G
                model = parts[5] if len(parts) > 5 else "USB Device"
                vendor = parts[6] if len(parts) > 6 else ""

                if mount_point:  # فقط درایوهای mount شده را نمایش می‌دهیم
                    drives.append({
                        'path': mount_point,
                        'caption': f"{mount_point} ({size}) - {vendor} {model}"
                    })
                else:  # اگر mount نشده ولی removable است، نمایش دهیم که کاربر خودش mount کند
                    drives.append({
                        'path': device_path,
                        'caption': f"{device_path} (Unmounted, {size}) - {vendor} {model}"
                    })

        except Exception as e:
            # logger.error(f"خطا در شناسایی درایوهای لینوکس: {e}")
            pass
        return drives


class USBManagementForm(forms.Form):
    # این فرم در ویو نمایش داده می‌شود
    # لیست درایوها در زمان __init__ پر می‌شود
    usb_device = forms.ChoiceField(
        label=_("انتخاب درایو USB"),
        help_text=_("درایو USB که می‌خواهید لایسنس را روی آن ذخیره/بخوانید را انتخاب کنید."),
        widget=forms.RadioSelect
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        removable_drives = get_removable_drives()
        choices = []
        if removable_drives:
            choices = [(drive['path'], drive['caption']) for drive in removable_drives]
        else:
            choices = [('', _('هیچ درایو Removable (USB) یافت نشد.').format(platform.system()))]
            # اگر درایو USB یافت نشد، فیلد را غیرفعال می‌کنیم
            self.fields['usb_device'].disabled = True

        self.fields['usb_device'].choices = choices

# ----------------------------------------------------------------------
# توابع مربوط به سیستم عامل (برای شناسایی درایوهای USB)
# اینها در خود فرم و ویو استفاده می‌شوند.
# ----------------------------------------------------------------------

# توابع برای ویندوز
if platform.system() == "Windows":
    import wmi
    import win32file
    import win32con
    import pythoncom


    def get_removable_drives():
        """شناسایی درایوهای Removable در ویندوز"""
        drives = []
        try:
            pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
            c = wmi.WMI()
            for drive in c.Win32_LogicalDisk():
                if drive.DriveType == 2:  # 2 = Removable Disk
                    drives.append({
                        'path': drive.Name + "\\",  # E.g., 'D:\\'
                        'caption': f"{drive.Name} - {drive.VolumeName or _('بدون برچسب')} ({round(drive.Size / (1024 ** 3), 2) if drive.Size else 'N/A'} GB)"
                    })
        except Exception as e:
            # logger.error(f"خطا در شناسایی درایوهای ویندوز: {e}") # لاگینگ را در ویو انجام می‌دهیم
            pass
        finally:
            pythoncom.CoUninitialize()
        return drives


    def write_license_file_to_usb(drive_path, license_data):
        """ذخیره داده‌های لایسنس در فایل روی USB در ویندوز."""
        try:
            license_dir = os.path.join(drive_path, ".rcms_license")
            os.makedirs(license_dir, exist_ok=True)
            license_file_path = os.path.join(license_dir, "rcms_license.dat")
            with open(license_file_path, 'w', encoding='utf-8') as f:
                json.dump(license_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            # logger.error(f"خطا در نوشتن فایل لایسنس در ویندوز: {e}")
            return False


    def read_license_file_from_usb(drive_path):
        """خواندن داده‌های لایسنس از فایل روی USB در ویندوز."""
        license_file_path = os.path.join(drive_path, ".rcms_license", "rcms_license.dat")
        if not os.path.exists(license_file_path):
            return None
        try:
            with open(license_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            # logger.error(f"خطا در خواندن فایل لایسنس از USB در ویندوز: {e}")
            return None
        except Exception as e:
            # logger.error(f"خطا نامشخص در خواندن فایل لایسنس از USB در ویندوز: {e}")
            return None

# توابع برای لینوکس
elif platform.system() == "Linux":
    import subprocess

    # برای جلوگیری از تداخل با ماژول os
    _os_path_join = os.path.join
    _os_makedirs = os.makedirs
    _os_exists = os.path.exists
    _os_chmod = os.chmod


    def get_removable_drives():
        """شناسایی درایوهای Removable در لینوکس."""
        drives = []
        try:
            cmd = "lsblk -dpn -o NAME,SIZE,MOUNTPOINT,TYPE,FSTYPE,MODEL,VENDOR,REMOVABLE | grep -i removable=1"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split()
                device_path = parts[0]  # /dev/sdX
                mount_point = parts[2] if len(parts) > 2 else ""  # /mnt/usb or empty
                size = parts[1]  # e.g., 14.9G
                model = parts[5] if len(parts) > 5 else "USB Device"
                vendor = parts[6] if len(parts) > 6 else ""

                if mount_point:
                    drives.append({
                        'path': mount_point,
                        'caption': f"{mount_point} ({size}) - {vendor} {model}"
                    })
                else:
                    drives.append({
                        'path': device_path,  # نام دستگاه را می‌دهیم تا کاربر بتواند دستی mount کند
                        'caption': f"{device_path} ({size}) - {vendor} {model} ({_('بدون Mount')})"
                    })

        except Exception as e:
            # logger.error(f"خطا در شناسایی درایوهای لینوکس: {e}")
            pass
        return drives


    def write_license_file_to_usb(drive_path, license_data):
        """ذخیره داده‌های لایسنس در فایل روی USB در لینوکس."""
        try:
            license_dir = _os_path_join(drive_path, ".rcms_license")
            _os_makedirs(license_dir, exist_ok=True)
            license_file_path = _os_path_join(license_dir, "rcms_license.dat")
            with open(license_file_path, 'w', encoding='utf-8') as f:
                json.dump(license_data, f, indent=4, ensure_ascii=False)

            _os_chmod(license_file_path, 0o600)  # فقط مالک بخواند و بنویسد
            _os_chmod(license_dir, 0o700)  # فقط مالک دسترسی کامل
            return True
        except Exception as e:
            # logger.error(f"خطا در نوشتن فایل لایسنس در لینوکس: {e}")
            return False


    def read_license_file_from_usb(drive_path):
        """خواندن داده‌های لایسنس از فایل روی USB در لینوکس."""
        license_file_path = _os_path_join(drive_path, ".rcms_license", "rcms_license.dat")
        if not _os_exists(license_file_path):
            return None
        try:
            with open(license_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            # logger.error(f"خطا در خواندن فایل لایسنس از USB در لینوکس: {e}")
            return None
        except Exception as e:
            # logger.error(f"خطا نامشخص در خواندن فایل لایسنس از USB در لینوکس: {e}")
            return None

else:  # Fallback for unsupported OS (no USB functionality)
    def get_removable_drives():
        return []


    def write_license_file_to_usb(drive_path, license_data):
        return False


    def read_license_file_from_usb(drive_path):
        return None


# ----------------------------------------------------------------------
# فرم‌ها
# ----------------------------------------------------------------------

class TimeLockForm(forms.ModelForm):
    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label=_("تاریخ انقضا")
    )
    max_users = forms.IntegerField(
        min_value=1,
        label=_("حداکثر کاربران فعال")
    )
    organization_name = forms.CharField(
        max_length=255,
        required=False,
        label=_("نام مجموعه")
    )

    class Meta:
        model = TimeLockModel
        fields = ['expiry_date', 'max_users', 'organization_name']

    def save(self, commit=True):
        from core.RCMS_Lock.security import TimeLock
        expiry_date = self.cleaned_data['expiry_date']
        max_users = self.cleaned_data['max_users']
        organization_name = self.cleaned_data.get('organization_name', "")

        success = TimeLock.set_expiry_date(expiry_date, max_users, organization_name)
        if success:
            return TimeLockModel.objects.filter(is_active=True).order_by('-created_at').first()
        else:
            raise forms.ValidationError(_("خطا در ذخیره قفل سیستم."))


class USBManagementForm(forms.Form):
    usb_device = forms.ChoiceField(
        label=_("انتخاب درایو USB"),
        help_text=_("درایو USB که می‌خواهید لایسنس را روی آن ذخیره/بخوانید را انتخاب کنید."),
        widget=forms.RadioSelect
    )

    # فیلدهای اضافی برای ورودی در زمان تولید لایسنس جدید
    new_max_users = forms.IntegerField(
        label=_("حداکثر کاربران برای لایسنس جدید"),
        min_value=1,
        required=False,  # فقط زمانی که اکشن generate_and_save باشد لازم است
        initial=5,  # مقدار پیش‌فرض
        help_text=_("این مقدار در لایسنس جدید روی USB ذخیره می‌شود.")
    )
    new_organization_name = forms.CharField(
        max_length=255,
        label=_("نام مجموعه برای لایسنس جدید"),
        required=False,
        initial=_("پیش‌فرض"),
        help_text=_("این نام در لایسنس جدید روی USB ذخیره می‌شود.")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        removable_drives = get_removable_drives()
        choices = []
        if removable_drives:
            choices = [(drive['path'], drive['caption']) for drive in removable_drives]
        else:
            choices = [('', _('هیچ درایو Removable (USB) یافت نشد.'))]
            self.fields['usb_device'].disabled = True  # غیرفعال کردن فیلد انتخاب درایو

    def clean(self):
        cleaned_data = super().clean()
        action = self.data.get('action')  # دسترسی به اکشن ارسال شده

        if action == 'generate_and_save':
            # بررسی اینکه فیلدهای new_max_users و new_organization_name خالی نباشند
            if cleaned_data.get('new_max_users') is None:
                self.add_error('new_max_users', _("حداکثر کاربران برای لایسنس جدید نمی‌تواند خالی باشد."))
            if not cleaned_data.get('new_organization_name'):
                self.add_error('new_organization_name', _("نام مجموعه برای لایسنس جدید نمی‌تواند خالی باشد."))

        return cleaned_data
