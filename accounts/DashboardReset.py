import datetime
import logging
import zipfile

from dbbackup.utils import encrypt_file

from accounts.forms import DatabaseBackupForm

# یک لاگر (مقطع) برای این ماژول ایجاد می‌کنیم تا بتوانیم رویدادها را ثبت کنیم.
logger = logging.getLogger(__name__)
import json
import base64
from hashlib import sha256
from io import StringIO
from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.serializers import serialize
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, models as django_models, connection
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from cryptography.fernet import Fernet
from django.utils.translation import gettext_lazy as _

import json # برای کار با داده‌های JSON (سریالایز و دی‌سریالایز کردن)
import base64 # برای تبدیل داده‌های باینری به فرمت قابل استفاده در URL (مورد نیاز Fernet)
from cryptography.fernet import Fernet # برای رمزگذاری و رمزگشایی داده‌ها با کلید متقارن
from hashlib import sha256 # برای هش کردن رمز عبور به منظور تولید کلید رمزگذاری
from io import StringIO # برای ایجاد یک بافر متنی در حافظه، شبیه به فایل
import logging # برای ثبت رویدادها و خطاهای برنامه

from django.shortcuts import render # برای رندر کردن تمپلیت‌های HTML
from django.views import View # کلاس پایه برای ویوهای کلاس‌محور
from django.contrib.auth.mixins import LoginRequiredMixin # برای اطمینان از لاگین بودن کاربر
from django.http import HttpResponse, HttpResponseRedirect # برای برگرداندن پاسخ‌های HTTP و ریدایرکت
from django.urls import reverse_lazy # برای ایجاد URL بر اساس نام ویو به صورت تنبل (lazy)
from django.contrib import messages # برای نمایش پیام‌ها به کاربر (مانند خطا یا موفقیت)
from django.utils.translation import gettext_lazy as _ # برای بین‌المللی‌سازی (ترجمه متون)
from django.apps import apps # برای دسترسی به تنظیمات و مدل‌های برنامه‌های Django
from django.db.models import ForeignKey, ManyToManyField, OneToOneField # برای تشخیص انواع روابط در مدل‌ها
from django.conf import settings # برای دسترسی به تنظیمات پروژه Django
from django.core import management # برای اجرای دستورات منیجمنت Django (مانند dumpdata)
from django.core import serializers # برای سریالایز کردن آبجکت‌های Django به فرمت‌های مختلف (مثل JSON)
from django.db import transaction # برای انجام عملیات دیتابیس به صورت اتمیک (یا همه موفق یا هیچکدام)
from django.utils import timezone # برای کار با زمان و تاریخ (مورد نیاز برای نام‌گذاری فایل بک‌آپ)


from dbbackup.utils import encrypt_file

logger = logging.getLogger(__name__)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.serializers import serialize
from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.urls import reverse_lazy
from django.views import View
from django.db import transaction
from django.apps import apps
from django.core.management import call_command
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import tempfile
import json
import glob
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


import subprocess
import tempfile
import os
import shutil
from django.http import FileResponse
from django.views.generic.edit import FormView
from django.contrib import messages
from django.conf import settings
#--------------------
import json
import logging
from django.conf import settings
from django.apps import apps
from django.db.models import ForeignKey, ManyToManyField, OneToOneField, AutoField
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse  # برای ایجاد لینک ادمین

class DatabaseResetView(LoginRequiredMixin, View):
    template_name = 'core/DashboardDatabase/dashboardReset.html'

    login_url = reverse_lazy('accounts:login')

    def get_model_relations(self, model):
        """استخراج روابط ForeignKey, ManyToMany, OneToOne برای مدل"""
        relations = []
        for field in model._meta.get_fields():
            if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
                relations.append({
                    'field_name': field.name,
                    'related_model': f"{field.related_model._meta.app_label}.{field.related_model._meta.model_name}",
                    'type': field.__class__.__name__
                })
        return relations

    def get(self, request):
        if not request.user.is_superuser:
            messages.error(request, "فقط مدیران سیستم می‌توانند دیتابیس را ریست کنند.")
            return HttpResponseRedirect(reverse_lazy('index'))

        # جمع‌آوری همه مدل‌ها از اپ‌های پروژه
        app_labels = ['core', 'budgets', 'tankhah']  # اپ‌های پروژه
        models = []
        for app_label in app_labels:
            app_config = apps.get_app_config(app_label)
            for model in app_config.get_models():
                models.append({
                    'app_label': app_label,
                    'model_name': model._meta.model_name,
                    'verbose_name': model._meta.verbose_name,
                    'key': f"{app_label}.{model._meta.model_name}",
                    'relations': self.get_model_relations(model)
                })

        context = {
            'title': 'ریست انتخابی دیتابیس',
            'models': sorted(models, key=lambda x: x['key']),
        }
        logger.debug(f"Rendering reset database form: models={[m['key'] for m in models]}")
        return render(request, self.template_name, context)

    def post(self, request):
        if not request.user.is_superuser:
            messages.error(request, "فقط مدیران سیستم می‌توانند دیتابیس را ریست کنند.")
            return HttpResponseRedirect(reverse_lazy('index'))

        selected_models = request.POST.getlist('models')
        if not selected_models:
            messages.error(request, "هیچ مدلی برای ریست انتخاب نشده است.")
            return HttpResponseRedirect(reverse_lazy('reset_database'))

        try:
            with transaction.atomic():
                for model_key in selected_models:
                    try:
                        app_label, model_name = model_key.split('.')
                        model_class = apps.get_model(app_label, model_name)
                        # حذف تمام داده‌های جدول
                        model_class.objects.all().delete()
                        logger.info(f"Deleted all data from {model_key} by user {request.user.username}")
                    except Exception as e:
                        logger.error(f"Error deleting data from {model_key}: {e}", exc_info=True)
                        messages.error(request, f"خطا در ریست مدل {model_key}: {str(e)}")
                        continue

                messages.success(request, f"داده‌های مدل‌های انتخاب‌شده ({', '.join(selected_models)}) با موفقیت ریست شدند.")

        except Exception as e:
            logger.error(f"Error resetting database for models {selected_models}: {e}", exc_info=True)
            messages.error(request, f"خطا در ریست دیتابیس: {str(e)}")

        return HttpResponseRedirect(reverse_lazy('reset_database'))

class DatabaseBackupView(FormView):
    template_name = 'accounts/DashboardDatabase/backup.html'
    form_class = DatabaseBackupForm

    def form_valid(self, form):
        db_type = form.cleaned_data['database_type']
        output_format = form.cleaned_data['format']
        password = form.cleaned_data['password']
        reset_models = form.cleaned_data['reset_models']
        models_to_reset = form.cleaned_data['models_to_reset']

        db_settings = settings.DATABASES['default']
        user = db_settings['USER']
        password_db = db_settings['PASSWORD']
        name = db_settings['NAME']
        host = db_settings['HOST'] or 'localhost'
        port = db_settings['PORT']

        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".sql")
        command = []

        if db_type == 'mysql':
            command = [
                'mysqldump',
                f'--user={user}',
                f'--password={password_db}',
                f'--host={host}',
                f'--port={port}',
                name
            ]
        elif db_type == 'postgresql':
            os.environ['PGPASSWORD'] = password_db
            command = [
                'pg_dump',
                f'--username={user}',
                f'--host={host}',
                f'--port={port}',
                name
            ]
        else:
            messages.error(self.request, "نوع دیتابیس نامعتبر است.")
            return self.form_invalid(form)

        try:
            with open(output_file.name, 'wb') as f:
                subprocess.check_call(command, stdout=f)

            final_path = output_file.name

            if output_format == 'zip':
                import zipfile
                zip_path = f"{output_file.name}.zip"
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(output_file.name, arcname=os.path.basename(output_file.name))
                    if password:
                        zipf.setpassword(password.encode('utf-8'))
                final_path = zip_path

            # Reset tables if requested
            if reset_models and models_to_reset:
                from django.db import connection
                cursor = connection.cursor()
                for model_name in models_to_reset.split(','):
                    model_name = model_name.strip()
                    cursor.execute(f"DROP TABLE IF EXISTS {model_name} CASCADE;")
                messages.success(self.request, "جدول‌های انتخاب‌شده ریست شدند.")

            messages.success(self.request, "بکاپ با موفقیت ایجاد شد.")
            return FileResponse(open(final_path, 'rb'), as_attachment=True, filename=os.path.basename(final_path))

        except subprocess.CalledProcessError as e:
            messages.error(self.request, f"خطا در ایجاد بکاپ: {str(e)}")
            return self.form_invalid(form)

        finally:
            if os.path.exists(output_file.name):
                os.unlink(output_file.name)

