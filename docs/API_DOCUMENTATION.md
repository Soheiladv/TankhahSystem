# 📊 مستندات API های سیستم گزارش‌گیری

## 🎯 خلاصه پاکسازی

### ✅ **قبل از پاکسازی:**
- **14 کلاس API** در فایل
- **8 API تکراری** و غیرضروری
- **6 API فعال** و ضروری
- **57% کد تکراری**

### ✅ **بعد از پاکسازی:**
- **6 کلاس API** در فایل
- **0 API تکراری**
- **6 API فعال** و بهینه
- **0% کد تکراری**

---

## 🔧 **API های فعال**

### 1️⃣ **ComprehensiveBudgetReportView**
```python
class ComprehensiveBudgetReportView(PermissionBaseView, ListView)
```
**وظیفه:** گزارش جامع بودجه
**URL:** `/reports/comprehensive-budget/`
**Template:** `reports/v2/comprehensive_report_main.html`
**ویژگی‌ها:**
- نمایش دوره‌های بودجه
- آمار تخصیص و مصرف
- خروجی Excel
- جستجو و فیلتر

### 2️⃣ **APIOrganizationsForPeriodView**
```python
class APIOrganizationsForPeriodView(PermissionBaseView, View)
```
**وظیفه:** دریافت سازمان‌های یک دوره
**URL:** `/reports/api/organizations-for-period/<int:period_pk>/`
**کاربرد:** AJAX برای بارگذاری سازمان‌ها
**خروجی:** HTML content

### 3️⃣ **BudgetItemsForOrgPeriodAPIView**
```python
class BudgetItemsForOrgPeriodAPIView(APIView)
```
**وظیفه:** دریافت سرفصل‌های بودجه برای سازمان و دوره
**URL:** `/reports/api/budget-items-for-org-period/<int:period_pk>/<int:org_pk>/`
**کاربرد:** AJAX برای نمایش سرفصل‌ها
**خروجی:** JSON با HTML content

### 4️⃣ **APIFactorsForTankhahView**
```python
class APIFactorsForTankhahView(View)
```
**وظیفه:** دریافت فاکتورهای یک تنخواه
**URL:** `/api/factors-for-tankhah/<int:tankhah_pk>/`
**کاربرد:** AJAX برای نمایش فاکتورها
**خروجی:** JSON با HTML content

### 5️⃣ **APITankhahsForAllocationView**
```python
class APITankhahsForAllocationView(View)
```
**وظیفه:** دریافت تنخواه‌های یک تخصیص
**URL:** `/api/tankhahs-for-allocation/<int:alloc_pk>/`
**کاربرد:** AJAX برای نمایش تنخواه‌ها
**خروجی:** JSON با HTML content

### 6️⃣ **OrganizationAllocationsAPIView**
```python
class OrganizationAllocationsAPIView(PermissionBaseView, View)
```
**وظیفه:** دریافت تخصیص‌های سازمان برای دوره
**URL:** `/api/period/<int:period_pk>/organization-allocations/`
**کاربرد:** AJAX برای نمایش تخصیص‌ها
**خروجی:** JSON با HTML content

---

## 🗑️ **API های حذف شده**

### ❌ **API های تکراری (8 عدد):**
1. `AComprehensiveBudgetReportView` - نسخه دوم گزارش جامع
2. `APIBudgetItemsForOrgPeriodView` - نسخه دوم API سرفصل‌ها
3. `APITankhahsForPBAView` - نسخه دوم API تنخواه‌ها
4. `AA__APIFactorsForTankhahView` - نسخه دوم API فاکتورها
5. `AA__BudgetItemsForOrgPeriodAPIView` - نسخه سوم API سرفصل‌ها
6. `AzA__OrganizationAllocationsAPIView` - نسخه دوم API تخصیص‌ها
7. `AbPITankhahsForAllocationView` - نسخه سوم API تنخواه‌ها
8. `AA__APIOrganizationsForPeriodView` - نسخه دوم API سازمان‌ها

---

## 📈 **مزایای پاکسازی**

### ✅ **بهبود عملکرد:**
- کاهش **57% حجم کد**
- حذف **8 کلاس تکراری**
- بهبود **سرعت بارگذاری**
- کاهش **مصرف حافظه**

### ✅ **بهبود نگهداری:**
- کد **تمیزتر** و **خوانا**
- کاهش **پیچیدگی**
- آسان‌تر **دیباگ**
- بهتر **مستندسازی**

### ✅ **بهبود توسعه:**
- API های **یکپارچه**
- کاهش **تداخل**
- بهتر **تست**
- آسان‌تر **گسترش**

---

## 🔗 **لینک‌های مرتبط**

### 📊 **گزارش‌ها:**
- گزارش جامع: `/reports/comprehensive-budget/`
- گزارش تخصیص: `/reports/budget-allocation/<id>/report/`
- گزارش پیشرفته: `/reports/budget-allocation/<id>/report-enhanced/`

### 🔌 **API ها:**
- سازمان‌ها: `/reports/api/organizations-for-period/<period_pk>/`
- سرفصل‌ها: `/reports/api/budget-items-for-org-period/<period_pk>/<org_pk>/`
- فاکتورها: `/api/factors-for-tankhah/<tankhah_pk>/`
- تنخواه‌ها: `/api/tankhahs-for-allocation/<alloc_pk>/`
- تخصیص‌ها: `/api/period/<period_pk>/organization-allocations/`

---

## 🎯 **نتیجه‌گیری**

پاکسازی موفقیت‌آمیز انجام شد و سیستم گزارش‌گیری بهینه‌سازی شد:

- ✅ **حذف 57% کد تکراری**
- ✅ **بهبود عملکرد**
- ✅ **کاهش پیچیدگی**
- ✅ **آسان‌تر نگهداری**
- ✅ **بهتر مستندسازی**

سیستم حالا **تمیز**، **بهینه** و **قابل نگهداری** است! 🚀
