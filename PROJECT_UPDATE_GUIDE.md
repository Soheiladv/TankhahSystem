## راهنمای به‌روزرسانی: روش جدید ثبت قوانین گردش کار (Branch ↔ HQ)

این سند، جمع‌بندی تغییرات این گفتگو و روش جدید تعریف و مدیریت قوانین گردش کار را ارائه می‌کند.

### 1) مسئله اولیه
- فاکتور 79 در وضعیت `PENDING_APPROVAL` باقی می‌ماند چون گذار `APPROVE` دوباره به همان وضعیت برمی‌گشت (حلقه).
- نیاز: افزودن گذار «ارسال به دفتر مرکزی» و تکمیل مسیرهای ستاد تا «تأیید نهایی»، به‌همراه امکان فعال/غیرفعال کردن قانون در سطح کاربر.

### 2) مدل‌ها و امکانات موجود (بدون تغییر اسکیمای DB)
- مدل‌های پایهٔ گردش کار در `core/models.py`:
  - `Status`, `Action`, `EntityType`, `Transition`
  - تخصیص گذارها به پست‌ها از طریق `Transition.allowed_posts`
  - پرچم‌های نهایی در `Post`: `can_final_approve_factor`, `can_final_approve_budget` (برای دستور پرداخت هم از factor استفاده شده است)
  - کنترل در سطح کاربر:
    - `PostRuleAssignment` (قانون به پست)
    - `UserRuleOverride` (فعالسازی/غیرفعالسازی صریح قانون برای کاربر)

### 3) استانداردسازی کدهای وضعیت/اکشن
- وضعیت‌ها: `DRAFT`, `PENDING_APPROVAL`, `APPROVED_INTERMEDIATE`, `APPROVED`, `REJECTED`
- اکشن‌ها: `SUBMIT`, `APPROVE`, `FINAL_APPROVE`, `REJECT`
- نکته: برای سازگاری با ویوها، از `APPROVED` و `REJECTED` به‌عنوان نهایی استفاده می‌کنیم.

### 4) دستور جدید ساخت قوانین
- فایل: `core/management/commands/generate_full_rules.py`
- کاربرد:
```bash
python manage.py generate_full_rules --branch-code=<BRANCH_CODE> --hq-code=<HQ_CODE>
# مثال عملی:
python manage.py generate_full_rules --branch-code=HSarein --hq-code=HQ_ITDC
```
- خروجی دستور:
  - ایجاد/به‌روزرسانی وضعیت‌ها و اقدامات در صورت نبود
  - ایجاد گذارهای شعبه:
    - `DRAFT --SUBMIT--> PENDING_APPROVAL`
    - `PENDING_APPROVAL --SUBMIT--> APPROVED_INTERMEDIATE` (ارسال به ستاد)
    - `PENDING_APPROVAL --REJECT--> REJECTED`
  - ایجاد گذارهای دفتر مرکزی:
    - `APPROVED_INTERMEDIATE --APPROVE--> APPROVED_INTERMEDIATE` (تأییدهای میانی)
    - `APPROVED_INTERMEDIATE --FINAL_APPROVE--> APPROVED` (تأیید نهایی)
    - `APPROVED_INTERMEDIATE --REJECT--> REJECTED`
  - تخصیص پست‌ها:
    - شعبه: همهٔ پست‌های فعال همان شعبه برای گذارهای شعبه
    - ستاد: `APPROVE` برای پست‌های غیرنهایی؛ `FINAL_APPROVE` فقط برای پست‌های دارای پرچم نهایی مربوط

### 5) کنترل فعال/غیرفعال قانون در سطح کاربر
- ادمین‌ها:
  - `UserRuleOverride` و `PostRuleAssignment` در `core/admin.py` ثبت شده‌اند.
  - می‌توانید برای هر کاربر/پست/سازمان/نوع موجودیت، اقدام‌ها را فعال یا غیرفعال کنید.
- تابع کمکی برای استفاده در ویوها/سرویس‌ها:
```python
from core.utils_workflow import get_allowed_actions_for_user

result = get_allowed_actions_for_user(user, organization, 'FACTOR', current_status)
# {'allowed': [...], 'blocked': [...]} را برمی‌گرداند
```

### 6) تست مسیر فاکتور (نمونه)
1) در شعبه (HSarein):
   - از `DRAFT` با `SUBMIT` به `PENDING_APPROVAL` بروید
   - از `PENDING_APPROVAL` با `SUBMIT` به `APPROVED_INTERMEDIATE` بروید
2) در ستاد (HQ_ITDC):
   - کاربران غیرنهایی می‌توانند `APPROVE` بزنند (وضعیت ثابت می‌ماند)
   - تأییدکننده نهایی با `FINAL_APPROVE` وضعیت را به `APPROVED` می‌برد
   - در هر دو سطح `REJECT` به `REJECTED` منتهی می‌شود

### 7) نکات نگهداری و رفع اشکال
- اگر دستور اجرا نشد:
  - کد سازمان‌ها را بررسی کنید:
```bash
python manage.py shell -c "from core.models import Organization; print(list(Organization.objects.values_list('code', flat=True)))"
```
  - اگر خطای فونت ReportLab دیدید (پیام فارسی در لاگ)، نادیده بگیرید؛ مانع اجرای دستور نیست.
- اگر در ویوها اقدام دیده نمی‌شود:
  - عضویت کاربر در پست‌های فعالِ همان سازمان را بررسی کنید.
  - `Transition` های سازمان/موجودیت/وضعیت فعلی و `allowed_posts` را چک کنید.
  - Overrideهای کاربر (`UserRuleOverride`) را بررسی کنید.

### 8) یادداشت‌های سازگاری
- این تغییرات اسکیمای دیتابیس را تغییر نمی‌دهد.
- کدهای وضعیت با ویوهای موجود هماهنگ شده‌اند (`APPROVED`, `REJECTED`).

---
برای ساخت قوانین برای سازمان‌های دیگر، همان دستور را با کدهای سازمان مربوط اجرا کنید.