class Dld__atabaseManageView(LoginRequiredMixin, View):
    """
    این ویو مسئول مدیریت دیتابیس است که شامل قابلیت‌های بک‌آپ‌گیری (پشتیبان‌گیری)
    و ریست (حذف تمامی داده‌ها) برای مدل‌های انتخاب شده یا کل دیتابیس می‌شود.
    این ویو فقط برای کاربران با دسترسی 'superuser' قابل دسترس است.
    """
    # مسیر تمپلیت HTML که قرار است برای این ویو رندر شود.
    template_name = 'accounts/DashboardDatabase/Dashboard_admin.html'
    # URLی که کاربر در صورت لاگین نبودن به آن هدایت می‌شود.
    login_url = reverse_lazy('accounts:login')

    def get_model_relations(self, model_class):
        """
        این متد روابط یک مدل خاص را (ForeignKey, ManyToManyField, OneToOneField) پیدا کرده
        و اطلاعات مربوط به مدل‌های مرتبط را برمی‌گرداند.
        """
        relations = [] # لیستی برای ذخیره اطلاعات روابط
        # تمامی فیلدهای مدل را پیمایش می‌کنیم.
        for field in model_class._meta.get_fields():
            # بررسی می‌کنیم که آیا فیلد یک نوع رابطه (ForeignKey, ManyToManyField, OneToOneField) است.
            if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
                # متادیتای مدل مرتبط را دریافت می‌کنیم.
                related_model_meta = field.related_model._meta
                # اطلاعات رابطه را به لیست اضافه می‌کنیم.
                relations.append({
                    'field_name': field.name, # نام فیلد در مدل فعلی
                    'related_model_key': f"{related_model_meta.app_label}.{related_model_meta.model_name}", # کلید مدل مرتبط (مثال: 'app_name.model_name')
                    'related_model_verbose_name': str(related_model_meta.verbose_name), # نام نمایشی مدل مرتبط (برای نمایش در UI)
                    'type': field.__class__.__name__ # نوع رابطه (مثال: 'ForeignKey')
                })
        return relations # لیست روابط را برمی‌گردانیم.

    def get(self, request):
        """
        این متد درخواست‌های GET را مدیریت می‌کند.
        مسئول نمایش صفحه مدیریت دیتابیس و لیست کردن مدل‌های قابل مدیریت است.
        """
        # بررسی می‌کنیم که آیا کاربر فعلی 'superuser' است یا خیر.
        if not request.user.is_superuser:
            # اگر کاربر سوپریوزر نیست، پیام خطا نمایش داده و به صفحه اصلی هدایت می‌شود.
            messages.error(request, _("فقط مدیران سیستم می‌توانند دیتابیس را مدیریت کنند."))
            return HttpResponseRedirect(reverse_lazy('index'))

        # سعی می‌کنیم app_labels مورد نظر برای مدیریت را از تنظیمات Django بخوانیم.
        # اگر تنظیم نشده باشد، از لیست پیش‌فرض ['core', 'budgets', 'tankhah'] استفاده می‌کنیم.
        app_labels_to_manage = getattr(settings, 'DATABASE_MANAGE_APP_LABELS', ['core', 'budgets', 'tankhah'])

        all_models_info = [] # لیستی برای ذخیره اطلاعات تمامی مدل‌ها
        vis_groups = {} # دیکشنری برای گروه‌بندی مدل‌ها بر اساس اپ‌ها برای نمایش در vis.js (یک کتابخانه گرافیکی)
        # یک پالت رنگی برای گروه‌های vis.js تعریف می‌کنیم.
        app_colors = ['#e3f2fd', '#e8f5e9', '#fff3e0', '#ffebee', '#f3e5f5', '#e0f7fa', '#fce4ec', '#f1f8e9']

        # هر app_label را که قرار است مدیریت شود، پیمایش می‌کنیم.
        for i, app_label in enumerate(app_labels_to_manage):
            try:
                # پیکربندی (config) برنامه Django را بر اساس app_label دریافت می‌کنیم.
                app_config = apps.get_app_config(app_label)
                # اطلاعات گروه (رنگ و فونت) برای هر اپ را برای استفاده در vis.js ذخیره می‌کنیم.
                vis_groups[app_label] = {
                    'color': {
                        'background': app_colors[i % len(app_colors)], # رنگ پس‌زمینه از پالت رنگ
                        'border': '#aeaeae', # رنگ حاشیه
                        'highlight': { # رنگ هنگام هاور یا انتخاب
                            'background': app_colors[i % len(app_colors)],
                            'border': '#2B7CE9'
                        }
                    },
                    'font': {'color': '#343434'}
                }
                # تمامی مدل‌های موجود در این اپ را پیمایش می‌کنیم.
                for model_class in app_config.get_models():
                    model_meta = model_class._meta # متادیتای مدل را دریافت می‌کنیم.
                    # اطلاعات مدل را به لیست all_models_info اضافه می‌کنیم.
                    all_models_info.append({
                        'app_label': app_label, # نام اپلیکیشن
                        'model_name': model_meta.model_name, # نام مدل (مثال: 'user')
                        'verbose_name': str(model_meta.verbose_name), # نام نمایشی مدل (برای نمایش در UI)
                        'key': f"{app_label}.{model_meta.model_name}", # کلید منحصر به فرد مدل (مثال: 'accounts.user')
                        'relations': self.get_model_relations(model_class) # روابط این مدل
                    })
            except LookupError:
                # اگر اپلیکیشن مورد نظر پیدا نشد یا مدلی نداشت، یک هشدار ثبت می‌کنیم.
                logger.warning(f"App with label '{app_label}' not found or contains no models.")

        # کانتکست (داده‌هایی که به تمپلیت فرستاده می‌شوند) را آماده می‌کنیم.
        context = {
            'title': _('مدیریت دیتابیس (ریست و بک‌آپ)'), # عنوان صفحه
            # مدل‌ها را بر اساس app_label و سپس verbose_name مرتب می‌کنیم.
            'models': sorted(all_models_info, key=lambda x: (x['app_label'], x['verbose_name'])),
            # گروه‌های vis.js را به فرمت JSON تبدیل می‌کنیم تا در جاوااسکریپت قابل استفاده باشند.
            'vis_groups_json': json.dumps(vis_groups),
        }
        # پیامی را برای دیباگ کردن ثبت می‌کنیم.
        logger.debug(f"Rendering database manage form: models_count={len(all_models_info)}")
        # تمپلیت را با کانتکست رندر کرده و برمی‌گردانیم.
        return render(request, self.template_name, context)

    # ---
    def post(self, request):
        """
        این متد درخواست‌های POST را مدیریت می‌کند.
        مسئول اجرای عملیات بک‌آپ‌گیری و ریست دیتابیس است.
        """
        # مجدداً بررسی می‌کنیم که آیا کاربر سوپریوزر است.
        if not request.user.is_superuser:
            messages.error(request, ("فقط مدیران سیستم می‌توانند دیتابیس را مدیریت کنند."))
            return HttpResponseRedirect(reverse_lazy('index')) # یا هر صفحه مناسب دیگر

        # نوع عملیات (backup یا reset) را از داده‌های POST دریافت می‌کنیم.
        action = request.POST.get('action')
        # لیست کلیدهای مدل‌های انتخاب شده را دریافت می‌کنیم (مثال: ['app1.model1', 'app2.model2']).
        selected_model_keys = request.POST.getlist('models')
        # رمز عبور وارد شده توسط کاربر را دریافت می‌کنیم.
        password = request.POST.get('password', '')
        # URL برای ریدایرکت پس از انجام عملیات.
        redirect_url = reverse_lazy('database_manage')
        logger.info(f'Redirect url: {redirect_url}')

        # اگر عملیات 'backup' باشد:
        if action == 'backup':
            # بررسی می‌کنیم که رمز عبور وارد شده باشد و حداقل 8 کاراکتر طول داشته باشد.
            if not password or len(password) < 8:
                messages.error(request,("رمز عبور برای بک‌آپ باید حداقل 8 کاراکتر باشد."))
                return HttpResponseRedirect(redirect_url)

            try:
                # رمز عبور را با SHA256 هش می‌کنیم تا یک هش 32 بایتی داشته باشیم.
                hashed_password = sha256(password.encode('utf-8')).digest()
                # هش 32 بایتی را به فرمت Base64 URL-safe تبدیل می‌کنیم تا کلید Fernet ساخته شود.
                fernet_key = base64.urlsafe_b64encode(hashed_password)
                # یک آبجکت Fernet برای رمزگذاری و رمزگشایی ایجاد می‌کنیم.
                fernet = Fernet(fernet_key)
                logger.info(f'Fernet key generated.')

                # لیستی برای نگهداری آبجکت‌های پایتون که از سریالایز کردن مدل‌ها به دست می‌آیند.
                data_to_backup_objects = []

                # اگر مدل‌های خاصی برای بک‌آپ انتخاب شده باشند:
                if selected_model_keys:
                    for model_key in selected_model_keys:
                        # app_label و model_name را از کلید مدل جدا می‌کنیم.
                        app_label, model_name = model_key.split('.')
                        # کلاس مدل را از Django دریافت می‌کنیم.
                        model_class = apps.get_model(app_label, model_name)
                        # یک بافر متنی در حافظه ایجاد می‌کنیم.
                        output_buffer = StringIO()
                        # تمامی آبجکت‌های مدل را به فرمت JSON سریالایز کرده و به بافر می‌نویسیم.
                        serializers.serialize('json', model_class.objects.all(), stream=output_buffer, ensure_ascii=False)
                        # محتوای بافر را به صورت JSON بارگذاری کرده و به لیست data_to_backup_objects اضافه می‌کنیم.
                        data_to_backup_objects.extend(json.loads(output_buffer.getvalue()))
                        output_buffer.close() # بافر را می‌بندیم.
                    # یک پیشوند نام فایل بر اساس مدل‌های انتخاب شده ایجاد می‌کنیم.
                    filename_prefix = "_".join(model_key.replace('.', '_') for model_key in selected_model_keys)
                    logger.info(f'Filename prefix for selected models: {filename_prefix}')
                else:  # اگر هیچ مدلی انتخاب نشده باشد، بک‌آپ کامل دیتابیس را می‌گیریم.
                    output_buffer = StringIO() # یک بافر متنی در حافظه ایجاد می‌کنیم.
                    # لیست اپلیکیشن‌ها/مدل‌هایی که باید از بک‌آپ کامل حذف شوند.
                    excluded_apps = ['admin.logentry', 'contenttypes', 'auth.permission', 'sessions.session']
                    # دستور `dumpdata` جنگو را برای گرفتن بک‌آپ کامل اجرا می‌کنیم.
                    # `*` برای باز کردن لیست `excluded_apps` به عنوان آرگومان‌های جداگانه است.
                    # `f'--exclude={app}' for app in excluded_apps` هر اپ را به فرمت '--exclude=app_name.model_name' تبدیل می‌کند.
                    management.call_command('dumpdata', *[f'--exclude={app}' for app in excluded_apps], stdout=output_buffer, format='json')
                    # محتوای بافر را به صورت JSON بارگذاری می‌کنیم.
                    data_to_backup_objects = json.loads(output_buffer.getvalue())
                    output_buffer.close() # بافر را می‌بندیم.
                    filename_prefix = "full_database" # پیشوند نام فایل برای بک‌آپ کامل.
                    logger.info(f'Filename prefix for full database: {filename_prefix}')

                # اگر هیچ داده‌ای برای بک‌آپ یافت نشد:
                if not data_to_backup_objects:
                    messages.warning(request,
                                     ("داده‌ای برای بک‌آپ یافت نشد (مدل‌های انتخاب شده ممکن است خالی باشند)."))
                    return HttpResponseRedirect(redirect_url)

                # لیست آبجکت‌های پایتون را به یک رشته JSON تبدیل کرده و سپس به بایت‌های UTF-8 انکود می‌کنیم.
                json_data = json.dumps(data_to_backup_objects, ensure_ascii=False, indent=2).encode('utf-8')
                # داده‌های JSON را با Fernet رمزگذاری می‌کنیم.
                encrypted_data = fernet.encrypt(json_data)

                # یک پاسخ HTTP برای دانلود فایل ایجاد می‌کنیم.
                response = HttpResponse(content=encrypted_data, content_type='application/octet-stream')
                # یک مهر زمانی (timestamp) برای نام فایل بک‌آپ ایجاد می‌کنیم.
                timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
                # هدر Content-Disposition را تنظیم می‌کنیم تا مرورگر فایل را دانلود کند.
                response['Content-Disposition'] = f'attachment; filename="backup_{filename_prefix}_{timestamp}.enc"'

                # پیام موفقیت را ثبت و نمایش می‌دهیم.
                logger.info(
                    f"Encrypted backup created for {selected_model_keys or 'all models'} by user {request.user.username}")
                messages.success(request, ("بک‌آپ رمزگذاری‌شده با موفقیت ایجاد شد. دانلود باید به طور خودکار شروع شود."))
                return response  # بسیار مهم: پاسخ HTTP را برمی‌گردانیم تا دانلود شروع شود.

            except Exception as e:
                # در صورت بروز خطا، آن را ثبت کرده و به کاربر نمایش می‌دهیم.
                logger.error(f"Error creating backup: {e}", exc_info=True)
                messages.error(request,(f"خطا در ایجاد بک‌آپ: {str(e)}"))

        # اگر عملیات 'reset' باشد:
        elif action == 'reset':
            # بررسی می‌کنیم که حداقل یک مدل برای ریست انتخاب شده باشد.
            if not selected_model_keys:
                messages.error(request, ("هیچ مدلی برای ریست انتخاب نشده است."))
                return HttpResponseRedirect(redirect_url)

            try:
                # از یک بلاک تراکنش اتمیک استفاده می‌کنیم. اگر هر بخشی از این بلاک شکست بخورد،
                # تمامی تغییرات دیتابیس (حذف‌ها) برگردانده می‌شوند.
                with transaction.atomic():
                    for model_key in selected_model_keys:
                        app_label, model_name = model_key.split('.')
                        model_class = apps.get_model(app_label, model_name)
                        # تمامی رکوردها را از مدل حذف می‌کنیم.
                        count, _ = model_class.objects.all().delete()
                        # تعداد رکوردهای حذف شده را ثبت می‌کنیم.
                        logger.info(f"Deleted {count} records from {model_key} by user {request.user.username}")
                # پیام موفقیت را نمایش می‌دهیم.
                messages.success(request,
                                 _(f"داده‌های مدل‌های انتخاب‌شده ({', '.join(selected_model_keys)}) با موفقیت ریست شدند."))
            except Exception as e:
                # در صورت بروز خطا، آن را ثبت کرده و به کاربر نمایش می‌دهیم.
                logger.error(f"Error resetting models {selected_model_keys}: {e}", exc_info=True)
                messages.error(request, _(f"خطا در ریست دیتابیس: {str(e)}"))

        # اگر عملیات نامشخص باشد:
        else:
            messages.warning(request, ("عملیات نامشخص است."))

        # در نهایت، کاربر را به صفحه مدیریت دیتابیس ریدایرکت می‌کنیم (اگر دانلود اتفاق نیفتاده باشد).
        return HttpResponseRedirect(redirect_url)

