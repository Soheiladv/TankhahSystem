# Generated by Django 5.1.7 on 2025-03-27 21:50

import django.db.models.deletion
import django.utils.timezone
import tankhah.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Dashboard_Tankhah',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'permissions': [('Dashboard_Tankhah_view', 'دسترسی به داشبورد تنخواه گردان ')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='TanbakhFinalApproval',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'permissions': [('TanbakhFinalApproval_view', 'دسترسی تایید یا رد تنخواه گردان ')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='Factor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(blank=True, max_length=60, verbose_name='شماره فاکتور')),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='تاریخ')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='مبلغ')),
                ('description', models.TextField(verbose_name='توضیحات')),
                ('status', models.CharField(choices=[('PENDING', 'در حال بررسی'), ('APPROVED', 'تأییدشده'), ('REJECTED', 'ردشده')], default='PENDING', max_length=20, verbose_name='وضعیت')),
                ('is_finalized', models.BooleanField(default=False, verbose_name='نهایی شده')),
                ('locked', models.BooleanField(default=False, verbose_name='قفل شده')),
                ('approved_by', models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, verbose_name='تأییدکنندگان')),
            ],
            options={
                'verbose_name': 'فاکتور',
                'verbose_name_plural': 'فاکتورها',
                'permissions': [('a_factor_add', 'افزودن فاکتور برای جزئیات تنخواه '), ('a_factor_update', 'ویرایش فاکتور برای جزئیات تنخواه'), ('a_factor_delete', 'حــذف فاکتور برای جزئیات تنخواه'), ('a_factor_view', 'نمایش فاکتور برای جزئیات تنخواه')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='FactorDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='factors/documents/%Y/%m/%d/', verbose_name='فایل پیوست')),
                ('file_size', models.IntegerField(blank=True, null=True, verbose_name='حجم فایل (بایت)')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ بارگذاری')),
                ('factor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='tankhah.factor', verbose_name='فاکتور')),
            ],
            options={
                'verbose_name': 'سند فاکتور',
                'verbose_name_plural': 'اسناد فاکتور',
                'permissions': [('FactorDocument_add', 'افزودن سند فاکتور'), ('FactorDocument_update', 'بروزرسانی سند فاکتور'), ('FactorDocument_view', 'نمایش سند فاکتور'), ('FactorDocument_delete', 'حــذف سند فاکتور')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='FactorItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=255, verbose_name='شرح ردیف')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='مبلغ')),
                ('status', models.CharField(choices=[('PENDING', 'در حال بررسی'), ('APPROVED', 'تأیید شده'), ('REJECTED', 'رد شده')], default='PENDING', max_length=20, verbose_name='وضعیت')),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=25, verbose_name='تعداد')),
                ('unit_price', models.DecimalField(decimal_places=1, default=1, max_digits=25, verbose_name='قیمت واحد')),
                ('factor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='tankhah.factor', verbose_name='فاکتور')),
            ],
            options={
                'verbose_name': 'ردیف فاکتور',
                'verbose_name_plural': 'ردیف\u200cهای فاکتور',
                'permissions': [('FactorItem_add', 'افزودن اقلام فاکتور'), ('FactorItem_update', 'ویرایش اقلام فاکتور'), ('FactorItem_view', 'نمایش اقلام فاکتور'), ('FactorItem_delete', 'حذف اقلام فاکتور')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='StageApprover',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True, verbose_name='وضعیت فعال')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.post', verbose_name='پست مجاز')),
                ('stage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.workflowstage', verbose_name='مرحله')),
            ],
            options={
                'verbose_name': 'تأییدکننده مرحله',
                'verbose_name_plural': 'تأییدکنندگان مرحله',
                'permissions': [('stageapprover__view', 'نمایش تأییدکننده مرحله'), ('stageapprover__add', 'افزودن تأییدکننده مرحله'), ('stageapprover__Update', 'بروزرسانی تأییدکننده مرحله'), ('stageapprover__delete', 'حــذف تأییدکننده مرحله')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='Tankhah',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(blank=True, max_length=50, unique=True, verbose_name='شماره تنخواه')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=25, verbose_name='مبلغ')),
                ('date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='تاریخ')),
                ('due_date', models.DateTimeField(blank=True, null=True, verbose_name='مهلت زمانی')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')),
                ('letter_number', models.CharField(blank=True, max_length=50, null=True, verbose_name='شماره نامه')),
                ('description', models.TextField(verbose_name='توضیحات')),
                ('status', models.CharField(choices=[('DRAFT', 'پیش\u200cنویس'), ('PENDING', 'در حال بررسی'), ('APPROVED', 'تأییدشده'), ('SENT_TO_HQ', 'ارسال\u200cشده به HQ'), ('HQ_OPS_PENDING', 'در حال بررسی - بهره\u200cبرداری'), ('HQ_OPS_APPROVED', 'تأییدشده - بهره\u200cبرداری'), ('HQ_FIN_PENDING', 'در حال بررسی - مالی'), ('PAID', 'پرداخت\u200cشده'), ('REJECTED', 'ردشده')], default='DRAFT', max_length=20, verbose_name='وضعیت')),
                ('hq_status', models.CharField(blank=True, choices=[('DRAFT', 'پیش\u200cنویس'), ('PENDING', 'در حال بررسی'), ('APPROVED', 'تأییدشده'), ('SENT_TO_HQ', 'ارسال\u200cشده به HQ'), ('HQ_OPS_PENDING', 'در حال بررسی - بهره\u200cبرداری'), ('HQ_OPS_APPROVED', 'تأییدشده - بهره\u200cبرداری'), ('HQ_FIN_PENDING', 'در حال بررسی - مالی'), ('PAID', 'پرداخت\u200cشده'), ('REJECTED', 'ردشده')], default='PENDING', max_length=20, null=True, verbose_name='وضعیت در HQ')),
                ('is_archived', models.BooleanField(default=False, verbose_name='آرشیو شده')),
                ('archived_at', models.DateTimeField(blank=True, null=True, verbose_name='زمان آرشیو')),
                ('canceled', models.BooleanField(default=False, verbose_name='لغو شده')),
                ('approved_by', models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, verbose_name='تأییدکنندگان')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tanbakh_created', to=settings.AUTH_USER_MODEL, verbose_name='ایجادکننده')),
                ('current_stage', models.ForeignKey(default=tankhah.models.get_default_workflow_stage, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.workflowstage', verbose_name='مرحله فعلی')),
                ('last_stopped_post', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.post', verbose_name='آخرین پست متوقف\u200cشده')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.organization', verbose_name='مجموعه/شعبه')),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.project', verbose_name='پروژه')),
            ],
            options={
                'verbose_name': 'تنخواه',
                'verbose_name_plural': 'تنخواه\u200cها',
                'permissions': [('Tanbakh_add', 'ثبت تنخواه'), ('Tanbakh_update', 'بروزرسانی تنخواه'), ('Tanbakh_view', 'نمایش تنخواه'), ('Tanbakh_delete', 'حذف تنخواه'), ('Tanbakh_part_approve', '👍تأیید رئیس قسمت'), ('Tanbakh_approve', '👍تأیید مدیر مجموعه'), ('Tanbakh_hq_view', 'رصد دفتر مرکزی'), ('Tanbakh_hq_approve', '👍تأیید رده بالا در دفتر مرکزی'), ('Tanbakh_HQ_OPS_PENDING', 'در حال بررسی - بهره\u200cبرداری'), ('Tanbakh_HQ_OPS_APPROVED', '👍تأییدشده - بهره\u200cبرداری'), ('Tanbakh_HQ_FIN_PENDING', 'در حال بررسی - مالی'), ('Tanbakh_PAID', 'پرداخت\u200cشده'), ('Tanbakh_REJECTED', 'ردشده'), ('FactorItem_approve', '👍تایید/رد ردیف فاکتور دفتر مرکزی '), ('edit_full_tanbakh', '👍😊تغییرات کاربری در فاکتور /تایید یا رد ردیف ها '), ('Dashboard_Core_view', 'دسترسی به داشبورد Core پایه'), ('DashboardView_flows_view', 'دسترسی به روند تنخواه گردانی'), ('Dashboard__view', 'دسترسی به داشبورد اصلی 💻')],
                'default_permissions': (),
            },
        ),
        migrations.AddField(
            model_name='factor',
            name='tankhah',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='factors', to='tankhah.tankhah', verbose_name='تنخواه'),
        ),
        migrations.CreateModel(
            name='ApprovalLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('APPROVE', 'تأیید'), ('REJECT', 'رد'), ('RETURN', 'بازگشت'), ('CANCEL', 'لغو')], max_length=10, verbose_name='اقدام')),
                ('comment', models.TextField(blank=True, null=True, verbose_name='توضیحات')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='زمان')),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')),
                ('changed_field', models.CharField(blank=True, max_length=50, null=True, verbose_name='فیلد تغییر یافته')),
                ('post', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.post', verbose_name='پست تأییدکننده')),
                ('stage', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.workflowstage', verbose_name='مرحله')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
                ('factor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='approval_logs', to='tankhah.factor', verbose_name='فاکتور')),
                ('factor_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='approval_logs', to='tankhah.factoritem', verbose_name='ردیف فاکتور')),
                ('tankhah', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='approval_logs', to='tankhah.tankhah', verbose_name='تنخواه')),
            ],
            options={
                'verbose_name': 'تأیید',
                'verbose_name_plural': 'تأییدات👍',
                'permissions': [('Approval_add', 'افزودن تأیید برای ثبت اقدامات تأیید یا رد '), ('Approval_update', 'ویرایش تأیید برای ثبت اقدامات تأیید یا رد'), ('Approval_delete', 'حــذف تأیید برای ثبت اقدامات تأیید یا رد'), ('Approval_view', 'نمایش تأیید برای ثبت اقدامات تأیید یا رد')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='TankhahDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document', models.FileField(upload_to=tankhah.models.tanbakh_document_path, verbose_name='سند')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ آپلود')),
                ('file_size', models.IntegerField(blank=True, null=True, verbose_name='حجم فایل (بایت)')),
                ('tankhah', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='tankhah.tankhah', verbose_name='تنخواه')),
            ],
        ),
        migrations.AddIndex(
            model_name='tankhah',
            index=models.Index(fields=['number', 'date', 'status'], name='tankhah_tan_number_b77feb_idx'),
        ),
        migrations.AddIndex(
            model_name='factor',
            index=models.Index(fields=['number', 'date', 'status'], name='tankhah_fac_number_f3bf46_idx'),
        ),
    ]
