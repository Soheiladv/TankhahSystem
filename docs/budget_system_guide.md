# راهنمای جامع سیستم مدیریت بودجه

## فهرست مطالب

1. [معرفی سیستم](#معرفی-سیستم)
2. [مدل‌های اصلی](#مدل‌های-اصلی)
3. [فرآیند تخصیص بودجه](#فرآیند-تخصیص-بودجه)
4. [فرآیند برگشت بودجه](#فرآیند-برگشت-بودجه)
5. [مدیریت انقضای بودجه](#مدیریت-انقضای-بودجه)
6. [گزارش‌گیری](#گزارش‌گیری)
7. [API ها](#api-ها)
8. [تست‌ها](#تست‌ها)
9. [عیب‌یابی](#عیب‌یابی)

---

## معرفی سیستم

سیستم مدیریت بودجه یک سیستم جامع برای مدیریت چرخه کامل بودجه از تخصیص تا مصرف و برگشت است.

### ویژگی‌های کلیدی

- ✅ **مدیریت دوره‌های بودجه**: تعریف و مدیریت دوره‌های بودجه کلان
- ✅ **تخصیص بودجه**: تخصیص بودجه به پروژه‌ها و سازمان‌ها
- ✅ **برگشت بودجه**: امکان برگشت مبالغ غیرمصرف شده
- ✅ **مدیریت انقضا**: کنترل خودکار انقضای بودجه
- ✅ **گزارش‌گیری**: گزارش‌های تفصیلی و جامع
- ✅ **تاریخچه کامل**: ثبت تمام عملیات و تغییرات

---

## مدل‌های اصلی

### 1. BudgetPeriod (دوره بودجه کلان)

```python
class BudgetPeriod(models.Model):
    organization = models.ForeignKey('core.Organization')
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    total_amount = models.DecimalField(max_digits=25, decimal_places=0)
    total_allocated = models.DecimalField(max_digits=25, decimal_places=2, default=0)
    returned_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0)
    locked_percentage = models.IntegerField(default=0)
    warning_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    is_active = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)
```

**ویژگی‌های مهم:**
- مدیریت مبلغ کل بودجه
- کنترل درصد قفل‌شده
- آستانه هشدار
- وضعیت فعال/غیرفعال

### 2. BudgetAllocation (تخصیص بودجه)

```python
class BudgetAllocation(models.Model):
    budget_period = models.ForeignKey('BudgetPeriod')
    organization = models.ForeignKey('core.Organization')
    budget_item = models.ForeignKey('BudgetItem')
    project = models.ForeignKey('core.Project')
    subproject = models.ForeignKey('core.SubProject', null=True, blank=True)
    allocated_amount = models.DecimalField(max_digits=25, decimal_places=2)
    allocation_date = models.DateField(default=timezone.now)
    returned_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False)
```

**ویژگی‌های مهم:**
- تخصیص بودجه به پروژه‌ها
- مدیریت مانده بودجه
- کنترل قفل بودن

### 3. BudgetTransaction (تراکنش بودجه)

```python
class BudgetTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('ALLOCATION', 'تخصیص اولیه'),
        ('CONSUMPTION', 'مصرف / هزینه'),
        ('ADJUSTMENT_INCREASE', 'افزایش تخصیص'),
        ('ADJUSTMENT_DECREASE', 'کاهش تخصیص'),
        ('RETURN', 'برگشت به بودجه'),
    )
    allocation = models.ForeignKey('BudgetAllocation')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=25, decimal_places=2)
    related_tankhah = models.ForeignKey('tankhah.Tankhah', null=True, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey('accounts.CustomUser')
```

**انواع تراکنش:**
- `ALLOCATION`: تخصیص اولیه بودجه
- `CONSUMPTION`: مصرف بودجه
- `ADJUSTMENT_INCREASE`: افزایش تخصیص
- `ADJUSTMENT_DECREASE`: کاهش تخصیص
- `RETURN`: برگشت بودجه

---

## فرآیند تخصیص بودجه

### مراحل تخصیص

1. **ایجاد دوره بودجه**
   ```python
   budget_period = BudgetPeriod.objects.create(
       organization=organization,
       name='دوره بودجه 1404',
       start_date=date(2024, 1, 1),
       end_date=date(2024, 12, 31),
       total_amount=Decimal('1000000000'),  # 1 میلیارد ریال
       locked_percentage=10,  # 10% قفل
       warning_threshold=20,  # 20% هشدار
   )
   ```

2. **ایجاد ردیف بودجه**
   ```python
   budget_item = BudgetItem.objects.create(
       budget_period=budget_period,
       organization=organization,
       name='ردیف بودجه عملیاتی',
       code='OP001',
   )
   ```

3. **تخصیص بودجه به پروژه**
   ```python
   allocation = BudgetAllocation.objects.create(
       budget_period=budget_period,
       organization=organization,
       budget_item=budget_item,
       project=project,
       allocated_amount=Decimal('50000000'),  # 50 میلیون ریال
       description='تخصیص بودجه برای پروژه X',
   )
   ```

### اعتبارسنجی تخصیص

```python
def clean(self):
    # بررسی مانده بودجه
    remaining_budget = self.budget_period.get_remaining_amount()
    if self.allocated_amount > remaining_budget:
        raise ValidationError("مبلغ تخصیص بیشتر از مانده بودجه است")
    
    # بررسی درصد قفل
    locked_amount = self.budget_period.get_locked_amount()
    available_for_allocation = remaining_budget - locked_amount
    if self.allocated_amount > available_for_allocation:
        raise ValidationError("نمی‌توان تخصیص داد. بودجه قفل شده است")
```

---

## فرآیند برگشت بودجه

### مراحل برگشت

1. **ثبت تراکنش برگشت**
   ```python
   return_transaction = BudgetTransaction.objects.create(
       allocation=budget_allocation,
       transaction_type='RETURN',
       amount=return_amount,
       related_tankhah=tankhah,
       description=f'برگشت {return_amount:,.0f} ریال',
       created_by=user,
   )
   ```

2. **به‌روزرسانی مبالغ**
   ```python
   # کاهش مبلغ تخصیص‌یافته
   budget_allocation.allocated_amount -= return_amount
   
   # افزایش مبلغ برگشتی
   budget_allocation.returned_amount += return_amount
   
   # به‌روزرسانی دوره بودجه
   budget_period.returned_amount += return_amount
   ```

### جریان مبلغ برگشتی

**فرمول محاسبه مانده:**
```
مانده = مبلغ_کل - مجموع_تخصیص‌ها + مجموع_برگشتی
```

**مثال:**
- مبلغ کل: 800,000,000 ریال
- مجموع تخصیص‌ها: 200,000,000 ریال
- مجموع برگشتی: 10,000,000 ریال
- **مانده قابل تخصیص: 610,000,000 ریال**

### اعتبارسنجی برگشت

```python
def validate_return(self):
    if self.transaction_type != 'RETURN':
        return True, None
    
    # بررسی مبلغ مثبت
    if self.amount <= 0:
        return False, "مبلغ بازگشت باید مثبت باشد"
    
    # بررسی عدم تجاوز از مبلغ تخصیص
    if self.amount > self.allocation.allocated_amount:
        return False, "مبلغ بازگشت نمی‌تواند بیشتر از مبلغ تخصیص باشد"
    
    # بررسی عدم تجاوز از مانده
    remaining_budget = self.allocation.get_remaining_amount()
    if self.amount > remaining_budget:
        return False, "مبلغ بازگشت نمی‌تواند بیشتر از مانده باشد"
    
    return True, None
```

---

## مدیریت انقضای بودجه

### شرایط قفل شدن

1. **AFTER_DATE**: قفل شدن بعد از تاریخ پایان
2. **MANUAL**: قفل شدن دستی
3. **ZERO_REMAINING**: قفل شدن هنگام رسیدن باقی‌مانده به صفر

### مهلت تمدید (Grace Period)

```python
def is_locked(self):
    # اعمال مهلت تمدید
    grace_days = getattr(settings, 'BUDGET_PERIOD_GRACE_DAYS', 0) or 0
    effective_end_date = self.end_date + timedelta(days=int(grace_days))
    
    if self.lock_condition == 'AFTER_DATE' and effective_end_date < timezone.now().date():
        return True, "دوره بودجه به دلیل پایان تاریخ قفل شده است"
    
    return False, "دوره بودجه فعال است"
```

### وضعیت‌های بودجه

- **normal**: وضعیت عادی
- **warning**: رسیدن به آستانه هشدار
- **locked**: قفل شده
- **completed**: تمام‌شده
- **inactive**: غیرفعال

---

## گزارش‌گیری

### گزارش مانده بودجه

```python
def get_budget_details(entity):
    """دریافت جزئیات بودجه برای یک موجودیت"""
    if isinstance(entity, Project):
        return {
            'total_budget': get_project_total_budget(entity),
            'used_budget': get_project_used_budget(entity),
            'remaining_budget': get_project_remaining_budget(entity),
        }
    elif isinstance(entity, Organization):
        return get_organization_budget(entity)
```

### گزارش تراکنش‌ها

```python
def get_transaction_report(budget_period, start_date=None, end_date=None):
    """گزارش تراکنش‌های دوره بودجه"""
    transactions = BudgetTransaction.objects.filter(
        allocation__budget_period=budget_period
    )
    
    if start_date:
        transactions = transactions.filter(timestamp__date__gte=start_date)
    if end_date:
        transactions = transactions.filter(timestamp__date__lte=end_date)
    
    return transactions.order_by('-timestamp')
```

### گزارش برگشت‌ها

```python
def get_returned_budgets(budget_period):
    """گزارش بودجه‌های برگشتی"""
    return BudgetHistory.objects.filter(
        content_type=ContentType.objects.get_for_model(BudgetAllocation),
        action='RETURN',
        content_object__budget_period=budget_period
    ).values('amount', 'details', 'created_at', 'created_by__username')
```

---

## API ها

### API دریافت مانده بودجه

```python
class ProjectAllocationFreeBudgetAPI(APIView):
    def get(self, request, pk):
        allocation = BudgetAllocation.objects.get(pk=pk, is_active=True)
        
        # محاسبه مانده آزاد
        transactions = BudgetTransaction.objects.filter(
            allocation=allocation.budget_allocation,
            project=allocation.project
        ).aggregate(
            consumed=Sum('amount', filter=Q(transaction_type='CONSUMPTION')),
            returned=Sum('amount', filter=Q(transaction_type='RETURN'))
        )
        
        free_budget = allocation.allocated_amount - consumed + returned
        
        return Response({
            'free_budget': float(free_budget),
            'allocated_amount': float(allocation.allocated_amount),
            'consumed_amount': float(consumed),
            'returned_amount': float(returned),
        })
```

### API لیست تخصیص‌ها

```python
class ProjectAllocationsAPI(APIView):
    def get(self, request):
        queryset = BudgetAllocation.objects.filter(
            is_active=True,
            is_locked=False
        )
        
        search = request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(project__name__icontains=search) |
                Q(budget_allocation__organization__name__icontains=search)
            )
        
        paginator = Paginator(queryset, 10)
        allocations = paginator.page(int(request.GET.get('page', 1)))
        
        return Response({
            'results': [
                {
                    'id': alloc.id,
                    'project_name': alloc.project.name,
                    'organization_name': alloc.budget_allocation.organization.name,
                    'allocated_amount': float(alloc.allocated_amount)
                } for alloc in allocations
            ],
            'pagination': {'more': allocations.has_next()}
        })
```

---

## تست‌ها

### تست برگشت بودجه

```python
def test_budget_return():
    """تست برگشت بودجه"""
    # ایجاد داده‌های تست
    budget_period = BudgetPeriod.objects.create(...)
    budget_allocation = BudgetAllocation.objects.create(...)
    
    # اجرای برگشت
    return_amount = Decimal('1000000')
    return_transaction = BudgetTransaction.objects.create(
        allocation=budget_allocation,
        transaction_type='RETURN',
        amount=return_amount,
        description='تست برگشت بودجه'
    )
    
    # بررسی نتایج
    budget_allocation.refresh_from_db()
    assert budget_allocation.returned_amount == return_amount
    assert budget_period.returned_amount == return_amount
```

### تست انقضای بودجه

```python
def test_budget_expiration():
    """تست انقضای بودجه"""
    # ایجاد دوره بودجه منقضی
    budget_period = BudgetPeriod.objects.create(
        end_date=date.today() - timedelta(days=1),
        lock_condition='AFTER_DATE'
    )
    
    # بررسی قفل بودن
    is_locked, message = budget_period.is_locked
    assert is_locked == True
    assert 'قفل شده' in message
```

---

## عیب‌یابی

### مشکلات رایج

#### 1. خطای محاسبه مانده

**مشکل:** مانده محاسبه شده نادرست است

**راه حل:**
```python
# پاک کردن کش
from django.core.cache import cache
cache.delete(f"budget_allocation_balance_{allocation.pk}")
cache.delete(f"project_remaining_budget_{project.pk}")

# محاسبه مجدد
remaining = allocation.get_remaining_amount()
```

#### 2. خطای اعتبارسنجی برگشت

**مشکل:** نمی‌توان مبلغ برگشتی را ثبت کرد

**بررسی:**
```python
# بررسی مانده تخصیص
remaining = allocation.get_remaining_amount()
print(f"مانده تخصیص: {remaining}")

# بررسی مبلغ برگشتی
if return_amount > remaining:
    print("مبلغ برگشتی بیشتر از مانده است")
```

#### 3. خطای انقضای بودجه

**مشکل:** بودجه زودتر از موعد قفل می‌شود

**بررسی:**
```python
# بررسی تنظیمات مهلت تمدید
grace_days = getattr(settings, 'BUDGET_PERIOD_GRACE_DAYS', 0)
print(f"مهلت تمدید: {grace_days} روز")

# بررسی تاریخ موثر
effective_end_date = budget_period.end_date + timedelta(days=grace_days)
print(f"تاریخ موثر پایان: {effective_end_date}")
```

### لاگ‌گیری

```python
import logging
logger = logging.getLogger(__name__)

# ثبت لاگ عملیات
logger.info(f"برگشت بودجه: {amount:,.0f} ریال از تخصیص {allocation.pk}")
logger.debug(f"مانده جدید: {allocation.get_remaining_amount():,.0f} ریال")
logger.error(f"خطا در برگشت بودجه: {str(e)}")
```

---

## بهترین روش‌ها

### 1. مدیریت تراکنش‌ها

```python
# همیشه از transaction.atomic استفاده کنید
with transaction.atomic():
    return_transaction = BudgetTransaction.objects.create(...)
    budget_allocation.allocated_amount -= return_amount
    budget_allocation.save()
```

### 2. اعتبارسنجی کامل

```python
# اعتبارسنجی در مدل
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
# کش کردن محاسبات پیچیده
cache_key = f"budget_balance_{allocation.pk}"
cached_balance = cache.get(cache_key)
if cached_balance is None:
    cached_balance = allocation.get_remaining_amount()
    cache.set(cache_key, cached_balance, timeout=300)
```

### 4. ثبت تاریخچه

```python
# ثبت تمام تغییرات در تاریخچه
BudgetHistory.objects.create(
    content_type=ContentType.objects.get_for_model(allocation),
    object_id=allocation.pk,
    action='RETURN',
    amount=return_amount,
    details=f'برگشت {return_amount:,.0f} ریال',
    created_by=user
)
```

---

## خلاصه

سیستم مدیریت بودجه یک سیستم جامع و قدرتمند است که:

- ✅ **تخصیص بودجه** را به صورت دقیق مدیریت می‌کند
- ✅ **برگشت بودجه** را با شفافیت کامل ثبت می‌کند
- ✅ **انقضای بودجه** را به صورت خودکار کنترل می‌کند
- ✅ **گزارش‌گیری** جامع و دقیق ارائه می‌دهد
- ✅ **تاریخچه کامل** از تمام عملیات نگهداری می‌کند

**مبلغ برگشتی کاملاً قابل تخصیص مجدد است و در محاسبه مانده دوره بودجه لحاظ می‌شود.**
