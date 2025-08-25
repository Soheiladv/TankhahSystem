import google.generativeai as genai
import os
from dotenv import load_dotenv # اگر از روش فایل .env استفاده می‌کنید

# --- بارگذاری کلید API ---
# اگر از فایل .env استفاده می‌کنید:
load_dotenv()
api_key = os.getenv("AIzaSyDAupPrZVXFegk38UEBGIRXKN3LVh_hCTw")

# اگر از Run Configuration پای‌چارم استفاده می‌کنید:
# api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    print("خطا: متغیر محیطی GOOGLE_API_KEY تنظیم نشده است.")
    exit()

try:
    genai.configure(api_key=api_key)
except Exception as e:
    print(f"خطا در تنظیم کلید API: {e}")
    exit()

# --- انتخاب مدل ---
# برای مدل متنی، 'gemini-pro' مناسب است.
# برای مدل چندوجهی (متن و تصویر)، 'gemini-pro-vision' را استفاده کنید.
try:
    model = genai.GenerativeModel('gemini-pro')

    # --- ارسال درخواست (Prompt) ---
    prompt = "پایتون چیست؟ به طور خلاصه توضیح بده."
    print(f"ارسال درخواست: {prompt}")

    # --- دریافت پاسخ ---
    response = model.generate_content(prompt)

    # --- نمایش پاسخ ---
    print("\nپاسخ Gemini:")
    # گاهی اوقات ممکن است پاسخ شامل بخش‌های نامناسب باشد که فیلتر شده‌اند
    if response.parts:
         print(response.text)
    else:
         print("پاسخی دریافت نشد یا محتوا مسدود شده است.")
         # می‌توانید جزئیات بیشتری از response.prompt_feedback ببینید
         # print(response.prompt_feedback)

except Exception as e:
    print(f"خطایی در هنگام ارتباط با API رخ داد: {e}")