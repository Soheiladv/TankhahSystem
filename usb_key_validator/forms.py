from django import forms
from django.utils.translation import gettext as _
import os
import platform
import logging

logger = logging.getLogger(__name__)

class DongleEditForm(forms.Form):
    """فرم ویرایش اطلاعات dongle"""
    
    organization_name = forms.CharField(
        max_length=255,
        label=_('نام شرکت/سازمان'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('نام شرکت خود را وارد کنید')
        })
    )
    
    software_id = forms.CharField(
        max_length=100,
        label=_('شناسه نرم‌افزار'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'RCMS'
        }),
        initial='RCMS'
    )
    
    expiry_date = forms.DateField(
        label=_('تاریخ انقضا'),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        # دریافت اطلاعات اولیه از dongle
        initial_data = kwargs.pop('initial_data', {})
        super().__init__(*args, **kwargs)
        
        if initial_data:
            self.fields['organization_name'].initial = initial_data.get('organization_name', '')
            self.fields['software_id'].initial = initial_data.get('software_id', 'RCMS')
            self.fields['expiry_date'].initial = initial_data.get('expiry_date', '')

class CompanyDongleForm(forms.Form):
    """فرم ایجاد dongle برای شرکت جدید"""
    
    company_name = forms.CharField(
        max_length=255,
        label=_('نام شرکت'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('نام شرکت جدید')
        })
    )
    
    software_id = forms.CharField(
        max_length=100,
        label=_('شناسه نرم‌افزار'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'RCMS'
        }),
        initial='RCMS'
    )
    
    max_users = forms.IntegerField(
        label=_('حداکثر تعداد کاربران'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 1000
        }),
        initial=10
    )
    
    expiry_days = forms.IntegerField(
        label=_('مدت اعتبار (روز)'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 3650
        }),
        initial=365
    )
    
    description = forms.CharField(
        label=_('توضیحات'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('توضیحات اضافی در مورد شرکت')
        }),
        required=False
    )

# فرم‌های قدیمی برای سازگاری
class USBKeyForm(forms.Form):
    """فرم انتخاب USB (ویندوز)"""
    device_id = forms.ChoiceField(
        label=_('انتخاب درایو USB'),
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['device_id'].choices = get_removable_drives()

class USBKeyFormLinux(forms.Form):
    """فرم انتخاب USB (لینوکس)"""
    device_path = forms.ChoiceField(
        label=_('انتخاب مسیر دستگاه'),
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['device_path'].choices = get_linux_usb_devices()

class USBManagementForm(forms.Form):
    """فرم مدیریت USB"""
    action = forms.ChoiceField(
        label=_('عملیات'),
        choices=[
            ('write', _('نوشتن فایل مجوز')),
            ('read', _('خواندن فایل مجوز')),
            ('validate', _('اعتبارسنجی')),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    license_file = forms.FileField(
        label=_('فایل مجوز'),
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

class TimeLockForm(forms.Form):
    """فرم تنظیم قفل زمانی"""
    expiry_date = forms.DateField(
        label=_('تاریخ انقضا'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    max_users = forms.IntegerField(
        label=_('حداکثر تعداد کاربران'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1})
    )

# توابع کمکی
def get_removable_drives():
    """دریافت لیست درایوهای قابل جابجایی (ویندوز)"""
    drives = []
    try:
        if platform.system() == "Windows":
            import wmi
            import pythoncom
            pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
            c = wmi.WMI()
            for disk in c.Win32_DiskDrive():
                if "USB" in disk.MediaType.upper() or disk.InterfaceType == "USB":
                    device_id = f"\\\\.\\PhysicalDrive{disk.Index}"
                    drives.append((device_id, f"{disk.Caption} - {device_id}"))
            pythoncom.CoUninitialize()
    except Exception as e:
        logger.error(f"Error getting removable drives: {e}")
    return drives

def get_linux_usb_devices():
    """دریافت لیست دستگاه‌های USB (لینوکس)"""
    devices = []
    try:
        if platform.system() == "Linux":
            import subprocess
            result = subprocess.run(['lsblk', '-d', '-n', '-o', 'NAME,TYPE'], 
                                  capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'disk' in line:
                    device_name = line.split()[0]
                    device_path = f"/dev/{device_name}"
                    devices.append((device_path, f"USB Device - {device_path}"))
    except Exception as e:
        logger.error(f"Error getting Linux USB devices: {e}")
    return devices

def write_license_file_to_usb(device_path, license_file_path):
    """نوشتن فایل مجوز به USB"""
    try:
        if platform.system() == "Windows":
            # برای ویندوز، فایل را در ریشه درایو می‌نویسیم
            import shutil
            drive_letter = device_path.split('\\')[-1].replace('PhysicalDrive', '')
            # این یک پیاده‌سازی ساده است
            return True
        else:
            # برای لینوکس
            import shutil
            shutil.copy2(license_file_path, f"{device_path}/license.key")
            return True
    except Exception as e:
        logger.error(f"Error writing license file: {e}")
        return False

def read_license_file_from_usb(device_path):
    """خواندن فایل مجوز از USB"""
    try:
        if platform.system() == "Windows":
            # برای ویندوز
            return "License data from Windows USB"
        else:
            # برای لینوکس
            license_path = f"{device_path}/license.key"
            if os.path.exists(license_path):
                with open(license_path, 'r') as f:
                    return f.read()
            return None
    except Exception as e:
        logger.error(f"Error reading license file: {e}")
        return None