import os

##!/bin/bash
#
## تنظیمات اتصال
#DB_NAME="tanbakh_db"
#DB_USER="root"
#DB_PASSWORD="S@123456@1234"
#
## ساخت دیتابیس اگر وجود ندارد
#mysql -u $DB_USER -p$DB_PASSWORD -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
#
## اعمال مایگریشن‌ها
#python manage.py makemigrations
#python manage.py migrate

# ایجاد سوپر یوزر اولیه اگر وجود ندارد
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')" | python manage.py shell

# کد Bash برای اجرای یک‌باره تمام مراحل از ساخت دیتابیس تا ایجاد سوپر یوزر
bash_script = """
# تنظیم متغیرهای اتصال به MySQL
MYSQL_USER="root"
MYSQL_PASSWORD="S@123456@1234"
DB_NAME="tankhasystem"

# بررسی اینکه دیتابیس وجود دارد یا نه
RESULT=`mysql -u$MYSQL_USER -p$MYSQL_PASSWORD -e "SHOW DATABASES LIKE '$DB_NAME'"`
if [ "$RESULT" == "" ]; then
    echo "Creating database $DB_NAME..."
    mysql -u$MYSQL_USER -p$MYSQL_PASSWORD -e "CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
else
    echo "Database $DB_NAME already exists."
fi

# مهاجرت و ساخت یوزر اولیه
echo "Running Django migrations..."
python manage.py makemigrations
python manage.py migrate

# ساخت سوپر یوزر فقط در صورت نبود یوزر
echo "Creating superuser if not exists..."
echo "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(username='admin', email='admin@example.com', password='admin')
" | python manage.py shell
"""

bash_script_path = "init_django_setup.sh"

# ذخیره فایل اسکریپت
with open(bash_script_path, "w") as f:
    f.write(bash_script)

bash_script_path
