# به‌روزرسانی داشبورد و سیستم مدیریت قوانین گردش کار

## تغییرات اعمال شده

### 1. اضافه شدن لینک‌های جدید مدیریت قوانین گردش کار

در فایل `BudgetsSystem/view/view_Dashboard.py` لینک‌های زیر اضافه شده‌اند:

#### در بخش "قوانین سیستم (رول‌های دسترسی)":
- **مدیریت قوانین گردش کار**: `workflow_management:workflow_dashboard`
- **تمپلیت‌های قوانین**: `workflow_management:template_list`

#### در بخش "گزارشات جامع مدیرعامل":
- **داشبورد اجرایی**: `executive_dashboard`
- **گزارشات بودجه (کلی)**: `comprehensive_budget_report`
- **گزارشات فاکتور (کلی)**: `comprehensive_factor_report`
- **گزارشات تنخواه (کلی)**: `comprehensive_tankhah_report`
- **گزارشات عملکرد مالی**: `financial_performance_report`
- **گزارشات تحلیلی**: `analytical_reports`

### 2. ایجاد کلاس ExecutiveDashboardView

کلاس جدیدی برای داشبورد اجرایی مدیرعامل ایجاد شده که شامل:

#### ویژگی‌های اصلی:
- **نمایش جامع آمار**: بودجه، تنخواه، فاکتور
- **روندهای ماهانه**: نمودارهای تعاملی برای هر بخش
- **تحلیل عملکرد مالی**: شاخص‌های کلیدی عملکرد
- **تحلیل ریسک‌ها**: شناسایی و هشدار ریسک‌ها
- **رابط کاربری زیبا**: طراحی مدرن و responsive

#### متدهای کلیدی:
- `_get_budget_statistics()`: آمار کلی بودجه
- `_get_tankhah_statistics()`: آمار کلی تنخواه
- `_get_factor_statistics()`: آمار کلی فاکتورها
- `_get_analytical_data()`: داده‌های تحلیلی
- `_get_risk_analysis()`: تحلیل ریسک‌ها

### 3. ایجاد تمپلیت HTML برای داشبورد اجرایی

فایل `templates/core/executive_dashboard.html` با ویژگی‌های زیر:

#### طراحی:
- **رنگ‌بندی مدرن**: استفاده از gradient ها و رنگ‌های جذاب
- **کارت‌های تعاملی**: hover effects و انیمیشن‌ها
- **تب‌های سازمان‌یافته**: جداسازی گزارشات در تب‌های مختلف
- **نمودارهای تعاملی**: استفاده از Chart.js

#### بخش‌های اصلی:
1. **هدر داشبورد**: نمایش تاریخ و ساعت
2. **آمار کلی**: 4 کارت اصلی با آمار کلیدی
3. **تب‌های گزارشات**:
   - گزارشات بودجه
   - گزارشات تنخواه
   - گزارشات فاکتور
   - گزارشات تحلیلی

### 4. ایجاد ویوهای گزارشات جامع

#### فایل‌های جدید:
- `core/views_executive_dashboard.py`: ویوهای گزارشات جامع
- `core/urls_executive_dashboard.py`: URL patterns
- `templates/core/executive_dashboard.html`: تمپلیت اصلی

#### کلاس‌های ایجاد شده:
1. **ComprehensiveBudgetReportView**: گزارش جامع بودجه
2. **ComprehensiveFactorReportView**: گزارش جامع فاکتورها
3. **ComprehensiveTankhahReportView**: گزارش جامع تنخواه
4. **FinancialPerformanceReportView**: گزارش عملکرد مالی
5. **AnalyticalReportsView**: گزارشات تحلیلی

### 5. ویژگی‌های داشبورد اجرایی

#### آمار کلی:
- **بودجه کل تخصیص‌یافته**: نمایش مبلغ کل بودجه
- **مبلغ کل تنخواه**: نمایش مبلغ کل تنخواه‌ها
- **مبلغ کل فاکتورها**: نمایش مبلغ کل فاکتورها
- **تعداد ریسک‌ها**: نمایش ریسک‌های شناسایی شده

#### نمودارهای تعاملی:
- **روند ماهانه بودجه**: نمودار خطی برای بودجه تخصیص‌یافته و مصرف‌شده
- **روند ماهانه تنخواه**: نمودار میله‌ای برای تنخواه ایجاد شده و پرداخت شده
- **روند ماهانه فاکتورها**: نمودار میله‌ای برای فاکتورهای ایجاد شده و پرداخت شده

