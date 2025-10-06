import os
import shutil
import ctypes
import winreg


def secure_delete(file_path, passes=3, chunk_size=1024 * 1024):
    """
    فایل را به صورت امن با بازنویسی داده‌های تصادفی در قطعات (chunks) حذف می‌کند.
    این روش از مصرف بیش از حد حافظه برای فایل‌های بزرگ جلوگیری می‌کند.
    """
    try:
        long_path = f"\\\\?\\{os.path.abspath(file_path)}"
        if os.path.isfile(long_path):
            with open(long_path, "r+b") as f:  # استفاده از 'r+b' برای خواندن و نوشتن از ابتدای فایل
                length = os.path.getsize(long_path)
                for _ in range(passes):
                    f.seek(0)
                    for i in range(0, length, chunk_size):
                        chunk = os.urandom(min(chunk_size, length - i))
                        f.write(chunk)
            os.remove(long_path)
            print(f"Securely deleted: {file_path}")
    except Exception as e:
        print(f"Error securely deleting {file_path}: {e}")


def delete_directory(directory_path):
    """
    دایرکتوری و تمام محتویات آن را حذف می‌کند.
    'ignore_errors=True' حذف شد تا خطاها به درستی گزارش شوند.
    """
    try:
        long_path = f"\\\\?\\{os.path.abspath(directory_path)}"
        if os.path.exists(long_path):
            # حذف ignore_errors=True برای گزارش خطاهای شفاف‌تر
            shutil.rmtree(long_path)
            print(f"Deleted directory: {directory_path}")
    except Exception as e:
        print(f"Error deleting directory {directory_path}: {e}")


