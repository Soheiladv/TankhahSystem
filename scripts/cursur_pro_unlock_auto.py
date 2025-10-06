#!/usr/bin/env python3
import os
import json
import uuid
import logging
import psutil
import time
import platform
import subprocess
import sys
import stat
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.safari.options import Options as SafariOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import arabic_reshaper
from bidi.algorithm import get_display

# تنظیمات کنسول Rich برای رابط کاربری جذاب
console = Console()

# تنظیم لاگ‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# مسیر فایل تنظیمات
CONFIG_PATH = os.path.expanduser("~/cursor_pro_config.json")

# تنظیمات پیش‌فرض
DEFAULT_CONFIG = {
    "cursor_path": "",
    "browser": "chrome",
    "token_limit": 1000000,
    "cursor_version": "0.49.2"
}

# مسیرهای پیش‌فرض Cursor برای پلتفرم‌های مختلف
CURSOR_PATHS = {
    "Darwin": "~/Library/Application Support/Cursor",
    "Linux": "~/.config/cursor",
    "Windows": os.path.join(os.getenv("APPDATA", ""), "Cursor")
}

# پکیج‌های موردنیاز
REQUIRED_PACKAGES = [
    "rich",
    "selenium",
    "webdriver-manager",
    "psutil",
    "arabic-reshaper",
    "python-bidi"
]

# آدرس لاگین Cursor
LOGIN_URL = (
    "https://authenticator.cursor.sh/?client_id=client_01GS6W3C96KW4WRS6Z93JCE2RJ"
    "&redirect_uri=https%3A%2F%2Fcursor.com%2Fapi%2Fauth%2Fcallback"
    "&response_type=code"
    "&state=%257B%2522returnTo%2522%253A%2522%252Fsettings%2522%257D"
    "&authorization_session_id=01JTZKNFR5TRMTDGS621R3F1BQ"
)


def reshape_text(text):
    """اصلاح نمایش متن فارسی با arabic_reshaper و bidi"""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)


def print_panel(message, style="bold green", title=None):
    """نمایش پنل با متن فارسی اصلاح‌شده"""
    reshaped_message = reshape_text(message)
    panel = Panel(
        Text(reshaped_message, style="white", justify="right"),
        style=style,
        title=reshape_text(title) if title else None,
        border_style="bold cyan"
    )
    console.print(panel)


def install_packages():
    """نصب خودکار پکیج‌های موردنیاز"""
    with Progress(
            SpinnerColumn(spinner_name="aesthetic"),
            TextColumn("[progress.description]{task.description}"),
            transient=True
    ) as progress:
        task = progress.add_task(reshape_text("[cyan]بررسی و نصب پکیج‌ها..."), total=len(REQUIRED_PACKAGES))
        for pkg in REQUIRED_PACKAGES:
            try:
                __import__(pkg.replace("-", "_"))
                progress.update(task, advance=1, description=reshape_text(f"[green]پکیج {pkg} موجود است"))
            except ImportError:
                progress.update(task, description=reshape_text(f"[yellow]نصب پکیج {pkg}..."))
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                    progress.update(task, advance=1, description=reshape_text(f"[green]پکیج {pkg} نصب شد"))
                except subprocess.CalledProcessError as e:
                    print_panel(f"🚨 خطا در نصب پکیج {pkg}: {e}", style="bold red", title="خطای نصب")
                    exit(1)


def check_and_set_permissions(file_path):
    """بررسی و تنظیم خودکار مجوزهای فایل"""
    file_path = os.path.expanduser(file_path)
    if not os.path.exists(file_path):
        return
    try:
        # بررسی دسترسی نوشتن
        if not os.access(file_path, os.W_OK):
            if platform.system() in ["Linux", "Darwin"]:
                subprocess.check_call(["sudo", "chmod", "u+rw", file_path])
            elif platform.system() == "Windows":
                subprocess.check_call(["icacls", file_path, "/grant", f"{os.getlogin()}:F"])
        logger.debug(f"مجوزهای {file_path} تنظیم شدند")
    except subprocess.CalledProcessError as e:
        print_panel(
            f"🚨 خطا در تنظیم مجوزهای {file_path}: {e}\nلطفاً اسکریپت را با sudo (Linux/macOS) یا Administrator (Windows) اجرا کنید.",
            style="bold red",
            title="خطای مجوز"
        )
        exit(1)