class older__DatabaseManageView(LoginRequiredMixin, View):
    """
    این ویو مسئول مدیریت دیتابیس است که شامل قابلیت‌های بک‌آپ‌گیری (پشتیبان‌گیری)
    از داده‌ها و ساختار دیتابیس (Schema) و ریست (حذف تمامی داده‌ها) برای مدل‌های
    انتخاب شده یا کل دیتابیس می‌شود. این ویو فقط برای کاربران با دسترسی 'superuser'
    قابل دسترس است.
    """
    # مسیر تمپلیت HTML که قرار است برای این ویو رندر شود.
    template_name = 'accounts/DashboardDatabase/Dashboard_admin.html'
    # URLی که کاربر در صورت لاگین نبودن به آن هدایت می‌شود.
    login_url = reverse_lazy('accounts:login')

    # ---
    def get_model_relations(self, model_class):
        """
        این متد روابط یک مدل خاص را (ForeignKey, ManyToManyField, OneToOneField) پیدا کرده
        و اطلاعات مربوط به مدل‌های مرتبط را برمی‌گرداند.
        """
        relations = []  # لیستی برای ذخیره اطلاعات روابط
        # تمامی فیلدهای مدل را پیمایش می‌کنیم.
        for field in model_class._meta.get_fields():
            # بررسی می‌کنیم که آیا فیلد یک نوع رابطه (ForeignKey, ManyToManyField, OneToOneField) است.
            if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
                # متادیتای مدل مرتبط را دریافت می‌کنیم.
                related_model_meta = field.related_model._meta
                # اطلاعات رابطه را به لیست اضافه می‌کنیم.
                relations.append({
                    'field_name': field.name,  # نام فیلد در مدل فعلی
                    'related_model_key': f"{related_model_meta.app_label}.{related_model_meta.model_name}",
                    # کلید مدل مرتبط (مثال: 'app_name.model_name')
                    'related_model_verbose_name': str(related_model_meta.verbose_name),
                    # نام نمایشی مدل مرتبط (برای نمایش در UI)
                    'type': field.__class__.__name__  # نوع رابطه (مثال: 'ForeignKey')
                })
        return relations  # لیست روابط را برمی‌گردانیم.

    def get(self, request):
        """
        این متد درخواست‌های GET را مدیریت می‌کند.
        مسئول نمایش صفحه مدیریت دیتابیس و لیست کردن مدل‌های قابل مدیریت است.
        """
        # بررسی می‌کنیم که آیا کاربر فعلی 'superuser' است یا خیر.
        if not request.user.is_superuser:
            # اگر کاربر سوپریوزر نیست، پیام خطا نمایش داده و به صفحه اصلی هدایت می‌شود.
            messages.error(request, _("فقط مدیران سیستم می‌توانند دیتابیس را مدیریت کنند."))
            return HttpResponseRedirect(reverse_lazy('index'))

        # سعی می‌کنیم app_labels مورد نظر برای مدیریت را از تنظیمات Django بخوانیم.
        # اگر تنظیم نشده باشد، از لیست پیش‌فرض ['core', 'budgets', 'tankhah'] استفاده می‌کنیم.
        app_labels_to_manage = getattr(settings, 'DATABASE_MANAGE_APP_LABELS',
                                       ['core', 'budgets', 'tankhah', 'accounts', 'reports'])

        all_models_info = []  # لیستی برای ذخیره اطلاعات تمامی مدل‌ها
        vis_groups = {}  # دیکشنری برای گروه‌بندی مدل‌ها بر اساس اپ‌ها برای نمایش در vis.js (یک کتابخانه گرافیکی)
        # یک پالت رنگی برای گروه‌های vis.js تعریف می‌کنیم.
        app_colors = ['#e3f2fd', '#e8f5e9', '#fff3e0', '#ffebee', '#f3e5f5', '#e0f7fa', '#fce4ec', '#f1f8e9']

        # هر app_label را که قرار است مدیریت شود، پیمایش می‌کنیم.
        for i, app_label in enumerate(app_labels_to_manage):
            try:
                # پیکربندی (config) برنامه Django را بر اساس app_label دریافت می‌کنیم.
                app_config = apps.get_app_config(app_label)
                # اطلاعات گروه (رنگ و فونت) برای هر اپ را برای استفاده در vis.js ذخیره می‌کنیم.
                vis_groups[app_label] = {
                    'color': {
                        'background': app_colors[i % len(app_colors)],  # رنگ پس‌زمینه از پالت رنگ
                        'border': '#aeaeae',  # رنگ حاشیه
                        'highlight': {  # رنگ هنگام هاور یا انتخاب
                            'background': app_colors[i % len(app_colors)],
                            'border': '#2B7CE9'
                        }
                    },
                    'font': {'color': '#343434'}
                }
                # تمامی مدل‌های موجود در این اپ را پیمایش می‌کنیم.
                for model_class in app_config.get_models():
                    model_meta = model_class._meta  # متادیتای مدل را دریافت می‌کنیم.
                    # اطلاعات مدل را به لیست all_models_info اضافه می‌کنیم.
                    all_models_info.append({
                        'app_label': app_label,  # نام اپلیکیشن
                        'model_name': model_meta.model_name,  # نام مدل (مثال: 'user')
                        'verbose_name': str(model_meta.verbose_name),  # نام نمایشی مدل (برای نمایش در UI)
                        'key': f"{app_label}.{model_meta.model_name}",  # کلید منحصر به فرد مدل (مثال: 'accounts.user')
                        'relations': self.get_model_relations(model_class)  # روابط این مدل
                    })
            except LookupError:
                # اگر اپلیکیشن مورد نظر پیدا نشد یا مدلی نداشت، یک هشدار ثبت می‌کنیم.
                logger.warning(f"App with label '{app_label}' not found or contains no models.")

        # کانتکست (داده‌هایی که به تمپلیت فرستاده می‌شوند) را آماده می‌کنیم.
        context = {
            'title': _('مدیریت دیتابیس (ریست و بک‌آپ)'),  # عنوان صفحه
            # مدل‌ها را بر اساس app_label و سپس verbose_name مرتب می‌کنیم.
            'models': sorted(all_models_info, key=lambda x: (x['app_label'], x['verbose_name'])),
            # گروه‌های vis.js را به فرمت JSON تبدیل می‌کنیم تا در جاوااسکریپت قابل استفاده باشند.
            'vis_groups_json': json.dumps(vis_groups),
        }
        # پیامی را برای دیباگ کردن ثبت می‌کنیم.
        logger.debug(f"Rendering database manage form: models_count={len(all_models_info)}")
        # تمپلیت را با کانتکست رندر کرده و برمی‌گردانیم.
        return render(request, self.template_name, context)

    # ---
    def post(self, request):
        """
        این متد درخواست‌های POST را مدیریت می‌کند.
        مسئول اجرای عملیات بک‌آپ‌گیری و ریست دیتابیس است.
        """
        # مجدداً بررسی می‌کنیم که آیا کاربر سوپریوزر است.
        if not request.user.is_superuser:
            messages.error(request, ("فقط مدیران سیستم می‌توانند دیتابیس را مدیریت کنند."))
            return HttpResponseRedirect(reverse_lazy('index'))  # یا هر صفحه مناسب دیگر

        # نوع عملیات (backup یا reset) را از داده‌های POST دریافت می‌کنیم.
        action = request.POST.get('action')
        # لیست کلیدهای مدل‌های انتخاب شده را دریافت می‌کنیم (مثال: ['app1.model1', 'app2.model2']).
        selected_model_keys = request.POST.getlist('models')
        # رمز عبور وارد شده توسط کاربر را دریافت می‌کنیم.
        password = request.POST.get('password', '')
        # URL برای ریدایرکت پس از انجام عملیات.
        redirect_url = reverse_lazy('database_manage')
        logger.info(f'Redirect url: {redirect_url}')

        # اگر عملیات 'backup' باشد:
        if action == 'backup':
            # بررسی می‌کنیم که رمز عبور وارد شده باشد و حداقل 8 کاراکتر طول داشته باشد.
            if not password or len(password) < 8:
                messages.error(request, ("رمز عبور برای بک‌آپ باید حداقل 8 کاراکتر باشد."))
                return HttpResponseRedirect(redirect_url)

            try:
                # رمز عبور را با SHA256 هش می‌کنیم تا یک هش 32 بایتی داشته باشیم.
                hashed_password = sha256(password.encode('utf-8')).digest()
                # هش 32 بایتی را به فرمت Base64 URL-safe تبدیل می‌کنیم تا کلید Fernet ساخته شود.
                fernet_key = base64.urlsafe_b64encode(hashed_password)
                # یک آبجکت Fernet برای رمزگذاری و رمزگشایی ایجاد می‌کنیم.
                fernet = Fernet(fernet_key)
                logger.info(f'Fernet key generated.')

                # لیستی برای نگهداری آبجکت‌های پایتون که از سریالایز کردن مدل‌ها به دست می‌آیند.
                data_to_backup_objects = []

                # اگر مدل‌های خاصی برای بک‌آپ انتخاب شده باشند:
                if selected_model_keys:
                    for model_key in selected_model_keys:
                        # app_label و model_name را از کلید مدل جدا می‌کنیم.
                        app_label, model_name = model_key.split('.')
                        # کلاس مدل را از Django دریافت می‌کنیم.
                        model_class = apps.get_model(app_label, model_name)
                        # یک بافر متنی در حافظه ایجاد می‌کنیم.
                        output_buffer = StringIO()
                        # تمامی آبجکت‌های مدل را به فرمت JSON سریالایز کرده و به بافر می‌نویسیم.
                        serializers.serialize('json', model_class.objects.all(), stream=output_buffer,
                                              ensure_ascii=False)
                        # محتوای بافر را به صورت JSON بارگذاری کرده و به لیست data_to_backup_objects اضافه می‌کنیم.
                        data_to_backup_objects.extend(json.loads(output_buffer.getvalue()))
                        output_buffer.close()  # بافر را می‌بندیم.
                    # یک پیشوند نام فایل بر اساس مدل‌های انتخاب شده ایجاد می‌کنیم.
                    filename_prefix = "_".join(model_key.replace('.', '_') for model_key in selected_model_keys)
                    logger.info(f'Filename prefix for selected models: {filename_prefix}')
                else:  # اگر هیچ مدلی انتخاب نشده باشد، بک‌آپ کامل دیتابیس را می‌گیریم.
                    output_buffer = StringIO()  # یک بافر متنی در حافظه ایجاد می‌کنیم.
                    # لیست اپلیکیشن‌ها/مدل‌هایی که باید از بک‌آپ کامل حذف شوند.
                    excluded_apps = ['admin.logentry', 'contenttypes', 'auth.permission', 'sessions.session']
                    # دستور `dumpdata` جنگو را برای گرفتن بک‌آپ کامل اجرا می‌کنیم.
                    # `*` برای باز کردن لیست `excluded_apps` به عنوان آرگومان‌های جداگانه است.
                    # `f'--exclude={app}' for app in excluded_apps` هر اپ را به فرمت '--exclude=app_name.model_name' تبدیل می‌کند.
                    management.call_command('dumpdata', *[f'--exclude={app}' for app in excluded_apps],
                                            stdout=output_buffer, format='json')
                    # محتوای بافر را به صورت JSON بارگذاری می‌کنیم.
                    data_to_backup_objects = json.loads(output_buffer.getvalue())
                    output_buffer.close()  # بافر را می‌بندیم.
                    filename_prefix = "full_database"  # پیشوند نام فایل برای بک‌آپ کامل.
                    logger.info(f'Filename prefix for full database: {filename_prefix}')

                # اگر هیچ داده‌ای برای بک‌آپ یافت نشد:
                if not data_to_backup_objects:
                    messages.warning(request,
                                     ("داده‌ای برای بک‌آپ یافت نشد (مدل‌های انتخاب شده ممکن است خالی باشند)."))
                    return HttpResponseRedirect(redirect_url)

                # لیست آبجکت‌های پایتون را به یک رشته JSON تبدیل کرده و سپس به بایت‌های UTF-8 انکود می‌کنیم.
                json_data = json.dumps(data_to_backup_objects, ensure_ascii=False, indent=2).encode('utf-8')
                # داده‌های JSON را با Fernet رمزگذاری می‌کنیم.
                encrypted_data = fernet.encrypt(json_data)

                # یک پاسخ HTTP برای دانلود فایل ایجاد می‌کنیم.
                response = HttpResponse(content=encrypted_data, content_type='application/octet-stream')
                # یک مهر زمانی (timestamp) برای نام فایل بک‌آپ ایجاد می‌کنیم.
                timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
                # هدر Content-Disposition را تنظیم می‌کنیم تا مرورگر فایل را دانلود کند.
                response['Content-Disposition'] = f'attachment; filename="backup_{filename_prefix}_{timestamp}.enc"'

                # پیام موفقیت را ثبت و نمایش می‌دهیم.
                logger.info(
                    f"Encrypted backup created for {selected_model_keys or 'all models'} by user {request.user.username}")
                messages.success(request,
                                 ("بک‌آپ رمزگذاری‌شده با موفقیت ایجاد شد. دانلود باید به طور خودکار شروع شود."))
                return response  # بسیار مهم: پاسخ HTTP را برمی‌گردانیم تا دانلود شروع شود.

            except Exception as e:
                # در صورت بروز خطا، آن را ثبت کرده و به کاربر نمایش می‌دهیم.
                logger.error(f"Error creating backup: {e}", exc_info=True)
                messages.error(request, (f"خطا در ایجاد بک‌آپ: {str(e)}"))

        # اگر عملیات 'reset' باشد:
        elif action == 'reset':
            # بررسی می‌کنیم که حداقل یک مدل برای ریست انتخاب شده باشد.
            if not selected_model_keys:
                messages.error(request, ("هیچ مدلی برای ریست انتخاب نشده است."))
                return HttpResponseRedirect(redirect_url)

            try:
                # از یک بلاک تراکنش اتمیک استفاده می‌کنیم. اگر هر بخشی از این بلاک شکست بخورد،
                # تمامی تغییرات دیتابیس (حذف‌ها) برگردانده می‌شوند.
                with transaction.atomic():
                    for model_key in selected_model_keys:
                        app_label, model_name = model_key.split('.')
                        model_class = apps.get_model(app_label, model_name)
                        # تمامی رکوردها را از مدل حذف می‌کنیم.
                        count, _ = model_class.objects.all().delete()
                        # تعداد رکوردهای حذف شده را ثبت می‌کنیم.
                        logger.info(f"Deleted {count} records from {model_key} by user {request.user.username}")
                # پیام موفقیت را نمایش می‌دهیم.
                messages.success(request,
                                 _(f"داده‌های مدل‌های انتخاب‌شده ({', '.join(selected_model_keys)}) با موفقیت ریست شدند."))
            except Exception as e:
                # در صورت بروز خطا، آن را ثبت کرده و به کاربر نمایش می‌دهیم.
                logger.error(f"Error resetting models {selected_model_keys}: {e}", exc_info=True)
                messages.error(request, _(f"خطا در ریست دیتابیس: {str(e)}"))

        # اگر عملیات نامشخص باشد:
        else:
            messages.warning(request, ("عملیات نامشخص است."))

        # در نهایت، کاربر را به صفحه مدیریت دیتابیس ریدایرکت می‌کنیم (اگر دانلود اتفاق نیفتاده باشد).
        return HttpResponseRedirect(redirect_url)

