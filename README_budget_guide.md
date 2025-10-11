# راهنمای سیستم مدیریت بودجه

## فهرست مطالب

- [معرفی](#معرفی)
- [نصب و راه‌اندازی](#نصب-و-راه‌اندازی)
- [استفاده از راهنما](#استفاده-از-راهنما)
- [فایل‌های تست](#فایل‌های-تست)
- [API ها](#api-ها)
- [عیب‌یابی](#عیب‌یابی)

## معرفی

این راهنما شامل مستندات جامع سیستم مدیریت بودجه است که شامل:

- ✅ **مدل‌های اصلی**: BudgetPeriod, BudgetAllocation, BudgetTransaction, BudgetHistory
- ✅ **فرآیند تخصیص بودجه**: از ایجاد دوره تا تخصیص به پروژه‌ها
- ✅ **فرآیند برگشت بودجه**: نحوه برگشت مبالغ و تخصیص مجدد
- ✅ **مدیریت انقضای بودجه**: کنترل خودکار و دستی انقضا
- ✅ **گزارش‌گیری**: گزارش‌های تفصیلی و جامع
- ✅ **API ها**: رابط‌های برنامه‌نویسی
- ✅ **تست‌ها**: تست‌های جامع عملکرد سیستم

## نصب و راه‌اندازی

### پیش‌نیازها

- Python 3.8+
- Django 3.2+
- MySQL 8.0+
- Redis (برای کش)

### نصب

```bash
# کلون کردن پروژه
git clone <repository-url>
cd BudgetsSystem

# نصب وابستگی‌ها
pip install -r requirements.txt

# اجرای مایگریشن‌ها
python manage.py migrate

# ایجاد کاربر ادمین
python manage.py createsuperuser

# اجرای سرور
python manage.py runserver
```

## استفاده از راهنما

### دسترسی به راهنما

1. **از داشبورد بودجه**: روی کارت "راهنمای سیستم" کلیک کنید
2. **مستقیماً**: به آدرس `/budgets/guide/` بروید
3. **از منو**: در بخش بودجه، گزینه "راهنما" را انتخاب کنید

### ویژگی‌های راهنما

- 📖 **مستندات کامل**: تمام جنبه‌های سیستم پوشش داده شده
- 🔍 **جستجوی آسان**: فهرست مطالب با لینک‌های مستقیم
- 💻 **نمونه کد**: کدهای عملی برای هر بخش
- 📊 **آمار زنده**: آمار فعلی سیستم در راهنما
- 🎨 **طراحی زیبا**: رابط کاربری مدرن و کاربرپسند

## فایل‌های تست

### تست‌های موجود

| فایل | توضیحات | وضعیت |
|------|---------|--------|
| `test_budget_return_model_only.py` | تست ساده برگشت بودجه | ✅ موفق |
| `test_budget_return_comprehensive.py` | تست جامع برگشت بودجه | ✅ موفق |
| `analyze_budget_return_flow.py` | تحلیل جریان مبلغ برگشتی | ✅ موفق |
| `test_reallocate_returned_budget.py` | تست تخصیص مجدد مبلغ برگشتی | ✅ موفق |

### اجرای تست‌ها

```bash
# اجرای تست ساده
python test_budget_return_model_only.py

# اجرای تست جامع
python test_budget_return_comprehensive.py

# تحلیل جریان مبلغ برگشتی
python analyze_budget_return_flow.py

# تست تخصیص مجدد
python test_reallocate_returned_budget.py
```

### نتایج تست‌ها

همه تست‌ها با موفقیت اجرا شده‌اند و نشان می‌دهند که:

- ✅ سیستم برگشت بودجه به درستی کار می‌کند
- ✅ مبلغ برگشتی در محاسبه مانده لحاظ می‌شود
- ✅ امکان تخصیص مجدد مبلغ برگشتی وجود دارد
- ✅ تمام عملیات در تاریخچه ثبت می‌شوند

## API ها

### API های موجود

#### 1. دریافت مانده آزاد تخصیص بودجه

```http
GET /api/budget/allocation/{id}/free-budget/
```

**پاسخ:**
```json
{
    "free_budget": 50000000.0,
    "allocated_amount": 100000000.0,
    "consumed_amount": 30000000.0,
    "returned_amount": 20000000.0
}
```

#### 2. لیست تخصیص‌های بودجه

```http
GET /api/budget/allocations/?search=پروژه&page=1
```

**پاسخ:**
```json
{
    "results": [
        {
            "id": 1,
            "project_name": "پروژه نمونه",
            "organization_name": "سازمان نمونه",
            "allocated_amount": 50000000.0
        }
    ],
    "pagination": {"more": false}
}
```

## عیب‌یابی

### مشکلات رایج

#### 1. خطای محاسبه مانده

**علت:** کش قدیمی یا محاسبه نادرست

**راه حل:**
```python
from django.core.cache import cache
cache.delete(f"budget_allocation_balance_{allocation.pk}")
remaining = allocation.get_remaining_amount()
```

#### 2. خطای اعتبارسنجی برگشت

**علت:** مبلغ برگشتی بیشتر از مانده

**بررسی:**
```python
remaining = allocation.get_remaining_amount()
if return_amount > remaining:
    print("مبلغ برگشتی بیشتر از مانده است")
```

#### 3. خطای انقضای بودجه

**علت:** تنظیمات مهلت تمدید

**بررسی:**
```python
grace_days = getattr(settings, 'BUDGET_PERIOD_GRACE_DAYS', 0)
effective_end_date = budget_period.end_date + timedelta(days=grace_days)
```

### لاگ‌گیری

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"برگشت بودجه: {amount:,.0f} ریال")
logger.debug(f"مانده جدید: {remaining:,.0f} ریال")
logger.error(f"خطا: {str(e)}")
```

## بهترین روش‌ها

### 1. مدیریت تراکنش‌ها

```python
from django.db import transaction

with transaction.atomic():
    return_transaction = BudgetTransaction.objects.create(...)
    budget_allocation.allocated_amount -= return_amount
    budget_allocation.save()
```

### 2. اعتبارسنجی کامل

```python
def clean(self):
    super().clean()
    if self.amount <= 0:
        raise ValidationError("مبلغ باید مثبت باشد")
    
    remaining = self.allocation.get_remaining_amount()
    if self.amount > remaining:
        raise ValidationError("مبلغ بیشتر از مانده است")
```

### 3. استفاده از کش

```python
from django.core.cache import cache

cache_key = f"budget_balance_{allocation.pk}"
cached_balance = cache.get(cache_key)
if cached_balance is None:
    cached_balance = allocation.get_remaining_amount()
    cache.set(cache_key, cached_balance, timeout=300)
```

### 4. ثبت تاریخچه

```python
BudgetHistory.objects.create(
    content_type=ContentType.objects.get_for_model(allocation),
    object_id=allocation.pk,
    action='RETURN',
    amount=return_amount,
    details=f'برگشت {return_amount:,.0f} ریال',
    created_by=user
)
```

## خلاصه

سیستم مدیریت بودجه یک سیستم جامع و قدرتمند است که:

- ✅ **تخصیص بودجه** را به صورت دقیق مدیریت می‌کند
- ✅ **برگشت بودجه** را با شفافیت کامل ثبت می‌کند
- ✅ **انقضای بودجه** را به صورت خودکار کنترل می‌کند
- ✅ **گزارش‌گیری** جامع و دقیق ارائه می‌دهد
- ✅ **تاریخچه کامل** از تمام عملیات نگهداری می‌کند

**مبلغ برگشتی کاملاً قابل تخصیص مجدد است و در محاسبه مانده دوره بودجه لحاظ می‌شود.**

---

## پشتیبانی

برای سوالات و پشتیبانی:

- 📧 ایمیل: support@example.com
- 📞 تلفن: 021-12345678
- 🌐 وب‌سایت: https://example.com

---

**آخرین به‌روزرسانی:** 1403/07/20