def load_config():
    """بارگذاری یا ایجاد فایل تنظیمات"""
    system = platform.system()
    default_config = DEFAULT_CONFIG.copy()
    default_config["cursor_path"] = CURSOR_PATHS.get(system, "")

    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'w') as f:
            json.dump(default_config, f, indent=4)
        print_panel(
            f"📝 فایل تنظیمات در {CONFIG_PATH} ایجاد شد. لطفاً مسیرها و نسخه را بررسی کنید.",
            style="bold yellow",
            title="ایجاد تنظیمات"
        )
        exit(1)
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def check_cursor_process():
    """بررسی و بستن فرآیندهای Cursor"""
    with Progress(
            SpinnerColumn(spinner_name="aesthetic"),
            TextColumn("[progress.description]{task.description}"),
            transient=True
    ) as progress:
        task = progress.add_task(reshape_text("[cyan]بررسی فرآیندهای Cursor..."), total=None)
        cursor_found = False
        for proc in psutil.process_iter(['name']):
            if 'Cursor' in proc.info['name']:
                cursor_found = True
                proc.terminate()
                progress.update(task, description=reshape_text("[yellow]بستن فرآیند Cursor..."))
                time.sleep(1)
        progress.update(task, description=reshape_text(
            "[green]فرآیندها بررسی شدند!" if cursor_found else "[green]هیچ فرآیندی یافت نشد!"))


def reset_machine_id(cursor_path):
    """بازنشانی Machine ID"""
    machine_id_path = os.path.join(os.path.expanduser(cursor_path), "machineId")
    check_and_set_permissions(machine_id_path)
    with Progress(
            SpinnerColumn(spinner_name="aesthetic"),
            TextColumn("[progress.description]{task.description}"),
            transient=True
    ) as progress:
        task = progress.add_task(reshape_text("[cyan]بازنشانی Machine ID..."), total=None)
        try:
            new_id = str(uuid.uuid4())
            with open(machine_id_path, 'w') as f:
                f.write(new_id)
            progress.update(task, description=reshape_text(f"[green]Machine ID به {new_id} بازنشانی شد!"))
        except Exception as e:
            print_panel(f"🚨 خطا در بازنشانی Machine ID: {e}", style="bold red", title="خطا")
            exit(1)


def modify_product_json(cursor_path, token_limit):
    """تغییر product.json برای افزایش محدودیت توکن و فعال‌سازی مدل‌های پرمیوم"""
    product_json_path = os.path.join(os.path.expanduser(cursor_path), "product.json")
    check_and_set_permissions(product_json_path)
    with Progress(
            SpinnerColumn(spinner_name="aesthetic"),
            TextColumn("[progress.description]{task.description}"),
            transient=True
    ) as progress:
        task = progress.add_task(reshape_text("[cyan]به‌روزرسانی product.json..."), total=None)
        try:
            if os.path.exists(product_json_path):
                with open(product_json_path, 'r') as f:
                    data = json.load(f)
                data['tokenLimit'] = token_limit
                data['premiumModels'] = ["gpt-4o-mini", "gpt-4", "claude-3.5-sonnet"]
                with open(product_json_path, 'w') as f:
                    json.dump(data, f, indent=4)
                progress.update(task, description=reshape_text(
                    f"[green]محدودیت توکن به {token_limit} و مدل‌های پرمیوم فعال شدند!"))
            else:
                progress.update(task, description=reshape_text("[yellow]product.json یافت نشد. این مرحله رد شد."))
        except Exception as e:
            print_panel(f"🚨 خطا در تغییر product.json: {e}", style="bold red", title="خطا")
            exit(1)


def patch_workbench(cursor_path, cursor_version):
    """پچ کردن workbench.desktop.main.js برای غیرفعال کردن بررسی نسخه"""
    workbench_path = os.path.join(
        os.path.expanduser(cursor_path),
        f"app-{cursor_version}/resources/app/out/vs/code/electron-browser/workbench/workbench.desktop.main.js"
    )
    check_and_set_permissions(workbench_path)
    with Progress(
            SpinnerColumn(spinner_name="aesthetic"),
            TextColumn("[progress.description]{task.description}"),
            transient=True
    ) as progress:
        task = progress.add_task(reshape_text("[cyan]پچ کردن workbench.desktop.main.js..."), total=None)
        try:
            if os.path.exists(workbench_path):
                with open(workbench_path, 'r') as f:
                    content = f.read()
                patched_content = content.replace('checkForUpdates', '/*checkForUpdates*/').replace(
                    'restrictPremiumModels', '/*restrictPremiumModels*/'
                )
                with open(workbench_path, 'w') as f:
                    f.write(patched_content)
                progress.update(task, description=reshape_text("[green]بررسی نسخه و محدودیت‌ها غیرفعال شدند!"))
            else:
                progress.update(task, description=reshape_text(
                    "[yellow]workbench.desktop.main.js یافت نشد. این مرحله رد شد."))
        except Exception as e:
            print_panel(f"🚨 خطا در پچ کردن workbench: {e}", style="bold red", title="خطا")
            exit(1)


