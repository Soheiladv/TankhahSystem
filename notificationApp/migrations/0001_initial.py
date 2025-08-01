# Generated by Django 5.1.7 on 2025-07-26 18:37

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entity_type', models.CharField(choices=[('FACTOR', 'فاکتور'), ('TANKHAH', 'تنخواه'), ('PAYMENTORDER', 'دستور پرداخت')], max_length=50, verbose_name='نوع موجودیت')),
                ('action', models.CharField(choices=[('CREATED', 'ایجاد'), ('APPROVED', 'تأیید'), ('REJECTED', 'رد'), ('PAID', 'پرداخت')], max_length=50, verbose_name='اقدام')),
                ('priority', models.CharField(choices=[('LOW', 'کم'), ('MEDIUM', 'متوسط'), ('HIGH', 'زیاد')], default='MEDIUM', max_length=20, verbose_name='اولویت')),
                ('channel', models.CharField(choices=[('IN_APP', 'درون\u200cبرنامه'), ('EMAIL', 'ایمیل'), ('SMS', 'پیامک')], default='IN_APP', max_length=50, verbose_name='کانال')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('recipients', models.ManyToManyField(to='core.post', verbose_name='گیرندگان')),
            ],
            options={
                'verbose_name': 'قانون اعلان',
                'verbose_name_plural': 'قوانین اعلان',
                'permissions': [('NotificationRule_add', 'افزودن اعلان'), ('NotificationRule_update', 'بروزرسانی اعلان'), ('NotificationRule_view', 'نمایش اعلان'), ('NotificationRule_delete', 'حذف اعلان')],
                'default_permissions': (),
            },
        ),
    ]
