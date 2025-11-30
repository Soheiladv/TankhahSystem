# راهنمای کامل برگشت بودجه از زیرمجموعه به کلان بودجه

## خلاصه کلی (به فارسی، ساده و قابل اجرا)

### مفهوم برگشت بودجه

وقتی **بودجه دوره** (مثلاً رکورد با `id=30`) را **برمی‌گردانید**، در عمل دارید مبلغی از بودجه تخصیص‌داده‌شده آن زیرمجموعه را به بودجه بالاسری (**کلان بودجه**) بازمی‌گردانید.

### ساختار مدل‌ها

در سیستم شما:

- **BudgetPeriod** = کلان بودجه (parent)

  - `total_amount`: مبلغ کل بودجه
  - `total_allocated`: مجموع تخصیص‌ها به زیرمجموعه‌ها
  - `returned_amount`: مجموع بودجه برگشتی از زیرمجموعه‌ها

- **BudgetAllocation** = تخصیص بودجه به پروژه (child)
  - `budget_period`: ارتباط به کلان بودجه
  - `allocated_amount`: مبلغ تخصیص‌شده
  - `returned_amount`: مبلغ برگشتی از این تخصیص

### فرمول محاسبه موجودی (Available)

**برای کلان بودجه (BudgetPeriod):**

```
available = total_amount - total_allocated + returned_amount
```

**برای تخصیص بودجه (BudgetAllocation):**

```
available = allocated_amount - consumed + returned
```

### نحوه کار برگشت بودجه

در دیتابیس باید هم رکورد زیرمجموعه (child) و هم رکورد والد (parent) به‌صورت **اتمیک** به‌روزرسانی شوند:

1. **کاهش موجودی child:**

   - `allocated_amount` در BudgetAllocation کاهش می‌یابد
   - `returned_amount` در BudgetAllocation افزایش می‌یابد

2. **افزایش موجودی parent:**

   - `returned_amount` در BudgetPeriod افزایش می‌یابد
   - `total_allocated` در BudgetPeriod کاهش می‌یابد

3. **ثبت تراکنش:**
   - یک BudgetTransaction با نوع `RETURN` ثبت می‌شود
   - یک BudgetHistory برای ثبت تاریخچه ایجاد می‌شود

### مثال عددی

**قبل از برگشت:**

- کلان بودجه (parent):

  - `total_amount` = 1,000,000
  - `total_allocated` = 800,000
  - `returned_amount` = 0
  - `available` = 1,000,000 - 800,000 + 0 = 200,000

- بودجه دوره id=30 (child):
  - `allocated_amount` = 200,000
  - `consumed` = 150,000
  - `returned_amount` = 0
  - `available` = 200,000 - 150,000 + 0 = 50,000

**عملیات: می‌خواهیم مبلغ 30,000 را از child برگشت دهیم**

**بعد از برگشت:**

- child (BudgetAllocation):

  - `allocated_amount` = 200,000 - 30,000 = 170,000
  - `returned_amount` = 0 + 30,000 = 30,000
  - `available` = 170,000 - 150,000 + 30,000 = 50,000 ✅ (همان مبلغ قبلی)

- parent (BudgetPeriod):
  - `total_allocated` = 800,000 - 30,000 = 770,000
  - `returned_amount` = 0 + 30,000 = 30,000
  - `available` = 1,000,000 - 770,000 + 30,000 = 260,000 ✅ (200,000 + 30,000)

## چگونه برگشت بودجه انجام می‌شود؟

### روش 1: از صفحه جزئیات تخصیص بودجه (BudgetAllocation)

1. به صفحه جزئیات تخصیص بودجه بروید:

   ```
   /budgets/project-budget-allocation/<allocation_id>/
   ```

2. روی دکمه "برگشت بودجه" کلیک کنید

3. فرم برگشت را پر کنید:

   - مبلغ برگشتی
   - دلیل برگشت
   - توضیحات

4. سیستم به‌صورت خودکار:
   - تراکنش RETURN ایجاد می‌کند
   - موجودی child را کاهش می‌دهد
   - موجودی parent را افزایش می‌دهد
   - تاریخچه را ثبت می‌کند

### روش 2: از صفحه جزئیات کلان بودجه (BudgetPeriod)

در صفحه جزئیات BudgetPeriod (`/budgets/budgetperiod/30/`):

1. جدول "تخصیص‌های بودجه" را مشاهده کنید
2. برای هر تخصیص که `available > 0` باشد، دکمه "برگشت بودجه" نمایش داده می‌شود
3. روی دکمه کلیک کنید و فرم را پر کنید

## نمایش مبالغ برگشتی در کلان بودجه

