import os
import shutil
import subprocess # برای اجرای دستورات سیستمی (مثل manage.py)

def clean_migrations():
    """
    این تابع تمام فایل‌های .py و .pyc مربوط به مایگریشن‌ها را
    به جز فایل __init__.py، در تمام پوشه‌های migrations پروژه‌ی جنگو حذف می‌کند.
    به طور صریح از ورود به پوشه‌ی venv جلوگیری می‌کند.
    """
    current_directory = os.getcwd() # مسیر فعلی که اسکریپت از آن اجرا می‌شود

    print("--Start Delete migrations File >> - شروع پاکسازی فایل‌های مایگریشن ---")
    print("در حال جستجو برای پوشه‌های 'migrations'..ّFind migrations Files.")

    # پیمایش تمام پوشه‌ها و زیرپوشه‌ها
    for root, dirs, files in os.walk(current_directory):
        # نادیده گرفتن پوشه venv
        if 'venv' in dirs:
            dirs.remove('venv') # این خط باعث می‌شود os.walk وارد پوشه venv نشود

        if 'migrations' in dirs:
            migrations_path = os.path.join(root, 'migrations')
            print(f"پوشه‌ی مایگریشن پیدا شد: Find migrations Folder{migrations_path}")

            for item in os.listdir(migrations_path):
                item_path = os.path.join(migrations_path, item)

                if os.path.isfile(item_path):
                    if item != '__init__.py' and (item.endswith('.py') or item.endswith('.pyc')):
                        try:
                            os.remove(item_path)
                            print(f"  فایل حذف شد: Delete migrations File{item}")
                        except OSError as e:
                            print(f"  خطا در حذف فایل Error Delete migrations file{item}: {e}")
                elif os.path.isdir(item_path) and item == '__pycache__':
                    # حذف پوشه‌ی __pycache__ داخل migrations
                    try:
                        shutil.rmtree(item_path)
                        print(f"  پوشه‌ی {item} حذف شد: {item_path}")
                    except OSError as e:
                        print(f"  خطا در حذف پوشه‌ی   خطا در حذف فایل Error Delete migrations Folder><{item_path}: {e}")

    print("--- پاکسازی مایگریشن‌ها به پایان رسید End Delete   خطا در حذف فایل Error Delete migrations files---")

def run_django_migrations_commands():
    """
    این تابع دستورات makemigrations و migrate جنگو را اجرا می‌کند.
    """
    print("\n--- شروع اجرای دستورات مایگریشن جنگو ---")

    # اجرای makemigrations
    print("\nدر حال اجرای: python manage.py makemigrations")
    try:
        # capture_output=True برای گرفتن خروجی دستور و text=True برای نمایش متن
        result = subprocess.run(['py', '.\manage.py', 'makemigrations'], capture_output=True, text=True, check=True)
        print(result.stdout)
        if result.stderr:
            print("خطاهای makemigrations:")
            print(result.stderr)
        print("makemigrations با موفقیت اجرا شد.")
    except subprocess.CalledProcessError as e:
        print(f"خطا در اجرای makemigrations: {e}")
        print(e.stdout)
        print(e.stderr)
        return # اگر makemigrations خطا داد، ادامه نده

    # اجرای migrate
    print("\nدر حال اجرای: py .\manage.py migrate")
    try:
        result = subprocess.run(['py', '.\manage.py', 'migrate'], capture_output=True, text=True, check=True)
        print(result.stdout)
        if result.stderr:
            print("خطاهای migrate:")
            print(result.stderr)
        print("migrate با موفقیت اجرا شد.")
    except subprocess.CalledProcessError as e:
        print(f"خطا در اجرای migrate: {e}")
        print(e.stdout)
        print(e.stderr)

    print("\n--- اجرای دستورات مایگریشن جنگو به پایان رسید ---")


if __name__ == "__main__":
    clean_migrations()

    print("\n--- مرحله بعدی: ساخت و اعمال مایگریشن‌های جدید ---")
    print("توجه: اگر می‌خواهید دیتابیس کاملاً از نو ساخته شود،")
    print("فایل دیتابیس خود (مثلاً db.sqlite3) را قبل از ادامه حذف کنید.")
    # print("آیا مایلید دستورات 'makemigrations' و 'migrate' جنگو اجرا شوند؟ (Y/N)")
    print("How To run Migration ? (Y/N)")

    user_input = input().strip().lower()

    if user_input == 'y' or user_input == 'Y':
        run_django_migrations_commands()
    else:
        print("اجرای دستورات مایگریشن لغو شد.")
        print("می‌توانید به صورت دستی 'python manage.py makemigrations' و 'python manage.py migrate' را اجرا کنید.")

    print("\nعملیات اسکریپت به پایان رسید.")