def delete_registry_key(root_key, key_path):
    """
    یک کلید رجیستری و تمام ساب‌کی‌های آن را به صورت بازگشتی و امن حذف می‌کند.
    """
    try:
        with winreg.OpenKey(root_key, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
            # ابتدا لیست تمام ساب‌کی‌ها را دریافت می‌کنیم
            subkeys = []
            i = 0
            while True:
                try:
                    subkeys.append(winreg.EnumKey(key, i))
                    i += 1
                except OSError:
                    break  # هیچ ساب‌کی دیگری وجود ندارد

            # سپس در یک حلقه جداگانه آنها را حذف می‌کنیم
            for subkey_name in subkeys:
                delete_registry_key(root_key, os.path.join(key_path, subkey_name))

            # پس از حذف تمام ساب‌کی‌ها، خود کلید را حذف می‌کنیم
            # (این بخش به دلیل باز شدن key در with، بعد از اتمام with اجرا می‌شود)
    except FileNotFoundError:
        pass  # کلید وجود ندارد، که مشکلی نیست
    except Exception as e:
        print(f"Error accessing/deleting subkeys in {key_path}: {e}")

    # در نهایت، کلید اصلی را حذف می‌کنیم
    try:
        winreg.DeleteKey(root_key, key_path)
        print(f"Deleted registry key: {key_path}")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error deleting registry key {key_path}: {e}")


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return False


def wipe_cursor_traces():
    # استفاده از os.path.join برای ساخت مسیرهای استاندارد
    cursor_paths = [
        os.path.join(os.environ.get("APPDATA", ""), "Cursor"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Cursor"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Cursor"),
        os.path.join(os.environ.get("TEMP", ""), "Cursor"),
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Cursor"),
        os.path.join(os.environ.get("USERPROFILE", ""), ".cursor"),
        os.path.join(os.environ.get("PROGRAMDATA", ""), "Cursor"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "CursorInstaller"),
    ]

    for path in cursor_paths:
        if not path: continue  # اگر متغیر محیطی وجود نداشت، رد شو

        if os.path.isdir(path):
            delete_directory(path)
        elif os.path.isfile(path):
            secure_delete(path)

    # حذف کلیدهای رجیستری
    registry_keys = [
        r"Software\Cursor",
        r"Software\Classes\Cursor",
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Cursor",
    ]

    for key_path in registry_keys:
        delete_registry_key(winreg.HKEY_CURRENT_USER, key_path)
        delete_registry_key(winreg.HKEY_LOCAL_MACHINE, key_path)


def main():
    if not is_admin():
        print("This script requires administrative privileges to run.")
        print("Please right-click and 'Run as administrator'.")
        input("Press Enter to exit.")  # منتظر می‌ماند تا کاربر پیام را ببیند
        return

    print("Wiping Cursor app traces...")
    wipe_cursor_traces()
    print("\nDone. All known traces of Cursor have been wiped.")
    input("Press Enter to exit.")


if __name__ == "__main__":
    main()


# import os
# import shutil
# import ctypes
# import winreg
#
#
# def secure_delete(file_path, passes=3):
#     try:
#         long_path = f"\\\\?\\{file_path}"
#         if os.path.isfile(long_path):
#             with open(long_path, 'ba+', buffering=0) as f:
#                 length = f.tell()
#                 for _ in range(passes):
#                     f.seek(0)
#                     f.write(os.urandom(length))
#             os.remove(long_path)
#             print(f"Securely deleted: {file_path}")
#     except Exception as e:
#         print(f"Error deleting {file_path}: {e}")
#
#
# def delete_directory(directory_path):
#     try:
#         long_path = f"\\\\?\\{directory_path}"
#         if os.path.exists(long_path):
#             shutil.rmtree(long_path, ignore_errors=True)
#             print(f"Deleted directory: {directory_path}")
#     except Exception as e:
#         print(f"Error deleting {directory_path}: {e}")
#
#
# def delete_registry_key(root, path):
#     try:
#         with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as key:
#             for i in range(0, winreg.QueryInfoKey(key)[0]):
#                 subkey = winreg.EnumKey(key, 0)
#                 delete_registry_key(root, f"{path}\\{subkey}")
#             winreg.DeleteKey(root, path)
#             print(f"Deleted registry key: {path}")
#     except FileNotFoundError:
#         pass
#     except Exception as e:
#         print(f"Error deleting registry key {path}: {e}")
#
#
# def is_admin():
#     try:
#         return ctypes.windll.shell32.IsUserAnAdmin()
#     except:
#         return False
#
#
# def wipe_cursor_traces():
#     cursor_paths = [
#         os.path.expandvars(r"%APPDATA%\Cursor"),
#         os.path.expandvars(r"%LOCALAPPDATA%\Cursor"),
#         os.path.expandvars(r"%LOCALAPPDATA%\Programs\Cursor"),
#         os.path.expandvars(r"%TEMP%\Cursor"),
#         os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Cursor"),
#         os.path.expandvars(r"%USERPROFILE%\.cursor"),  # hidden folder
#         os.path.expandvars(r"%PROGRAMDATA%\Cursor"),
#         os.path.expandvars(r"%LOCALAPPDATA%\CursorInstaller"),
#         os.path.expandvars(r"%APPDATA%\Roaming\Cursor"),
#         os.path.expandvars(r"%APPDATA%\CursorData"),
#     ]
#
#     for path in cursor_paths:
#         if os.path.isdir(path):
#             delete_directory(path)
#         elif os.path.isfile(path):
#             secure_delete(path)
#
#     # Remove possible registry keys
#     registry_keys = [
#         r"Software\Cursor",
#         r"Software\Classes\Cursor",
#         r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Cursor",
#     ]
#
#     for key_path in registry_keys:
#         delete_registry_key(winreg.HKEY_CURRENT_USER, key_path)
#         delete_registry_key(winreg.HKEY_LOCAL_MACHINE, key_path)
#
#
# def main():
#     if not is_admin():
#         print("This script requires administrative privileges to run.")
#         return
#
#     print("Wiping Cursor app traces...")
#     wipe_cursor_traces()
#     print("Done.")
#
#
# if __name__ == "__main__":
#     main()
#
