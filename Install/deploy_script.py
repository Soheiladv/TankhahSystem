import os
import shutil
import fnmatch
import py_compile

# تنظیمات مسیرها
PROJECT_DIR = os.path.abspath(".")  # مسیر پروژه
DEPLOY_DIR = os.path.join(PROJECT_DIR, "deploy")  # پوشه مقصد

# فایل‌ها و پوشه‌های مورد نیاز
INCLUDE_FILES = ["manage.py", "wsgi.py", "asgi.py", "requirements.txt", ".env"]
INCLUDE_DIRS = ["staticfiles", "templates"]

# فایل‌ها و پوشه‌های غیرضروری
EXCLUDE_DIRS = ["venv", ".venv", "__pycache__", ".git", ".idea", "node_modules", "migrations", "db_backup", ".pytest_cache", "logs", "Documents", "Install"]
EXCLUDE_FILES = ["*.py", "*.log", ".gitignore", "deploy_script.py", "*.sql", "*.txt", "*.docx", "*.rar", "*.pdf"]

def is_excluded(path, is_dir=False):
    base_name = os.path.basename(path)
    if is_dir:
        return base_name in EXCLUDE_DIRS
    for pattern in EXCLUDE_FILES:
        if fnmatch.fnmatch(base_name, pattern):
            return True
    return False

def compile_to_pyc(file_path):
    try:
        pyc_file = py_compile.compile(file_path, cfile=None)
        return pyc_file
    except Exception as e:
        print(f"خطا در کامپایل فایل {file_path}: {e}")
        return None

def create_deployment_package():
    if not os.path.isdir(PROJECT_DIR):
        print(f"خطا: پوشه پروژه '{PROJECT_DIR}' پیدا نشد.")
        return

    if os.path.exists(DEPLOY_DIR):
        print(f"[*] حذف پوشه قبلی '{DEPLOY_DIR}'...")
        shutil.rmtree(DEPLOY_DIR)

    print(f"[*] ایجاد پوشه جدید: '{DEPLOY_DIR}'")
    os.makedirs(DEPLOY_DIR)

    print(f"[*] شروع کپی کردن فایل‌های خروجی از '{PROJECT_DIR}'...")

    # تولید فایل‌های .pyc
    pyc_files = {}
    for file_name in INCLUDE_FILES:
        if file_name.endswith(".py"):
            src_file = os.path.join(PROJECT_DIR, file_name)
            if os.path.exists(src_file):
                pyc_file = compile_to_pyc(src_file)
                if pyc_file:
                    pyc_files[file_name] = pyc_file
                    print(f"تولید شد: {pyc_file}")

    # پیمایش پروژه
    for root, dirs, files in os.walk(PROJECT_DIR, topdown=True):
        dirs[:] = [d for d in dirs if not is_excluded(os.path.join(root, d), is_dir=True)]
        relative_path = os.path.relpath(root, PROJECT_DIR)
        dest_dir = os.path.join(DEPLOY_DIR, relative_path)
        copy_dir = False
        for inc_dir in INCLUDE_DIRS:
            if inc_dir in relative_path.split(os.sep):
                copy_dir = True
                break
        if copy_dir:
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

        for file_name in files:
            if file_name.endswith(".pyc"):
                src_file = os.path.join(root, file_name)
                dst_file = os.path.join(dest_dir, file_name)
                try:
                    shutil.copy2(src_file, dst_file)
                    print(f"کپی شد: {relative_path}/{file_name}")
                except Exception as e:
                    print(f"خطا در کپی فایل .pyc {relative_path}/{file_name}: {e}")
            elif (not is_excluded(src_file) and copy_dir) or (file_name in INCLUDE_FILES and root == PROJECT_DIR):
                src_file = os.path.join(root, file_name)
                dst_file = os.path.join(dest_dir, file_name)
                try:
                    shutil.copy2(src_file, dst_file)
                    print(f"کپی شد: {relative_path}/{file_name}")
                except Exception as e:
                    print(f"خطا در کپی فایل {relative_path}/{file_name}: {e}")

    print("\n" + "=" * 40)
    print("✅ بسته‌بندی خروجی پروژه با موفقیت انجام شد!")
    print(f"   فایل‌های خروجی در '{DEPLOY_DIR}' آماده اجرا هستند.")
    print("=" * 40)

if __name__ == "__main__":
    create_deployment_package()