#### تحلیل‌های پیشرفته:
- **تحلیل عملکرد مالی**: نرخ استفاده از بودجه، کارایی تنخواه
- **تحلیل روندها**: مقایسه ماه جاری با ماه قبل
- **تحلیل ریسک‌ها**: شناسایی ریسک‌های بالا و متوسط

### 6. بهبودهای UI/UX

#### طراحی مدرن:
- استفاده از gradient backgrounds
- کارت‌های با shadow و border radius
- انیمیشن‌های hover
- رنگ‌بندی مناسب برای انواع داده‌ها

#### Responsive Design:
- سازگار با تمام اندازه‌های صفحه
- استفاده از Bootstrap grid system
- تنظیمات مناسب برای موبایل و تبلت

#### تعامل کاربر:
- تب‌های تعاملی برای جداسازی گزارشات
- نمودارهای قابل تعامل
- نمایش اطلاعات به صورت کارت‌های زیبا

### 7. نحوه استفاده

#### دسترسی به داشبورد اجرایی:
```python
# در URL patterns
path('executive-dashboard/', ExecutiveDashboardView.as_view(), name='executive_dashboard')
```

#### دسترسی به گزارشات جامع:
```python
# گزارشات بودجه
path('comprehensive-budget-report/', ComprehensiveBudgetReportView.as_view(), name='comprehensive_budget_report')

# گزارشات فاکتور
path('comprehensive-factor-report/', ComprehensiveFactorReportView.as_view(), name='comprehensive_factor_report')

# گزارشات تنخواه
path('comprehensive-tankhah-report/', ComprehensiveTankhahReportView.as_view(), name='comprehensive_tankhah_report')
```

### 8. مجوزهای مورد نیاز

برای دسترسی به داشبورد اجرایی، کاربر باید یکی از مجوزهای زیر را داشته باشد:
- `budgets.view_budgetallocation`
- `tankhah.view_tankhah`
- `tankhah.view_factor`
- `is_superuser`

### 9. نکات مهم

#### بهینه‌سازی عملکرد:
- استفاده از `select_related` و `prefetch_related`
- محاسبه آمار با استفاده از aggregation
- کش کردن داده‌های پرتکرار

#### مدیریت خطا:
- try-catch blocks برای تمام عملیات
- نمایش پیام‌های خطای مناسب
- fallback values برای داده‌های ناموجود

#### امنیت:
- بررسی مجوزهای دسترسی
- اعتبارسنجی ورودی‌ها
- محافظت در برابر SQL injection

### 10. فایل‌های ایجاد شده

```
core/
├── views_executive_dashboard.py      # ویوهای داشبورد اجرایی
├── urls_executive_dashboard.py       # URL patterns
├── workflow_management.py            # سیستم مدیریت قوانین
├── views_workflow_management.py      # ویوهای مدیریت قوانین
├── urls_workflow_management.py       # URL patterns قوانین
└── migrations/
    └── 0002_workflow_management_models.py

templates/core/
├── executive_dashboard.html          # تمپلیت داشبورد اجرایی
└── workflow/
    └── dashboard.html                # تمپلیت مدیریت قوانین

BudgetsSystem/view/
└── view_Dashboard.py                 # به‌روزرسانی شده با لینک‌های جدید
```

### 11. مراحل نصب

1. **اجرای migration**:
```bash
python manage.py migrate
```

2. **اضافه کردن URL patterns**:
```python
# در urls.py اصلی
urlpatterns = [
    # ... existing patterns
    path('workflow/', include('core.urls_workflow_management')),
    path('reports/', include('core.urls_executive_dashboard')),
]
```

3. **ایجاد مجوزها** (اختیاری):
```python
python manage.py create_permissions
```

### 12. تست سیستم

#### تست داشبورد اجرایی:
1. ورود به سیستم با کاربر دارای مجوز
2. دسترسی به `/reports/executive-dashboard/`
3. بررسی نمایش آمار و نمودارها
4. تست تب‌های مختلف

#### تست مدیریت قوانین:
1. دسترسی به `/workflow/dashboard/`
2. ایجاد تمپلیت جدید
3. اعمال تمپلیت به سازمان
4. تست اعتبارسنجی قوانین

این به‌روزرسانی‌ها سیستم را برای مدیرعامل و تصمیم‌گیرندگان به یک ابزار قدرتمند و جامع تبدیل می‌کند که امکان نظارت کامل بر وضعیت مالی سازمان را فراهم می‌کند.
