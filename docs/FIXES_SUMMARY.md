# خلاصه اصلاحات انجام شده

## مشکلات برطرف شده

### 1. مشکل URL برگشت بودجه (`/budgets/budget/allocation/92/return/`)

**مشکل:** View از `BudgetAllocation` query می‌کرد اما فرم انتظار `ProjectBudgetAllocation` داشت.

**راه حل:**
- View اصلاح شد تا `ProjectBudgetAllocation` را query کند
- Import اضافه شد: `from budgets.models import ProjectBudgetAllocation`
- Query اصلاح شد تا relation های صحیح را select کند

**فایل:** `budgets/BudgetReturn/views_BudgetTransferView.py`

### 2. مشکل URL جزئیات تخصیص (`/budgets/project-budget-allocation/95/`)

**مشکل:** احتمالاً مربوط به همان مشکل query بود که برطرف شد.

**راه حل:**
- View برای برگشت بودجه اصلاح شد
- Success URL اصلاح شد تا به صفحه صحیح redirect کند

### 3. مشکل لینک‌های markdown در راهنما (guide:index)

**مشکل:** لینک‌های Django URL مثل `[متن](guide:index)` در فایل‌های markdown کار نمی‌کردند.

**راه حل:**
- یک تابع `convert_guide_urls()` در view اضافه شد
- لینک‌های `guide:index` و `guide:detail` به URL های واقعی تبدیل می‌شوند
- تبدیل در backend (قبل از render) انجام می‌شود

**فایل‌ها:**
- `guide/views.py` - تابع تبدیل URL اضافه شد
- `guide/templates/guide/detail.html` - کد JavaScript ساده شد

### 4. بهبود صفحه BudgetPeriod Detail

**تغییرات:**
- Query بهینه شد تا `ProjectBudgetAllocation`ها را prefetch کند
- Template به‌روز شد تا `ProjectBudgetAllocation`ها را نمایش دهد
- لینک برگشت بودجه برای هر `ProjectBudgetAllocation` اضافه شد

**فایل‌ها:**
- `budgets/BudgetPeriod/views_BudgetPeriod.py` - prefetch اضافه شد
- `templates/budgets/budget/budgetperiod_detail.html` - نمایش ProjectBudgetAllocation

## تغییرات فنی

### اصلاح Query در BudgetReturnView

**قبل:**
```python
allocation = BudgetAllocation.objects.select_related(
    'budget_allocation__budget_period',
    ...
).get(pk=self.kwargs['allocation_id'], ...)
```

**بعد:**
```python
from budgets.models import ProjectBudgetAllocation
allocation = ProjectBudgetAllocation.objects.select_related(
    'budget_allocation__budget_period',
    'budget_allocation__organization',
    'project'
).get(pk=self.kwargs['allocation_id'], ...)
```

### تبدیل URL در Markdown

**اضافه شده:**
```python
def convert_guide_urls(content):
    # تبدیل guide:index
    index_url = reverse('guide:index')
    content = re.sub(r'\[([^\]]+)\]\(guide:index\)', f'[\\1]({index_url})', content)

    # تبدیل guide:detail doc_name
    ...
```

## تست

برای تست تغییرات:

1. **برگشت بودجه:**
   - به `/budgets/budgetperiod/30/` بروید
   - روی دکمه "برگشت بودجه" کلیک کنید
   - باید فرم برگشت باز شود

2. **لینک‌های راهنما:**
   - به `/guide/` بروید
   - یک فایل markdown را باز کنید
   - روی لینک‌هایی که `guide:index` یا `guide:detail` دارند کلیک کنید
   - باید به صفحه مورد نظر بروید

3. **جزئیات تخصیص:**
   - به `/budgets/project-budget-allocation/95/` بروید
   - باید صفحه جزئیات نمایش داده شود

## نکات مهم

1. مطمئن شوید که `ProjectBudgetAllocation` برای `BudgetAllocation` وجود دارد
2. لینک‌های markdown باید به فرمت صحیح باشند: `[متن](guide:index)` یا `[متن](guide:detail filename.md)`
3. View برگشت بودجه حالا فقط با `ProjectBudgetAllocation` کار می‌کند