def select_browser():
    """نمایش منوی انتخاب مرورگر"""
    system = platform.system()
    browsers = {
        "1": ("chrome", "Google Chrome"),
        "2": ("firefox", "Firefox"),
        "3": ("edge", "Microsoft Edge")
    }
    if system == "Darwin":
        browsers["4"] = ("safari", "Safari")

    table = Table(title=reshape_text("انتخاب مرورگر"), title_style="bold magenta")
    table.add_column(reshape_text("شماره"), style="cyan", justify="center")
    table.add_column(reshape_text("مرورگر"), style="green", justify="right")

    for key, (_, name) in browsers.items():
        table.add_row(key, reshape_text(name))

    console.print(Panel(table, border_style="bold cyan", title=reshape_text("منوی مرورگر")))
    choice = Prompt.ask(
        reshape_text("شماره مرورگر را وارد کنید"),
        choices=list(browsers.keys()),
        default="1"
    )
    return browsers[choice][0]


def open_login_page(browser_type):
    """باز کردن صفحه ورود Cursor در حالت غیرناشناس"""
    with Progress(
            SpinnerColumn(spinner_name="aesthetic"),
            TextColumn("[progress.description]{task.description}"),
            transient=True
    ) as progress:
        task = progress.add_task(reshape_text("[cyan]باز کردن صفحه ورود..."), total=None)
        try:
            driver = None
            if browser_type == "chrome":
                options = webdriver.ChromeOptions()
                options.add_argument("--no-sandbox")
                driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
            elif browser_type == "firefox":
                driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()))
            elif browser_type == "edge":
                driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()))
            elif browser_type == "safari":
                if platform.system() != "Darwin":
                    raise ValueError("Safari تنها در macOS پشتیبانی می‌شود.")
                driver = webdriver.Safari(options=SafariOptions())
            else:
                raise ValueError("مرورگر پشتیبانی‌نشده.")

            driver.get(LOGIN_URL)
            progress.update(task, description=reshape_text("[green]صفحه ورود باز شد!"))
            print_panel(
                "🌟 لطفاً با حساب گوگل یا گیت‌هاب وارد شوید. پس از ورود، Enter را در ترمینال فشار دهید.",
                style="bold blue",
                title="ورود"
            )
            input()
            driver.quit()
        except Exception as e:
            print_panel(f"🚨 خطا در باز کردن مرورگر: {e}", style="bold red", title="خطا")
            exit(1)


def welcome_animation():
    """انیمیشن خوش‌آمدگویی"""
    console.print("\n")
    with Progress(
            SpinnerColumn(spinner_name="aesthetic"),
            TextColumn("[progress.description]{task.description}"),
            transient=True
    ) as progress:
        task = progress.add_task(reshape_text("[cyan]آماده‌سازی محیط..."), total=10)
        for _ in range(10):
            progress.update(task, advance=1)
            time.sleep(0.1)
    console.print(reshape_text("[bold magenta]🚀 Cursor Pro Unlocker - نسخه کامل با تمام امکانات! 🚀[/]\n"))


def main():
    """تابع اصلی"""
    welcome_animation()
    print_panel(
        "🔥 فعال‌سازی نسخه Pro با مدل‌های هوش مصنوعی (GPT-4o-mini، GPT-4، Claude-3.5-Sonnet) و توکن نامحدود!",
        style="bold magenta",
        title="خوش‌آمدید"
    )

    # نصب پکیج‌ها
    install_packages()

    # بارگذاری تنظیمات
    config = load_config()
    cursor_path = config["cursor_path"]
    token_limit = config["token_limit"]
    cursor_version = config["cursor_version"]

    # بررسی مسیر Cursor
    if not os.path.exists(os.path.expanduser(cursor_path)):
        print_panel(
            f"🚨 مسیر Cursor ({cursor_path}) یافت نشد. لطفاً cursor_pro_config.json را بررسی کنید.",
            style="bold red",
            title="خطا"
        )
        exit(1)

    # انتخاب مرورگر
    browser_type = select_browser()

    # مراحل اجرا
    check_cursor_process()
    reset_machine_id(cursor_path)
    modify_product_json(cursor_path, token_limit)
    patch_workbench(cursor_path, cursor_version)
    open_login_page(browser_type)

    console.print("\n")
    print_panel(
        "🎉 نسخه Pro با تمام امکانات و مدل‌های هوش مصنوعی فعال شد!",
        style="bold green",
        title="موفقیت"
    )
    console.print(reshape_text("✅ Cursor را باز کنید و از امکانات نامحدود لذت ببرید!\n"))


if __name__ == "__main__":
    main()