# ---
class DatabaseBackupRestoreView(LoginRequiredMixin, View):
    """
    ویو مدیریت بک‌آپ و ریست دیتابیس
    امکان بک‌آپ رمزگذاری شده و ریست انتخابی مدل‌ها را فراهم می‌کند
    """
    template_name = 'accounts/DashboardDatabase/database_management.html'
    login_url = reverse_lazy('admin:login')

    def get_model_info(self):
        """اطلاعات تمام مدل‌های قابل مدیریت را جمع‌آوری می‌کند"""
        app_labels = getattr(settings, 'BACKUP_APPS', [
            'auth', 'contenttypes', 'sessions',
            'admin', 'core', 'budgets', 'tankhah'
        ])

        models_data = []
        color_palette = [
            '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e',
            '#e74a3b', '#858796', '#5a5c69', '#3a3b45'
        ]

        for i, app_label in enumerate(app_labels):
            try:
                app_config = apps.get_app_config(app_label)
                for model in app_config.get_models():
                    relations = []
                    for field in model._meta.get_fields():
                        if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
                            related_model = field.related_model
                            relations.append({
                                'name': field.name,
                                'type': field.__class__.__name__,
                                'related_model': f"{related_model._meta.app_label}.{related_model._meta.model_name}",
                                'related_verbose': str(related_model._meta.verbose_name)
                            })

                    models_data.append({
                        'app': app_label,
                        'name': model._meta.model_name,
                        'verbose': str(model._meta.verbose_name),
                        'key': f"{app_label}.{model._meta.model_name}",
                        'relations': relations,
                        'color': color_palette[i % len(color_palette)]
                    })
            except Exception as e:
                logger.error(f"Error processing app {app_label}: {str(e)}")

        return sorted(models_data, key=lambda x: (x['app'], x['verbose']))

    def get(self, request):
        """نمایش صفحه مدیریت"""
        if not request.user.is_superuser:
            messages.error(request, _("تنها مدیران سیستم می‌توانند به این بخش دسترسی داشته باشند"))
            return HttpResponseRedirect(reverse_lazy('admin:index'))

        context = {
            'title': _('مدیریت بک‌آپ و ریست دیتابیس'),
            'models': self.get_model_info(),
            'can_backup': True,
            'can_restore': True
        }
        return render(request, self.template_name, context)

    def post(self, request):
        """پردازش عملیات بک‌آپ یا ریست"""
        if not request.user.is_superuser:
            messages.error(request, _("دسترسی غیرمجاز"))
            return HttpResponseRedirect(reverse_lazy('admin:index'))

        action = request.POST.get('action')
        model_keys = request.POST.getlist('models')
        password = request.POST.get('password', '')

        if action == 'backup':
            return self.handle_backup(request, model_keys, password)
        elif action == 'reset':
            return self.handle_reset(request, model_keys)
        else:
            messages.warning(request, _("عملیات نامشخص"))
            return HttpResponseRedirect(reverse_lazy('new_databasebackup'))

    def handle_backup(self, request, model_keys, password):
        """مدیریت عملیات بک‌آپ"""
        if len(password) < 8:
            messages.error(request, _("رمز عبور باید حداقل 8 کاراکتر باشد"))
            return HttpResponseRedirect(reverse_lazy('new_databasebackup'))

        try:
            # تولید کلید رمزنگاری
            hashed = sha256(password.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(hashed)
            fernet = Fernet(fernet_key)

            # جمع‌آوری داده‌ها
            if model_keys:
                data = []
                for key in model_keys:
                    app, model = key.split('.')
                    model_class = apps.get_model(app, model)
                    serialized = serializers.serialize('json', model_class.objects.all())
                    data.extend(json.loads(serialized))
                filename = f"backup_{'_'.join(model_keys)}_{timezone.now().strftime('%Y%m%d_%H%M')}.enc"
            else:
                output = StringIO()
                call_command('dumpdata', exclude=['contenttypes', 'auth.permission', 'sessions'], stdout=output)
                data = json.loads(output.getvalue())
                output.close()
                filename = f"full_backup_{timezone.now().strftime('%Y%m%d_%H%M')}.enc"

            # رمزگذاری و دانلود
            encrypted = fernet.encrypt(json.dumps(data).encode())
            response = HttpResponse(encrypted, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            messages.success(request, _("بک‌آپ با موفقیت ایجاد شد"))
            return response

        except Exception as e:
            logger.error(f"Backup error: {str(e)}")
            messages.error(request, _("خطا در ایجاد بک‌آپ") + f": {str(e)}")
            return HttpResponseRedirect(reverse_lazy('new_databasebackup'))

    def handle_reset(self, request, model_keys):
        """مدیریت عملیات ریست"""
        if not model_keys:
            messages.error(request, ("هیچ مدلی انتخاب نشده است"))
            return HttpResponseRedirect(reverse_lazy('new_databasebackup'))

        try:
            with transaction.atomic():
                for key in model_keys:
                    app, model = key.split('.')
                    model_class = apps.get_model(app, model)
                    count, _ = model_class.objects.all().delete()
                    logger.info(f"Reset {key}: deleted {count} records")

            messages.success(request, _("داده‌های انتخاب شده با موفقیت ریست شدند"))
            return HttpResponseRedirect(reverse_lazy('new_databasebackup'))

        except Exception as e:
            logger.error(f"Reset error: {str(e)}")
            messages.error(request, _("خطا در ریست داده‌ها") + f": {str(e)}")
            return HttpResponseRedirect(reverse_lazy('new_databasebackup'))
# ---
class oooooooo_DatabaseManageView(LoginRequiredMixin, View):
    """
    این ویو مسئول مدیریت دیتابیس است که شامل قابلیت‌های بک‌آپ‌گیری (پشتیبان‌گیری)
    از داده‌ها و ساختار دیتابیس (Schema) و ریست (حذف تمامی داده‌ها) برای مدل‌ها
    می‌شود. این ویو فقط برای کاربران با دسترسی 'superuser' قابل دسترس است.
    """
    template_name = 'accounts/DashboardDatabase/Dashboard_admin.html'
    login_url = reverse_lazy('accounts:login')

    def get_model_relations(self, model_class):
        """
        این متد روابط یک مدل خاص را (ForeignKey, ManyToManyField, OneToOneField) پیدا کرده
        و اطلاعات مربوط به مدل‌های مرتبط را برمی‌گرداند.
        """
        relations = []
        for field in model_class._meta.get_fields():
            if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
                related_model_meta = field.related_model._meta
                relations.append({
                    'field_name': field.name,
                    'related_model_key': f"{related_model_meta.app_label}.{related_model_meta.model_name}",
                    'related_model_verbose_name': str(related_model_meta.verbose_name),
                    'type': field.__class__.__name__
                })
        return relations

    def get(self, request):
        """
        این متد درخواست‌های GET را مدیریت می‌کند.
        مسئول نمایش صفحه مدیریت دیتابیس و لیست کردن مدل‌های قابل مدیریت است.
        """
        if not request.user.is_superuser:
            messages.error(request, _("فقط مدیران سیستم می‌توانند دیتابیس را مدیریت کنند."))
            return HttpResponseRedirect(reverse_lazy('index'))

        app_labels_to_manage = getattr(settings, 'DATABASE_MANAGE_APP_LABELS',
                                       ['core', 'budgets', 'tankhah', 'accounts', 'reports'])

        all_models_info = []
        # 'vis_groups' و رنگ‌ها برای نمایش‌های گرافیکی (مثلا با vis.js) کاربرد دارند.
        # اگر از vis.js استفاده نمی‌کنید، این بخش برای نمایش عادی لازم نیست اما ضرری هم ندارد.
        vis_groups = {}
        app_colors = ['#e3f2fd', '#e8f5e9', '#fff3e0', '#ffebee', '#f3e5f5', '#e0f7fa', '#fce4ec', '#f1f8e9']

        for i, app_label in enumerate(app_labels_to_manage):
            try:
                app_config = apps.get_app_config(app_label)
                vis_groups[app_label] = {
                    'color': {
                        'background': app_colors[i % len(app_colors)],
                        'border': '#aeaeae',
                        'highlight': {
                            'background': app_colors[i % len(app_colors)],
                            'border': '#2B7CE9'
                        }
                    },
                    'font': {'color': '#343434'}
                }
                for model_class in app_config.get_models():
                    model_meta = model_class._meta
                    # اضافه کردن تعداد رکوردها به اطلاعات مدل
                    try:
                        record_count = model_class.objects.count()
                    except Exception as e:
                        logger.warning(f"Could not count records for {model_class.__name__}: {e}")
                        record_count = 'N/A'  # Not Available

                    all_models_info.append({
                        'app_label': app_label,
                        'model_name': model_meta.model_name,
                        'verbose_name': str(model_meta.verbose_name),
                        'key': f"{app_label}.{model_meta.model_name}",
                        'relations': self.get_model_relations(model_class),
                        'record_count': record_count,  # اضافه شدن تعداد رکوردها
                    })
            except LookupError:
                logger.warning(f"App with label '{app_label}' not found or contains no models.")

        context = {
            'title': _('مدیریت دیتابیس (ریست و بک‌آپ)'),
            'models': sorted(all_models_info, key=lambda x: (x['app_label'], x['verbose_name'])),
            'vis_groups_json': json.dumps(vis_groups),  # همچنان اگر برای نمایش گرافیکی نیاز دارید
        }
        logger.debug(f"Rendering database manage form: models_count={len(all_models_info)}")
        return render(request, self.template_name, context)

    def post(self, request):
        """
        این متد درخواست‌های POST را مدیریت می‌کند.
        مسئول اجرای عملیات بک‌آپ‌گیری و ریست دیتابیس است.
        """
        if not request.user.is_superuser:
            messages.error(request,  ("فقط مدیران سیستم می‌توانند دیتابیس را مدیریت کنند."))
            return HttpResponseRedirect(reverse_lazy('index'))

        action = request.POST.get('action')
        selected_model_keys = request.POST.getlist('models')
        password = request.POST.get('password', '')
        redirect_url = reverse_lazy('database_manage')
        logger.info(f'Redirect url: {redirect_url}')

        # --- عملیات بک‌آپ داده‌ها (Data Backup) ---
        if action == 'backup_data':
            if not password or len(password) < 8:
                messages.error(request, ("رمز عبور برای بک‌آپ داده باید حداقل 8 کاراکتر باشد."))
                return HttpResponseRedirect(redirect_url)

            try:
                hashed_password = sha256(password.encode('utf-8')).digest()
                fernet_key = base64.urlsafe_b64encode(hashed_password)
                fernet = Fernet(fernet_key)
                logger.info(f'Fernet key generated for data backup.')

                output_buffer = StringIO()
                # لیست اپلیکیشن‌ها/مدل‌هایی که باید از بک‌آپ کامل حذف شوند.
                # اینها معمولاً مدل‌های سیستمی هستند که نیازی به بک‌آپ از داده‌هایشان نیست.
                # 'auth.user' را هم اضافه کردم اگر نمی‌خواهید اطلاعات کاربران را در بک‌آپ داده‌ها داشته باشید.
                excluded_apps = [
                    'admin.logentry', 'contenttypes', 'auth.permission',
                    'sessions.session', 'auth.group', 'auth.user'  # اگر داده‌های کاربر را نمی‌خواهید
                ]

                # **بک‌آپ کامل تمامی مدل‌ها (داده‌ها) به فرمت JSON:**
                management.call_command(
                    'dumpdata',
                    *[f'--exclude={app}' for app in excluded_apps],
                    stdout=output_buffer,
                    format='json'
                )
                data_to_backup_objects = json.loads(output_buffer.getvalue())
                output_buffer.close()
                filename_prefix = "full_data_backup"
                logger.info(f'Filename prefix for full data backup: {filename_prefix}')

                if not data_to_backup_objects:
                    messages.warning(request, ("داده‌ای برای بک‌آپ یافت نشد (دیتابیس ممکن است خالی باشد)."))
                    return HttpResponseRedirect(redirect_url)

                json_data = json.dumps(data_to_backup_objects, ensure_ascii=False, indent=2).encode('utf-8')
                encrypted_data = fernet.encrypt(json_data)

                response = HttpResponse(content=encrypted_data, content_type='application/octet-stream')
                timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
                response[
                    'Content-Disposition'] = f'attachment; filename="backup_data_{filename_prefix}_{timestamp}.enc"'

                logger.info(f"Encrypted data backup created by user {request.user.username}")
                messages.success(request,
                                 ("بک‌آپ رمزگذاری‌شده داده با موفقیت ایجاد شد. دانلود باید به طور خودکار شروع شود."))
                return response

            except Exception as e:
                logger.error(f"Error creating data backup: {e}", exc_info=True)
                messages.error(request, (f"خطا در ایجاد بک‌آپ داده: {str(e)}"))

        # --- عملیات بک‌آپ Schema (ساختار دیتابیس) ---
        elif action == 'backup_schema':
            try:
                db_settings = settings.DATABASES['default']
                db_engine = db_settings['ENGINE']
                db_name = db_settings['NAME']
                db_user = db_settings['USER']
                db_password = db_settings['PASSWORD']  # رمز عبور دیتابیس

                schema_backup_output_buffer = StringIO()
                filename_prefix = "schema_backup"
                filename_suffix = "sql"

                if 'mysql' in db_engine:
                    command = [
                        'mysqldump',
                        '--no-data',
                        '-h', db_settings.get('HOST', 'localhost'),
                        '-P', str(db_settings.get('PORT', 3306)),
                        '-u', db_user,
                        f'--password={db_password}',  # ! توجه: رمز عبور مستقیماً در آرگومان‌های خط فرمان قرار می‌گیرد !
                        db_name
                    ]
                    logger.info(f"Executing MySQL schema backup command.")
                    process = subprocess.run(command, capture_output=True, text=True, check=True)
                    schema_backup_output_buffer.write(process.stdout)

                elif 'postgresql' in db_engine:
                    command = [
                        'pg_dump',
                        '--schema-only',
                        '-h', db_settings.get('HOST', 'localhost'),
                        '-p', str(db_settings.get('PORT', 5432)),
                        '-U', db_user,
                        db_name
                    ]
                    env = {'PGPASSWORD': db_password, **os.environ}
                    logger.info(f"Executing PostgreSQL schema backup command.")
                    process = subprocess.run(command, capture_output=True, text=True, env=env, check=True)
                    schema_backup_output_buffer.write(process.stdout)

                elif 'sqlite3' in db_engine:
                    db_path = os.path.join(settings.BASE_DIR, db_name)
                    if not os.path.exists(db_path):
                        raise FileNotFoundError(f"SQLite database file not found at {db_path}")

                    sqlite_command = ['sqlite3', db_path, '.schema']
                    logger.info(f"Executing SQLite schema backup command.")
                    process = subprocess.run(sqlite_command, capture_output=True, text=True, check=True)
                    schema_backup_output_buffer.write(process.stdout)

                else:
                    messages.error(request,  ("نوع دیتابیس شما برای بک‌آپ Schema پشتیبانی نمی‌شود."))
                    return HttpResponseRedirect(redirect_url)

                if not schema_backup_output_buffer.getvalue():
                    messages.warning(request,
                                     ("خروجی بک‌آپ Schema خالی است. شاید دیتابیس خالی باشد یا خطایی رخ داده باشد."))
                    return HttpResponseRedirect(redirect_url)

                schema_data_bytes = schema_backup_output_buffer.getvalue().encode('utf-8')
                schema_backup_output_buffer.close()

                response = HttpResponse(content=schema_data_bytes, content_type='application/sql')
                timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
                response[
                    'Content-Disposition'] = f'attachment; filename="backup_{filename_prefix}_{timestamp}.{filename_suffix}"'

                logger.info(f"Schema backup created by user {request.user.username}")
                messages.success(request, ("بک‌آپ Schema با موفقیت ایجاد شد. دانلود باید به طور خودکار شروع شود."))
                return response

            except subprocess.CalledProcessError as e:
                logger.error(f"Error executing database schema backup command: {e.stderr}", exc_info=True)
                messages.error(request,  (f"خطا در اجرای دستور بک‌آپ Schema: {e.stderr or str(e)}"))
            except FileNotFoundError:
                logger.error(
                    "Database backup utility (mysqldump/pg_dump/sqlite3) not found. Make sure it's installed and in PATH.")
                messages.error(request,
                                ("ابزار بک‌آپ دیتابیس (مانند mysqldump) پیدا نشد. لطفاً آن را نصب کرده و اطمینان حاصل کنید که در PATH سرور موجود است."))
            except Exception as e:
                logger.error(f"Error creating schema backup: {e}", exc_info=True)
                messages.error(request,  (f"خطا کلی در ایجاد بک‌آپ Schema: {str(e)}"))

        # --- عملیات ریست داده‌ها ---
        elif action == 'reset':
            if not selected_model_keys:
                messages.error(request, ("هیچ مدلی برای ریست انتخاب نشده است."))
                return HttpResponseRedirect(redirect_url)

            try:
                with transaction.atomic():
                    for model_key in selected_model_keys:
                        app_label, model_name = model_key.split('.')
                        model_class = apps.get_model(app_label, model_name)
                        count, _ = model_class.objects.all().delete()
                        logger.info(f"Deleted {count} records from {model_key} by user {request.user.username}")
                messages.success(request,
                                 _(f"داده‌های مدل‌های انتخاب‌شده ({', '.join(selected_model_keys)}) با موفقیت ریست شدند."))
            except Exception as e:
                logger.error(f"Error resetting models {selected_model_keys}: {e}", exc_info=True)
                messages.error(request, _(f"خطا در ریست دیتابیس: {str(e)}"))

        else:
            messages.warning(request, ("عملیات نامشخص است."))

        return HttpResponseRedirect(redirect_url)

class DatabaseBackupRView(FormView):
    template_name = 'accounts/DashboardDatabase/backupR.html'
    form_class = DatabaseBackupForm
    success_url = reverse_lazy('database_backup')

    def form_valid(self, form):
        db_type = form.cleaned_data['database_type']
        output_format = form.cleaned_data['format']
        password = form.cleaned_data['password']
        reset_models = form.cleaned_data['reset_models']
        models_to_reset = form.cleaned_data['models_to_reset']

        # تنظیمات دیتابیس
        db_settings = settings.DATABASES['default']
        db_name = db_settings['NAME']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.sql')
        backup_filename = f"backup_{db_type}_{timestamp}"

        try:
            # ایجاد بک‌آپ با django-dbbackup
            if db_type == 'mysql':
                call_command('dbbackup', database='default', output=temp_file.name, compress=False)
            elif db_type == 'postgresql':
                call_command('dbbackup', database='default', output=temp_file.name, compress=False)
            else:
                messages.error(self.request, _("نوع دیتابیس نامعتبر است."))
                return self.form_invalid(form)

            final_path = temp_file.name
            if output_format == 'zip':
                zip_path = f"{temp_file.name}.zip"
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(temp_file.name, arcname=os.path.basename(temp_file.name))
                    if password:
                        # رمزگذاری با GPG (نیاز به python-gnupg)
                        try:
                            with open(temp_file.name, 'rb') as f:
                                encrypted_data = encrypt_file(f, password)
                            with open(temp_file.name + '.gpg', 'wb') as f:
                                f.write(encrypted_data)
                            zipf.write(temp_file.name + '.gpg', arcname=f"{backup_filename}.sql.gpg")
                        except Exception as e:
                            logger.error(f"Encryption failed: {e}", exc_info=True)
                            messages.error(self.request, f"خطا در رمزگذاری: {str(e)}")
                            return self.form_invalid(form)
                final_path = zip_path
                backup_filename += '.zip'

            # ریست مدل‌ها
            if reset_models and models_to_reset:
                with connection.cursor() as cursor:
                    for model_name in models_to_reset.split(','):
                        model_name = model_name.strip()
                        try:
                            cursor.execute(f"DROP TABLE IF EXISTS {model_name} CASCADE;")
                            logger.info(f"Table {model_name} dropped by {self.request.user.username}")
                        except Exception as e:
                            logger.error(f"Error dropping table {model_name}: {e}", exc_info=True)
                            messages.error(self.request, f"خطا در ریست جدول {model_name}: {str(e)}")
                            return self.form_invalid(form)
                messages.success(self.request, _("جدول‌های انتخاب‌شده با موفقیت ریست شدند."))

            # پاسخ با فایل
            response = FileResponse(
                open(final_path, 'rb'),
                as_attachment=True,
                filename=backup_filename
            )
            messages.success(self.request, _("بکاپ با موفقیت ایجاد شد."))
            logger.info(f"Backup created: {backup_filename} by {self.request.user.username}")
            return response

        except Exception as e:
            logger.error(f"Backup failed: {e}", exc_info=True)
            messages.error(self.request, f"خطا در ایجاد بک‌آپ: {str(e)}")
            return self.form_invalid(form)

        finally:
            # پاکسازی فایل‌های موقت
            for path in [temp_file.name, f"{temp_file.name}.zip", f"{temp_file.name}.gpg"]:
                if os.path.exists(path):
                    os.unlink(path)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("ایجاد بکاپ دیتابیس")
        context['db_type'] = settings.DATABASES['default']['ENGINE'].split('.')[-1]
        return context

# ---
# مهم: مطمئن شوید 'cryptography' نصب شده است: pip install cryptography
class DatabaseManageView(LoginRequiredMixin, View):
    """
    این ویو مسئول مدیریت دیتابیس است که شامل قابلیت‌های بک‌آپ‌گیری (پشتیبان‌گیری)
    از داده‌ها و ساختار دیتابیس (Schema) و ریست (حذف تمامی داده‌ها) برای مدل‌ها
    می‌شود. این ویو فقط برای کاربران با دسترسی 'superuser' قابل دسترس است.
    """
    template_name = 'accounts/DashboardDatabase/Dashboard_admin_1.html'
    login_url = reverse_lazy('accounts:login')  # آدرس صفحه ورود شما

    def get_model_relations(self, model_class):
        """
        این متد روابط یک مدل خاص را (ForeignKey, ManyToManyField, OneToOneField) پیدا کرده
        و اطلاعات مربوط به مدل‌های مرتبط را برمی‌گرداند.
        """
        relations = []
        for field in model_class._meta.get_fields():
            if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
                related_model_meta = field.related_model._meta
                relations.append({
                    'field_name': field.name,
                    'related_model_key': f"{related_model_meta.app_label}.{related_model_meta.model_name}",
                    'related_model_verbose_name': str(related_model_meta.verbose_name),
                    'type': field.__class__.__name__
                })
        return relations

    def get(self, request, *args, **kwargs):
        """
        این متد درخواست‌های GET را مدیریت می‌کند و صفحه مدیریت دیتابیس را نمایش می‌دهد.
        مدل‌های قابل مدیریت را لیست کرده و اطلاعات آن‌ها را به تمپلیت ارسال می‌کند.
        """
        if not request.user.is_superuser:
            messages.error(request, _("فقط مدیران سیستم می‌توانند دیتابیس را مدیریت کنند."))
            return HttpResponseRedirect(reverse_lazy('index'))  # آدرس صفحه اصلی یا داشبورد

        # اپلیکیشن‌هایی که می‌خواهید مدل‌هایشان در بخش مدیریت دیتابیس نمایش داده شوند.
        # می‌توانید این لیست را در settings.py هم تعریف کنید: DATABASE_MANAGE_APP_LABELS
        app_labels_to_manage = getattr(settings, 'DATABASE_MANAGE_APP_LABELS',
                                       ['core', 'budgets', 'tankhah', 'accounts', 'reports'])

        all_models_info = []
        for app_label in app_labels_to_manage:
            try:
                app_config = apps.get_app_config(app_label)
                for model_class in app_config.get_models():
                    model_meta = model_class._meta
                    try:
                        record_count = model_class.objects.count()
                    except Exception as e:
                        logger.warning(f"Could not count records for {model_class.__name__}: {e}")
                        record_count = _('خطا در محاسبه')  # یا 'N/A'

                    all_models_info.append({
                        'app_label': app_label,
                        'model_name': model_meta.model_name,
                        'verbose_name': str(model_meta.verbose_name),
                        'key': f"{app_label}.{model_meta.model_name}",
                        'relations': self.get_model_relations(model_class),
                        'record_count': record_count,
                    })
            except LookupError:
                logger.warning(f"App with label '{app_label}' not found or contains no models.")

        context = {
            'title': _('مدیریت دیتابیس (ریست و بک‌آپ)'),
            # مدل‌ها را بر اساس نام اپلیکیشن و نام نمایشی مرتب می‌کنیم.
            'models': sorted(all_models_info, key=lambda x: (x['app_label'], x['verbose_name'])),
        }
        logger.debug(f"Rendering database manage form: models_count={len(all_models_info)}")
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        این متد درخواست‌های POST را مدیریت می‌کند و عملیات بک‌آپ‌گیری یا ریست را اجرا می‌کند.
        """
        if not request.user.is_superuser:
            messages.error(request("فقط مدیران سیستم می‌توانند دیتابیس را مدیریت کنند."))
            return HttpResponseRedirect(reverse_lazy('index'))

        action = request.POST.get('action')
        # models برای عملیات ریست استفاده می‌شود
        selected_model_keys = request.POST.getlist('models')
        # password فقط برای بک‌آپ داده‌ها استفاده می‌شود
        password = request.POST.get('password', '')
        redirect_url = reverse_lazy('database_manage')
        # logger.info(f'Redirect url: {redirect_url}')

        # --- عملیات بک‌آپ داده‌ها (Full Data Backup - Encrypted JSON) ---
        if action == 'backup_data':
            if not password or len(password) < 8:
                messages.error(request("رمز عبور برای بک‌آپ داده باید حداقل 8 کاراکتر باشد."))
                return HttpResponseRedirect(redirect_url)

            try:
                # ایجاد کلید رمزگذاری از رمز عبور کاربر
                hashed_password = sha256(password.encode('utf-8')).digest()
                fernet_key = base64.urlsafe_b64encode(hashed_password)
                fernet = Fernet(fernet_key)
                logger.info(f'Fernet key generated for data backup.')

                output_buffer = StringIO()
                # لیست اپلیکیشن‌ها/مدل‌هایی که از بک‌آپ کامل داده‌ها حذف می‌شوند.
                # معمولاً مدل‌های سیستمی که نیازی به بک‌آپ داده‌هایشان نیست.
                # 'auth.user' را هم می‌توانید اضافه کنید اگر نمی‌خواهید اطلاعات کاربران را در بک‌آپ داده‌ها داشته باشید.
                excluded_apps = [
                    'admin.logentry', 'contenttypes', 'auth.permission',
                    'sessions.session', 'auth.group',  # 'auth.user'
                ]

                # اجرای دستور dumpdata برای گرفتن بک‌آپ از داده‌ها به فرمت JSON
                management.call_command(
                    'dumpdata',
                    *[f'--exclude={app}' for app in excluded_apps],
                    stdout=output_buffer,
                    format='json',
                    # --indent 2 برای خوانایی بهتر فایل JSON خروجی
                    # --natural-foreign و --natural-primary برای بک‌آپ داده‌های مرتبط بهتر
                    # '--indent=2', '--natural-foreign', '--natural-primary'
                )

                data_to_backup_json = output_buffer.getvalue().encode('utf-8')
                output_buffer.close()

                if not data_to_backup_json.strip():  # بررسی کنید که خروجی خالی نباشد
                    messages.warning(request("داده‌ای برای بک‌آپ یافت نشد (دیتابیس ممکن است خالی باشد)."))
                    return HttpResponseRedirect(redirect_url)

                encrypted_data = fernet.encrypt(data_to_backup_json)

                response = HttpResponse(content=encrypted_data, content_type='application/octet-stream')
                timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
                response['Content-Disposition'] = f'attachment; filename="backup_data_encrypted_{timestamp}.enc"'

                logger.info(f"Encrypted data backup created by user {request.user.username}")
                messages.success(request,
                                  ("بک‌آپ رمزگذاری‌شده داده با موفقیت ایجاد شد. دانلود باید به طور خودکار شروع شود."))
                return response

            except Exception as e:
                logger.error(f"Error creating data backup: {e}", exc_info=True)
                messages.error(request(f"خطا در ایجاد بک‌آپ داده: {str(e)}"))

        # --- عملیات بک‌آپ Schema (ساختار دیتابیس به فرمت SQL) ---
        elif action == 'backup_schema':
            try:
                db_settings = settings.DATABASES['default']
                db_engine = db_settings['ENGINE']
                db_name = db_settings['NAME']
                db_user = db_settings['USER']
                db_password = db_settings['PASSWORD']

                schema_backup_output_buffer = StringIO()
                filename_prefix = "schema_backup"
                filename_suffix = "sql"

                # دستورات بومی برای بک‌آپ Schema بر اساس نوع دیتابیس
                if 'mysql' in db_engine:
                    command = [
                        'mysqldump',
                        '--no-data',  # فقط ساختار را بدون داده‌ها بک‌آپ می‌گیرد.
                        '-h', db_settings.get('HOST', 'localhost'),
                        '-P', str(db_settings.get('PORT', 3306)),
                        '-u', db_user,
                        f'--password={db_password}',  # ! توجه: رمز عبور مستقیماً در آرگومان‌های خط فرمان قرار می‌گیرد.
                        # برای امنیت بیشتر، از فایل ~/.my.cnf یا stdin استفاده کنید.
                        db_name
                    ]
                    process = subprocess.run(command, capture_output=True, text=True, check=True)
                    schema_backup_output_buffer.write(process.stdout)

                elif 'postgresql' in db_engine:
                    command = [
                        'pg_dump',
                        '--schema-only',  # فقط ساختار را بدون داده‌ها بک‌آپ می‌گیرد.
                        '-h', db_settings.get('HOST', 'localhost'),
                        '-p', str(db_settings.get('PORT', 5432)),
                        '-U', db_user,
                        db_name
                    ]
                    env = {'PGPASSWORD': db_password, **os.environ}  # رمز عبور از طریق متغیر محیطی (امن‌تر)
                    process = subprocess.run(command, capture_output=True, text=True, env=env, check=True)
                    schema_backup_output_buffer.write(process.stdout)

                elif 'sqlite3' in db_engine:
                    db_path = os.path.join(settings.BASE_DIR, db_name)
                    if not os.path.exists(db_path):
                        raise FileNotFoundError(f"SQLite database file not found at {db_path}")

                    sqlite_command = ['sqlite3', db_path, '.schema']  # دستور SQLite برای گرفتن Schema
                    process = subprocess.run(sqlite_command, capture_output=True, text=True, check=True)
                    schema_backup_output_buffer.write(process.stdout)

                else:
                    messages.error(request("نوع دیتابیس شما برای بک‌آپ Schema پشتیبانی نمی‌شود."))
                    return HttpResponseRedirect(redirect_url)

                if not schema_backup_output_buffer.getvalue().strip():
                    messages.warning(request,
                                      ("خروجی بک‌آپ Schema خالی است. شاید دیتابیس خالی باشد یا خطایی رخ داده باشد."))
                    return HttpResponseRedirect(redirect_url)

                schema_data_bytes = schema_backup_output_buffer.getvalue().encode('utf-8')
                schema_backup_output_buffer.close()

                response = HttpResponse(content=schema_data_bytes, content_type='application/sql')
                timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
                response[
                    'Content-Disposition'] = f'attachment; filename="backup_{filename_prefix}_{timestamp}.{filename_suffix}"'

                logger.info(f"Schema backup created by user {request.user.username}")
                messages.success(request("بک‌آپ Schema با موفقیت ایجاد شد. دانلود باید به طور خودکار شروع شود."))
                return response

            except subprocess.CalledProcessError as e:
                logger.error(f"Error executing database schema backup command: {e.stderr}", exc_info=True)
                messages.error(request(f"خطا در اجرای دستور بک‌آپ Schema: {e.stderr or str(e)}"))
            except FileNotFoundError:
                logger.error(
                    "Database backup utility (mysqldump/pg_dump/sqlite3) not found. Make sure it's installed and in PATH.")
                messages.error(request,
                               ("ابزار بک‌آپ دیتابیس (مانند mysqldump) پیدا نشد. لطفاً آن را نصب کرده و اطمینان حاصل کنید که در PATH سرور موجود است."))
            except Exception as e:
                logger.error(f"General error creating schema backup: {e}", exc_info=True)
                messages.error(request(f"خطا کلی در ایجاد بک‌آپ Schema: {str(e)}"))

        # --- عملیات ریست داده‌ها (Delete All Data for Selected Models) ---
        elif action == 'reset':
            if not selected_model_keys:
                messages.error(request("هیچ مدلی برای ریست انتخاب نشده است."))
                return HttpResponseRedirect(redirect_url)

            try:
                with transaction.atomic():  # استفاده از transaction برای اطمینان از کامل بودن عملیات
                    for model_key in selected_model_keys:
                        app_label, model_name = model_key.split('.')
                        model_class = apps.get_model(app_label, model_name)
                        # حذف تمامی رکوردها با استفاده از ORM جنگو
                        count, _ = model_class.objects.all().delete()
                        logger.info(f"Deleted {count} records from {model_key} by user {request.user.username}")
                messages.success(request,
                                 _(f"داده‌های مدل‌های انتخاب‌شده ({', '.join(selected_model_keys)}) با موفقیت ریست شدند."))
            except Exception as e:
                logger.error(f"Error resetting models {selected_model_keys}: {e}", exc_info=True)
                messages.error(request(f"خطا در ریست دیتابیس: {str(e)}"))

        else:
            messages.warning(request("عملیات نامشخص است."))

        return HttpResponseRedirect(redirect_url)

class SupervisorAndAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy('accounts:login')

    def test_func(self):
        return self.request.user.is_superuser  # فقط سوپریوزرها

    def handle_no_permission(self):
        messages.error(self.request, _("شما دسترسی لازم برای مدیریت دیتابیس را ندارید."))
        return HttpResponseRedirect(reverse_lazy('index'))

class new_DatabaseBackupRestoreView(SupervisorAndAdminRequiredMixin, View):
    template_name = 'accounts/DashboardDatabase/Dashboard_admin_d.html'

    def get_model_relations(self, model_class):
        from django.db.models import ForeignKey, ManyToManyField, OneToOneField
        relations = []
        for field in model_class._meta.get_fields():
            if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
                related_model_meta = field.related_model._meta
                relations.append({
                    'field_name': field.name,
                    'related_model_key': f"{related_model_meta.app_label}.{related_model_meta.model_name}",
                    'related_model_verbose_name': str(related_model_meta.verbose_name),
                    'type': field.__class__.__name__
                })
        return relations

    def get_existing_backups(self):
        from django.conf import settings
        backup_dir = settings.DBBACKUP_STORAGE_OPTIONS.get('location', os.path.join(settings.MEDIA_ROOT, 'backups'))
        if not os.path.isdir(backup_dir):
            logger.warning(f"Backup directory not found: {backup_dir}")
            return []

        backup_files = []
        for filepath in glob.glob(os.path.join(backup_dir, '*.*')):
            filename = os.path.basename(filepath)
            file_type = 'Database' if '_db_' in filename or filename.endswith('.enc') else 'Media'
            backup_files.append({
                'filename': filename,
                'filepath': filepath,
                'size': os.path.getsize(filepath),
                'last_modified': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S'),
                'type': file_type,
                'is_encrypted': filename.endswith('.enc'),
                'is_compressed': filename.endswith('.gz') or filename.endswith('.bz2')
            })
        return sorted(backup_files, key=lambda x: x['last_modified'], reverse=True)

    def get(self, request):
        excluded_apps = ['contenttypes', 'sessions', 'admin', 'auth', 'dbbackup']
        all_models_info = []

        for app_config in apps.get_app_configs():
            if app_config.label in excluded_apps:
                continue
            for model_class in app_config.get_models():
                model_meta = model_class._meta
                try:
                    record_count = model_class.objects.count()
                except Exception as e:
                    logger.warning(f"Could not count records for {model_class.__name__}: {e}")
                    record_count = 'N/A'
                all_models_info.append({
                    'app_label': app_config.label,
                    'model_name': model_meta.model_name,
                    'verbose_name': str(model_meta.verbose_name),
                    'key': f"{app_config.label}.{model_meta.model_name}",
                    'relations': self.get_model_relations(model_class),
                    'record_count': record_count
                })

        context = {
            'title': _('مدیریت دیتابیس (بک‌آپ و ریست)'),
            'models': sorted(all_models_info, key=lambda x: (x['app_label'], x['verbose_name'])),
            'existing_backups': self.get_existing_backups(),
            'is_superuser': request.user.is_superuser,
            'app_labels': [app.label for app in apps.get_app_configs() if app.label not in excluded_apps]
        }
        logger.debug(f"Rendering database manage form: models_count={len(all_models_info)}")
        return render(request, self.template_name, context)

    @staticmethod
    def encrypt_file(file, password):
        salt = b'fixed_salt_16_bytes'  # salt ثابت برای رمزنگاری و رمزگشایی
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        fernet = Fernet(key)
        return fernet.encrypt(file.read()), salt

    @staticmethod
    def decrypt_file(data, password, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        fernet = Fernet(key)
        return fernet.decrypt(data)

    def post(self, request):
        from django.conf import settings
        action = request.POST.get('action')
        selected_model_keys = request.POST.getlist('models')
        password = request.POST.get('password', '')
        backup_file = request.FILES.get('backup_file') or request.POST.get('backup_file_to_restore', '')
        save_to_server = request.POST.get('save_to_server', 'false') == 'true'
        redirect_url = reverse_lazy('accounts:new_databasebackup')

        if action == 'backup_data':
            if not password or len(password) < 8 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
                messages.error(request,  ("رمز باید حداقل 8 کاراکتر با حروف و اعداد باشد."))
                return HttpResponseRedirect(redirect_url)
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
                    if selected_model_keys:
                        data = []
                        for model_key in selected_model_keys:
                            app_label, model_name = model_key.split('.')
                            model_class = apps.get_model(app_label, model_name)
                            if model_class.objects.exists():
                                data.extend(json.loads(serialize('json', model_class.objects.all())))
                        filename_prefix = "_".join(model_key.replace('.', '_') for model_key in selected_model_keys)
                    else:
                        call_command('dumpdata', '--exclude=contenttypes', '--exclude=auth.permission', '--exclude=admin.logentry', '--exclude=sessions.session', output=temp_file.name)
                        with open(temp_file.name, 'r') as f:
                            data = json.load(f)
                        filename_prefix = "full_data_backup"
                    if not data:
                        messages.warning(request,  ("داده‌ای برای بک‌آپ یافت نشد."))
                        return HttpResponseRedirect(redirect_url)
                    json_data = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
                    import io
                    encrypted_data, salt = self.encrypt_file(io.BytesIO(json_data), password)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"backup_{filename_prefix}_{timestamp}.enc"
                if save_to_server:
                    backup_dir = settings.DBBACKUP_STORAGE_OPTIONS.get('location', os.path.join(settings.MEDIA_ROOT, 'backups'))
                    os.makedirs(backup_dir, exist_ok=True)
                    with open(os.path.join(backup_dir, filename), 'wb') as f:
                        f.write(encrypted_data)
                    logger.info(f"Backup saved to {backup_dir}/{filename}")
                response = HttpResponse(content=encrypted_data, content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                messages.success(request,   ("بک‌آپ رمزگذاری‌شده با موفقیت ایجاد شد."))
                logger.info(f"Backup created: {filename} by {request.user.username}")
                return response
            except Exception as e:
                logger.error(f"Backup failed: {e}", exc_info=True)
                messages.error(request, f"خطا در بک‌آپ: {str(e)}")
                return HttpResponseRedirect(redirect_url)

        elif action == 'backup_db':
            try:
                backup_dir = settings.DBBACKUP_STORAGE_OPTIONS.get('location', os.path.join(settings.MEDIA_ROOT, 'backups'))
                os.makedirs(backup_dir, exist_ok=True)
                temp_file_path = os.path.join(backup_dir, f"temp_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
                final_file_path = None
                call_command('dbbackup', database='default', output_filename=temp_file_path, compress=True)
                logger.info(f"Temp file created: {temp_file_path}, exists: {os.path.exists(temp_file_path)}")
                if password:
                    with open(temp_file_path, 'rb') as f:
                        encrypted_data, salt = self.encrypt_file(f, password)
                    os.unlink(temp_file_path)
                    temp_file_enc_path = temp_file_path + '.enc'
                    with open(temp_file_enc_path, 'wb') as f:
                        f.write(encrypted_data)  # نوشتن داده‌های رمزنگاری‌شده
                    filename = f"backup_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.enc"
                    final_file_path = temp_file_enc_path
                else:
                    filename = f"backup_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql.gz"
                    final_file_path = temp_file_path
                if save_to_server:
                    final_backup_path = os.path.join(backup_dir, filename)
                    os.rename(final_file_path, final_backup_path)
                    logger.info(f"DB Backup saved to {final_backup_path}")
                response = FileResponse(open(final_file_path, 'rb'), as_attachment=True, filename=filename)
                messages.success(request,  ("بک‌آپ دیتابیس با موفقیت ایجاد شد."))
                logger.info(f"DB Backup created: {filename} by {request.user.username}")
                return response
            except Exception as e:
                logger.error(f"DB Backup failed: {e}", exc_info=True)
                messages.error(request, f"خطا در بک‌آپ دیتابیس: {str(e)}")
                return HttpResponseRedirect(redirect_url)
            finally:
                if 'final_file_path' in locals() and final_file_path and os.path.exists(final_file_path):
                    os.unlink(final_file_path)

        elif action == 'restore':
            if not backup_file:
                messages.error(request,  ("فایلی برای بازگردانی انتخاب نشده است."))
                return HttpResponseRedirect(redirect_url)
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.json' if backup_file.endswith('.enc') else '.sql') as temp_file:
                    if isinstance(backup_file, str):
                        with open(backup_file, 'rb') as f:
                            content = f.read()
                    else:
                        content = backup_file.read()
                    if backup_file.endswith('.enc'):
                        if not password:
                            messages.error(request, ("رمز برای بازگردانی فایل رمزگذاری‌شده لازم است."))
                            return HttpResponseRedirect(redirect_url)
                        decrypted_content = self.decrypt_file(content, password, salt=b'fixed_salt_16_bytes')
                        temp_file.write(decrypted_content)
                        call_command('loaddata', temp_file.name)
                    else:
                        temp_file.write(content)
                        call_command('dbrestore', input_path=temp_file.name)
                messages.success(request,  ("دیتابیس با موفقیت بازگردانی شد."))
                logger.info(f"Restore completed from {backup_file} by {request.user.username}")
                return HttpResponseRedirect(redirect_url)
            except Exception as e:
                logger.error(f"Restore failed: {e}", exc_info=True)
                messages.error(request, f"خطا در بازگردانی: {str(e)}")
                return HttpResponseRedirect(redirect_url)
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)

        elif action == 'reset':
            if not selected_model_keys:
                messages.error(request,  ("هیچ مدلی برای ریست انتخاب نشده است."))
                return HttpResponseRedirect(redirect_url)
            try:
                with transaction.atomic():
                    for model_key in selected_model_keys:
                        app_label, model_name = model_key.split('.')
                        model_class = apps.get_model(app_label, model_name)
                        count, _ = model_class.objects.all().delete()
                        logger.info(f"Deleted {count} records from {model_key} by {request.user.username}")
                messages.success(request, _(f"داده‌های مدل‌های انتخاب‌شده ({', '.join(selected_model_keys)}) با موفقیت ریست شدند."))
                return HttpResponseRedirect(redirect_url)
            except Exception as e:
                logger.error(f"Reset failed: {e}", exc_info=True)
                messages.error(request, f"خطا در ریست: {str(e)}")
                return HttpResponseRedirect(redirect_url)

        messages.warning(request,  ("عملیات نامشخص است."))
        return HttpResponseRedirect(redirect_url)


class DatabaseModelGraphView_x(SupervisorAndAdminRequiredMixin, View):
    template_name = 'accounts/DashboardDatabase/Dashboard_model_graph.html'

    def get_model_relations(self, model_class):
        from django.db.models import ForeignKey, ManyToManyField, OneToOneField
        relations = []
        for field in model_class._meta.get_fields():
            if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
                related_model_meta = field.related_model._meta
                relations.append({
                    'field_name': field.name,
                    'related_model_key': f"{related_model_meta.app_label}.{related_model_meta.model_name}",
                    'related_model_verbose_name': str(related_model_meta.verbose_name),
                    'type': field.__class__.__name__
                })
        return relations

    def get(self, request):
        excluded_apps = ['contenttypes', 'sessions', 'admin', 'auth', 'dbbackup']
        all_models_info = []

        for app_config in apps.get_app_configs():
            if app_config.label in excluded_apps:
                continue
            for model_class in app_config.get_models():
                model_meta = model_class._meta
                try:
                    record_count = model_class.objects.count()
                except Exception as e:
                    logger.warning(f"Could not count records for {model_class.__name__}: {e}")
                    record_count = 'N/A'
                all_models_info.append({
                    'app_label': app_config.label,
                    'model_name': model_meta.model_name,
                    'verbose_name': str(model_meta.verbose_name),
                    'key': f"{app_config.label}.{model_meta.model_name}",
                    'relations': self.get_model_relations(model_class),
                    'record_count': record_count
                })

        context = {
            'title': _('گراف روابط مدل‌های دیتابیس'),
            'models': sorted(all_models_info, key=lambda x: (x['app_label'], x['verbose_name'])),
            'app_labels': [app.label for app in apps.get_app_configs() if app.label not in excluded_apps]
        }
        logger.debug(f"Rendering model graph: models_count={len(all_models_info)}")
        return render(request, self.template_name, context)



class DatabaseModelGraphView(SupervisorAndAdminRequiredMixin, View):
    template_name = 'accounts/DashboardDatabase/Dashboard_model_graph.html'  # مسیر تمپلیت شما
    login_url = 'accounts:login'  # یا URL لاگین صحیح شما

    def _get_model_details_for_graph(self):
        """
        اطلاعات مدل‌ها و روابط آن‌ها را برای vis.js جمع‌آوری می‌کند.
        """
        excluded_apps = getattr(settings, 'DATABASE_GRAPH_EXCLUDED_APPS',
                                ['contenttypes', 'sessions', 'admin', 'auth', 'dbbackup',
                                 'django_celery_results', 'channels', 'rest_framework', 'notifications'])

        vis_nodes_list = []
        vis_edges_list = []
        vis_groups_dict = {}
        processed_app_labels_set = set()
        all_models_for_filter_list = []  # برای dropdown فیلتر مدل

        # پالت رنگی ساده برای اپ‌ها
        app_colors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796', '#6f42c1', '#fd7e14']
        color_idx = 0

        for app_config in apps.get_app_configs():
            app_label = app_config.label
            if app_label in excluded_apps:
                continue

            processed_app_labels_set.add(app_label)
            app_verbose_name = str(app_config.verbose_name)

            if app_label not in vis_groups_dict:
                group_color = app_colors[color_idx % len(app_colors)]
                color_idx += 1
                vis_groups_dict[app_label] = {
                    'color': {'background': group_color, 'border': '#303030'},
                    'font': {'color': '#ffffff', 'size': 13, 'face': 'Vazirmatn, Arial'},
                    'shapeProperties': {'borderRadius': 4}
                }

            for model_class in app_config.get_models():
                model_meta = model_class._meta
                model_key = f"{app_label}.{model_meta.model_name}"

                all_models_for_filter_list.append({
                    'key': model_key,
                    'name': f"{app_verbose_name} - {str(model_meta.verbose_name)}"
                })

                record_count_str = 'N/A'
                try:
                    record_count = model_class.objects.count()
                    record_count_str = str(record_count)
                except Exception:
                    pass

                # لینک ادمین
                admin_url = None
                try:
                    admin_url = reverse(f'admin:{app_label}_{model_meta.model_name}_changelist')
                except Exception:
                    pass

                vis_nodes_list.append({
                    'id': model_key,
                    'label': str(model_meta.verbose_name),
                    'title': (
                        f"<b>{str(model_meta.verbose_name)}</b> ({model_meta.model_name})\n<hr class='my-1'>"
                        f"اپلیکیشن: {app_verbose_name}\n"
                        f"تعداد رکوردها: {record_count_str}"
                        # می‌توانید فیلدهای کلیدی را هم اینجا اضافه کنید
                    ),
                    'group': app_label,
                    'value': 15 + (
                        int(record_count) if record_count_str.isdigit() and int(record_count) > 0 else 0) ** 0.2 * 5,
                    # اندازه نود بر اساس تعداد رکورد
                    'admin_url': admin_url
                })

                for field in model_class._meta.get_fields():
                    if field.is_relation and hasattr(field, 'related_model') and field.related_model and field.concrete:
                        if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
                            related_model_meta = field.related_model._meta
                            target_app = related_model_meta.app_label
                            target_model_key = f"{target_app}.{related_model_meta.model_name}"

                            if target_app not in excluded_apps:
                                edge_color = '#a0aec0'  # خاکستری پیش‌فرض
                                edge_width = 1.5
                                dashes = False
                                relation_type = field.__class__.__name__

                                if relation_type == 'ForeignKey':
                                    edge_color = '#e53e3e'; edge_width = 1.8  # قرمز
                                elif relation_type == 'ManyToManyField':
                                    edge_color = '#3182ce'; edge_width = 1.8; dashes = [4, 4]  # آبی
                                elif relation_type == 'OneToOneField':
                                    edge_color = '#38a169'; edge_width = 1.8; dashes = [2, 2]  # سبز

                                vis_edges_list.append({
                                    'from': model_key,
                                    'to': target_model_key,
                                    'label': field.name,
                                    'title': (
                                        f"<b>{field.name}</b> ({str(field.verbose_name)})\n<hr class='my-1'>"
                                        f"نوع: {relation_type}\n"
                                        f"به: {str(related_model_meta.verbose_name_plural)}"
                                    ),
                                    'arrows': {'to': {'enabled': True, 'scaleFactor': 0.7, 'type': 'arrow'}},
                                    'color': {'color': edge_color, 'highlight': '#f6ad55', 'hover': '#63b3ed',
                                              'opacity': 0.8},
                                    'width': edge_width,
                                    'dashes': dashes,
                                    'smooth': {'type': 'cubicBezier', 'roundness': 0.1}
                                })

        return {
            'vis_nodes_json': json.dumps(vis_nodes_list, ensure_ascii=False),
            'vis_edges_json': json.dumps(vis_edges_list, ensure_ascii=False),
            'vis_groups_json': json.dumps(vis_groups_dict, ensure_ascii=False),
            'app_labels_for_filter': sorted(list(processed_app_labels_set)),
            'all_models_for_filter': sorted(all_models_for_filter_list, key=lambda x: x['name'])
        }

    def get(self, request):
        context = {
            'title': _('گراف روابط مدل‌های دیتابیس'),
        }
        try:
            graph_data = self._get_model_details_for_graph()
            context.update(graph_data)
            logger.info(
                f"Successfully prepared graph data: {len(json.loads(graph_data['vis_nodes_json']))} nodes, {len(json.loads(graph_data['vis_edges_json']))} edges.")
        except Exception as e:
            logger.error(f"Error preparing graph data: {e}", exc_info=True)
            messages.error(request, _("خطا در آماده‌سازی داده‌های گراف. لطفاً لاگ‌ها را بررسی کنید."))
            # ارسال داده‌های خالی برای جلوگیری از خطای جاوااسکریپت
            context.update({
                'vis_nodes_json': '[]', 'vis_edges_json': '[]', 'vis_groups_json': '{}',
                'app_labels_for_filter': [], 'all_models_for_filter': []
            })

        return render(request, self.template_name, context)