در صفحه جزئیات BudgetPeriod، بخش‌های زیر نمایش داده می‌شوند:

### 1. خلاصه وضعیت بودجه

- **بودجه کل**: `total_amount`
- **تخصیص یافته**: `total_allocated`
- **باقی‌مانده**: `total_amount - total_allocated + returned_amount`

### 2. جدول برگشت‌ها

- تاریخ برگشت
- مبلغ برگشتی
- تخصیص مرتبط
- توضیحات

### 3. موجودی (Available)

موجودی کلان بودجه به‌صورت خودکار با برگشت بودجه افزایش می‌یابد:

```
available = total_amount - total_allocated + returned_amount
```

## کدهای مهم در سیستم

### 1. فرم برگشت بودجه

```python
# budgets/BudgetReturn/forms_BudgetReturm.py
class BudgetReturnForm(forms.ModelForm):
    amount = forms.DecimalField(label='مبلغ برگشتی')
    return_reason = forms.ChoiceField(label='دلیل برگشت')
    description = forms.Textarea(label='توضیحات')
```

### 2. منطق برگشت بودجه

```python
# budgets/BudgetReturn/froms_BudgetTransferForm.py
def save(self):
    # ایجاد تراکنش RETURN
    BudgetTransaction.objects.create(
        allocation=allocation.budget_allocation,
        transaction_type='RETURN',
        amount=amount,
        ...
    )

    # به‌روزرسانی child
    allocation.returned_amount += amount
    allocation.allocated_amount -= amount

    # به‌روزرسانی parent
    allocation.budget_allocation.budget_period.returned_amount += amount
    allocation.budget_allocation.budget_period.total_allocated -= amount
```

### 3. محاسبه موجودی

```python
# budgets/models.py
def get_remaining_amount(self):
    return self.total_amount - self.total_allocated + self.returned_amount
```

## نکات مهم

1. **Transaction اتمیک**: تمام عملیات در یک `transaction.atomic()` انجام می‌شود تا در صورت خطا، همه تغییرات برگردانده شوند.

2. **اعتبارسنجی**: مبلغ برگشتی نمی‌تواند بیشتر از موجودی قابل برگشت باشد:

   ```python
   if amount > remaining_budget:
       raise ValidationError("مبلغ برگشتی بیشتر از موجودی است")
   ```

3. **ثبت تاریخچه**: هر برگشت در AuditLog و BudgetHistory ثبت می‌شود.

4. **اعلان‌ها**: پس از برگشت، وضعیت بودجه بررسی می‌شود و در صورت نیاز اعلان ارسال می‌شود.

## مشکلات احتمالی و راه حل

### مشکل 1: "مبلغ برگشتی بیشتر از موجودی است"

**راه حل:** بررسی کنید که:

- مبلغ وارد شده کمتر یا مساوی `available` باشد
- از فیلد `get_remaining_amount()` برای محاسبه موجودی استفاده کنید

### مشکل 2: "موجودی در کلان بودجه به‌روز نشده است"

**راه حل:** بررسی کنید که:

- `returned_amount` در BudgetPeriod افزایش یافته است
- `total_allocated` در BudgetPeriod کاهش یافته است
- از `refresh_from_db()` برای به‌روزرسانی استفاده کنید

### مشکل 3: "تراکنش برگشت ثبت نشده است"

**راه حل:** بررسی کنید که:

- `BudgetTransaction` با نوع `RETURN` ایجاد شده است
- `transaction_id` منحصر به فرد است
- `created_by` به درستی تنظیم شده است

## URL های مرتبط

- لیست کلان بودجه‌ها: `/budgets/budgetperiod/`
- جزئیات کلان بودجه: `/budgets/budgetperiod/<pk>/`
- برگشت بودجه از تخصیص: `/budgets/budget/allocation/<allocation_id>/return/`
- جزئیات تخصیص بودجه: `/budgets/project-budget-allocation/<pk>/`

## خلاصه نهایی

1. ✅ سیستم برگشت بودجه از قبل در پروژه وجود دارد
2. ✅ برگشت از BudgetAllocation (child) به BudgetPeriod (parent) انجام می‌شود
3. ✅ موجودی کلان بودجه به‌صورت خودکار با برگشت افزایش می‌یابد
4. ✅ تمام عملیات در یک تراکنش اتمیک انجام می‌شود
5. ✅ تاریخچه و لاگ تمام برگشت‌ها ثبت می‌شود

**برای استفاده:**

- از صفحه جزئیات BudgetAllocation دکمه "برگشت بودجه" را کلیک کنید
- یا از صفحه جزئیات BudgetPeriod از جدول تخصیص‌ها دکمه برگشت را انتخاب کنید
