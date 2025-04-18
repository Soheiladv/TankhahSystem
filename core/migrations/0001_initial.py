# Generated by Django 5.1.7 on 2025-04-19 10:38

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('budgets', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Dashboard_Core',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'permissions': [('Dashboard_Core_view', 'دسترسی به داشبورد Core پایه')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='DashboardView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'permissions': [('Dashboard__view', 'دسترسی به داشبورد اصلی 💻')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='DashboardView_flows',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'permissions': [('DashboardView_flows_view', 'دسترسی به روند تنخواه گردانی ')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='OrganizationType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fname', models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name='نام شعبه/مجتمع/اداره')),
                ('org_type', models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name='نام شعبه/مجتمع/اداره')),
                ('is_budget_allocatable', models.BooleanField(default=False, verbose_name='قابل استفاده برای تخصیص بودجه')),
            ],
            options={
                'verbose_name': 'عنوان مرکز/شعبه/اداره/سازمان',
                'verbose_name_plural': 'عنوان مرکز/شعبه/اداره/سازمان',
                'permissions': [('OrganizationType_add', 'افزودن شعبه/اداره/مجتمع/سازمان'), ('OrganizationType_view', 'نمایش شعبه/اداره/مجتمع/سازمان'), ('OrganizationType_update', 'ویرایش شعبه/اداره/مجتمع/سازمان'), ('OrganizationType_delete', 'حــذف شعبه/اداره/مجتمع/سازمان')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='WorkflowStage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='نام مرحله')),
                ('order', models.IntegerField(verbose_name='ترتیب')),
                ('description', models.TextField(blank=True, verbose_name='توضیحات')),
                ('is_active', models.BooleanField(default=True, verbose_name='وضعیت فعال')),
                ('is_final_stage', models.BooleanField(default=False, help_text='آیا این مرحله نهایی برای تکمیل تنخواه است؟', verbose_name='تعیین مرحله آخر')),
            ],
            options={
                'verbose_name': 'مرحله گردش کار',
                'verbose_name_plural': 'مراحل گردش کار',
                'ordering': ['order'],
                'permissions': [('WorkflowStage_view', 'نمایش مرحله گردش کار'), ('WorkflowStage_add', 'افزودن مرحله گردش کار'), ('WorkflowStage_update', 'بروزرسانی مرحله گردش کار'), ('WorkflowStage_delete', 'حــذف مرحله گردش کار')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10, unique=True, verbose_name='کد سازمان')),
                ('name', models.CharField(max_length=100, verbose_name='نام سازمان')),
                ('description', models.TextField(blank=True, null=True, verbose_name='توضیحات')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('is_core', models.BooleanField(default=False, verbose_name='دفتر مرکزی سازمان')),
                ('parent_organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.organization', verbose_name='سازمان والد')),
                ('org_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='organizations', to='core.organizationtype', verbose_name='نوع سازمان')),
            ],
            options={
                'verbose_name': 'سازمان',
                'verbose_name_plural': 'سازمان\u200cها',
                'permissions': [('Organization_add', 'افزودن سازمان برای تعریف مجتمع\u200cها و دفتر مرکزی'), ('Organization_update', 'بروزرسانی سازمان برای تعریف مجتمع\u200cها و دفتر مرکزی'), ('Organization_delete', 'حــذف سازمان برای تعریف مجتمع\u200cها و دفتر مرکزی'), ('Organization_view', 'نمایش سازمان برای تعریف مجتمع\u200cها و دفتر مرکزی')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='نام پست')),
                ('level', models.IntegerField(default=1, verbose_name='سطح')),
                ('branch', models.CharField(blank=True, choices=[('OPS', 'بهره\u200cبرداری'), ('FIN', 'مالی و اداری'), (None, 'بدون شاخه')], max_length=3, null=True, verbose_name='شاخه')),
                ('description', models.TextField(blank=True, null=True, verbose_name='توضیحات')),
                ('is_active', models.BooleanField(default=True, verbose_name='وضعیت فعال')),
                ('max_change_level', models.IntegerField(default=1, help_text='حداکثر مرحله\u200cای که این پست می\u200cتواند تغییر دهد', verbose_name='حداکثر سطح تغییر(ارجاع به مرحله قبل تر)')),
                ('is_payment_order_signer', models.BooleanField(default=False, verbose_name='مجاز به امضای دستور پرداخت')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.organization', verbose_name='سازمان')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.post', verbose_name='پست والد')),
            ],
            options={
                'verbose_name': 'پست سازمانی',
                'verbose_name_plural': 'پست\u200cهای سازمانی',
                'permissions': [('Post_add', 'افزودن  پست سازمانی برای تعریف سلسله مراتب'), ('Post_update', 'بروزرسانی پست سازمانی برای تعریف سلسله مراتب'), ('Post_view', 'نمایش  پست سازمانی برای تعریف سلسله مراتب'), ('Post_delete', 'حــذف  پست سازمانی برای تعریف سلسله مراتب')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='PostHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('changed_field', models.CharField(help_text='نام فیلدی که تغییر کرده (مثل name یا parent)', max_length=50, verbose_name='فیلد تغییر یافته')),
                ('old_value', models.TextField(blank=True, help_text='مقدار قبلی فیلد قبل از تغییر', null=True, verbose_name='مقدار قبلی')),
                ('new_value', models.TextField(blank=True, help_text='مقدار جدید فیلد بعد از تغییر', null=True, verbose_name='مقدار جدید')),
                ('changed_at', models.DateTimeField(auto_now_add=True, help_text='زمان ثبت تغییر به صورت خودکار', verbose_name='تاریخ و زمان تغییر')),
                ('changed_by', models.ForeignKey(help_text='کاربری که این تغییر را اعمال کرده', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='تغییر دهنده')),
                ('post', models.ForeignKey(help_text='پستی که تغییر کرده است', on_delete=django.db.models.deletion.CASCADE, to='core.post', verbose_name='پست سازمانی')),
            ],
            options={
                'verbose_name': 'تاریخچه پست',
                'verbose_name_plural': 'تاریخچه پست\u200cها',
                'ordering': ['-changed_at'],
                'permissions': [('posthistory_view', 'می\u200cتواند تاریخچه پست\u200cها را مشاهده کند'), ('posthistory_add', 'می\u200cتواند تاریخچه پست\u200cها را اضافه کند'), ('posthistory_update', 'می\u200cتواند تاریخچه پست\u200cها را ویرایش کند'), ('posthistory_delete', 'می\u200cتواند تاریخچه پست\u200cها را حذف کند')],
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='نام پروژه')),
                ('code', models.CharField(max_length=80, unique=True, verbose_name='کد پروژه')),
                ('start_date', models.DateField(verbose_name='تاریخ شروع')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='تاریخ پایان')),
                ('description', models.TextField(blank=True, null=True, verbose_name='توضیحات')),
                ('is_active', models.BooleanField(default=True, verbose_name='وضعیت فعال')),
                ('priority', models.CharField(choices=[('LOW', 'کم'), ('MEDIUM', 'متوسط'), ('HIGH', 'زیاد')], default='MEDIUM', max_length=20, verbose_name='اولویت')),
                ('organizations', models.ManyToManyField(limit_choices_to={'org_type__is_budget_allocatable': True}, to='core.organization', verbose_name='سازمان\u200cهای مرتبط')),
            ],
            options={
                'verbose_name': 'پروژه',
                'verbose_name_plural': 'پروژه',
                'permissions': [('Project_add', 'افزودن  مجموعه پروژه'), ('Project_update', 'ویرایش مجموعه پروژه'), ('Project_view', 'نمایش مجموعه پروژه'), ('Project_delete', 'حــذف مجموعه پروژه')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='SubProject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='نام ساب\u200cپروژه')),
                ('description', models.TextField(blank=True, null=True, verbose_name='توضیحات')),
                ('allocated_budget', models.DecimalField(decimal_places=2, default=0, max_digits=25, verbose_name='بودجه تخصیص\u200cیافته')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('allocations', models.ManyToManyField(blank=True, related_name='budget_allocations_set', to='budgets.projectbudgetallocation', verbose_name='تخصیص\u200cهای بودجه مرتبط')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subprojects', to='core.project', verbose_name='پروژه اصلی')),
            ],
            options={
                'verbose_name': 'ساب\u200cپروژه',
                'verbose_name_plural': 'ساب\u200cپروژه\u200cها',
                'permissions': [('SubProject_add', 'افزودن زیر مجموعه پروژه'), ('SubProject_update', 'ویرایش زیر مجموعه پروژه'), ('SubProject_view', 'نمایش زیر مجموعه پروژه'), ('SubProject_delete', 'حــذف زیر مجموعه پروژه'), ('SubProject_Head_Office', 'تخصیص زیر مجموعه پروژه(دفتر مرکزی)🏠'), ('SubProject_Branch', 'تخصیص  زیر مجموعه پروژه(شعبه)🏠')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='UserPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(default=django.utils.timezone.now, verbose_name='تاریخ شروع')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='تاریخ پایان')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.post', verbose_name='پست')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
            ],
            options={
                'verbose_name': 'اتصال کاربر به پست',
                'verbose_name_plural': 'اتصالات کاربر به پست\u200cها',
                'permissions': [('UserPost_add', 'افزودن  اتصال کاربر به پست'), ('UserPost_update', 'بروزرسانی  اتصال کاربر به پست'), ('UserPost_view', 'نمایش   اتصال کاربر به پست'), ('UserPost_delete', 'حــذف  اتصال کاربر به پست')],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='PostAction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(choices=[('APPROVE', 'تأیید'), ('REJECT', 'رد'), ('ISSUE_PAYMENT_ORDER', 'صدور دستور پرداخت'), ('FINALIZE', 'اتمام'), ('INSURANCE', 'ثبت بیمه'), ('CUSTOM', 'سفارشی')], max_length=50, verbose_name='نوع اقدام')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.post', verbose_name='پست')),
                ('stage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.workflowstage', verbose_name='مرحله')),
            ],
            options={
                'verbose_name': 'اقدام مجاز پست',
                'verbose_name_plural': 'اقدامات مجاز پست\u200cها',
                'permissions': [('PostAction_view', 'نمایش اقدامات مجاز پست'), ('PostAction_add', 'افزودن اقدامات مجاز پست'), ('PostAction_update', 'بروزرسانی اقدامات مجاز پست'), ('PostAction_delete', 'حذف اقدامات مجاز پست')],
            },
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['code', 'org_type'], name='core_organi_code_eadc65_idx'),
        ),
        migrations.AddIndex(
            model_name='posthistory',
            index=models.Index(fields=['post', 'changed_at'], name='core_posthi_post_id_2c35ae_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='userpost',
            unique_together={('user', 'post')},
        ),
        migrations.AlterUniqueTogether(
            name='postaction',
            unique_together={('post', 'stage', 'action_type')},
        ),
    ]
