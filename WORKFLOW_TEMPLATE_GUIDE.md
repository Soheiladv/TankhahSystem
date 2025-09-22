# راهنمای کامل تمپلیت‌های گردش کار (Workflow Templates Guide)

## 📋 فهرست مطالب
1. [معرفی تمپلیت‌ها](#معرفی-تمپلیت‌ها)
2. [انواع تمپلیت‌ها](#انواع-تمپلیت‌ها)
3. [ایجاد تمپلیت جدید](#ایجاد-تمپلیت-جدید)
4. [مدیریت تمپلیت‌ها](#مدیریت-تمپلیت‌ها)
5. [اعمال تمپلیت‌ها](#اعمال-تمپلیت‌ها)
6. [تمپلیت تایید دستور پرداخت](#تمپلیت-تایید-دستور-پرداخت)
7. [تمپلیت‌های سازمان مرکزی](#تمپلیت‌های-سازمان-مرکزی)
8. [بهترین روش‌ها](#بهترین-روش‌ها)
9. [مشکلات رایج](#مشکلات-رایج)

---

## 🎯 معرفی تمپلیت‌ها

تمپلیت‌های گردش کار قالب‌های از پیش تعریف شده‌ای هستند که شامل:

- **وضعیت‌ها**: مراحل مختلف فرآیند
- **اقدامات**: عملیات قابل انجام
- **انتقال‌ها**: مسیرهای مجاز بین وضعیت‌ها
- **قوانین**: محدودیت‌ها و شرایط

### مزایای استفاده از تمپلیت‌ها:
- ✅ **سازگاری**: قوانین یکسان در تمام سازمان‌ها
- ✅ **سرعت**: ایجاد سریع گردش کارهای جدید
- ✅ **انعطاف**: قابل تنظیم برای نیازهای مختلف
- ✅ **نگهداری**: آسان‌تر از قوانین پراکنده

---

## 🔧 انواع تمپلیت‌ها

### 1. تمپلیت‌های عمومی
```python
# ویژگی‌ها
- is_public = True
- قابل استفاده در تمام سازمان‌ها
- مناسب برای فرآیندهای استاندارد
```

### 2. تمپلیت‌های اختصاصی
```python
# ویژگی‌ها
- is_public = False
- مخصوص یک سازمان خاص
- مناسب برای فرآیندهای منحصر به فرد
```

### 3. تمپلیت‌های سازمان مرکزی
```python
# ویژگی‌ها
- organization.is_central_office = True
- قوانین خاص مرکزی
- تاییدیه‌های نهایی
```

---

## 🚀 ایجاد تمپلیت جدید

### 1. از طریق رابط کاربری
```bash
# URL: /workflow-management/templates/create/
# مراحل:
1. ورود به سیستم
2. انتخاب "ایجاد تمپلیت جدید"
3. پر کردن فرم
4. ذخیره تمپلیت
```

### 2. از طریق کد
```python
from core.models import WorkflowRuleTemplate, Organization

# ایجاد تمپلیت
template = WorkflowRuleTemplate.objects.create(
    name='تمپلیت تایید فاکتور',
    description='تمپلیت برای فرآیند تایید فاکتورها',
    organization=organization,
    entity_type='FACTOR',
    rules_data={
        'statuses': [...],
        'actions': [...],
        'transitions': [...]
    },
    is_active=True,
    is_public=True
)
```

### 3. از تمپلیت موجود
```python
# کپی تمپلیت موجود
existing_template = WorkflowRuleTemplate.objects.get(id=1)
new_template = existing_template
new_template.pk = None
new_template.name = 'کپی ' + existing_template.name
new_template.save()
```

---

## 📝 مدیریت تمپلیت‌ها

### 1. مشاهده لیست تمپلیت‌ها
```bash
# URL: /workflow-management/templates/
# قابلیت‌ها:
- جستجو در تمپلیت‌ها
- فیلتر بر اساس سازمان
- مرتب‌سازی
- صفحه‌بندی
```

### 2. ویرایش تمپلیت
```bash
# URL: /workflow-management/templates/{id}/
# قابلیت‌ها:
- مشاهده جزئیات
- ویرایش اطلاعات
- مدیریت قوانین
- تست تمپلیت
```

### 3. حذف تمپلیت
```python
# حذف نرم (غیرفعال کردن)
template.is_active = False
template.save()

# حذف کامل
template.delete()
```

---

## 🔄 اعمال تمپلیت‌ها

### 1. اعمال به سازمان
```bash
# URL: /workflow-management/templates/{id}/apply/
# مراحل:
1. انتخاب سازمان مقصد
2. تایید اعمال
3. بررسی نتیجه
```

### 2. اعمال خودکار
```python
# اعمال خودکار هنگام ایجاد موجودیت
def apply_template_automatically(entity, organization):
    template = WorkflowRuleTemplate.objects.filter(
        organization=organization,
        entity_type=entity.__class__.__name__,
        is_active=True
    ).first()
    
    if template:
        template.apply_to_entity(entity)
```

### 3. اعمال شرطی
```python
# اعمال بر اساس شرایط
def apply_template_conditionally(entity, organization):
    if organization.is_central_office:
        template = get_central_template(entity.__class__.__name__)
    else:
        template = get_local_template(entity.__class__.__name__)
    
    if template:
        template.apply_to_entity(entity)
```

---

## 💳 تمپلیت تایید دستور پرداخت

### ساختار تمپلیت
```python
{
    'name': 'تمپلیت تایید دستور پرداخت',
    'description': 'تمپلیت کامل برای فرآیند تایید دستور پرداخت',
    'organization': 'هتل لاله سرعین',
    'entity_type': 'PAYMENTORDER',
    'statuses': [
        {'code': 'DRAFT', 'name': 'پیش‌نویس', 'is_initial': True},
        {'code': 'SUBMITTED', 'name': 'ارسال شده'},
        {'code': 'MANAGER_APPROVED', 'name': 'تایید مدیر'},
        {'code': 'FINANCE_APPROVED', 'name': 'تایید مالی'},
        {'code': 'CEO_APPROVED', 'name': 'تایید مدیرعامل', 'is_final': True},
        {'code': 'REJECTED', 'name': 'رد شده', 'is_final': True}
    ],
    'actions': [
        {'code': 'SUBMIT', 'name': 'ارسال'},
        {'code': 'APPROVE', 'name': 'تایید'},
        {'code': 'REJECT', 'name': 'رد'},
        {'code': 'RETURN', 'name': 'برگرداندن'},
        {'code': 'FINAL_APPROVE', 'name': 'تایید نهایی'}
    ],
    'transitions': [
        # مسیرهای مجاز بین وضعیت‌ها
        {'from_status': 'DRAFT', 'to_status': 'SUBMITTED', 'action': 'SUBMIT'},
        {'from_status': 'SUBMITTED', 'to_status': 'MANAGER_APPROVED', 'action': 'APPROVE'},
        {'from_status': 'SUBMITTED', 'to_status': 'REJECTED', 'action': 'REJECT'},
        {'from_status': 'SUBMITTED', 'to_status': 'DRAFT', 'action': 'RETURN'},
        {'from_status': 'MANAGER_APPROVED', 'to_status': 'FINANCE_APPROVED', 'action': 'APPROVE'},
        {'from_status': 'MANAGER_APPROVED', 'to_status': 'REJECTED', 'action': 'REJECT'},
        {'from_status': 'MANAGER_APPROVED', 'to_status': 'DRAFT', 'action': 'RETURN'},
        {'from_status': 'FINANCE_APPROVED', 'to_status': 'CEO_APPROVED', 'action': 'FINAL_APPROVE'},
        {'from_status': 'FINANCE_APPROVED', 'to_status': 'REJECTED', 'action': 'REJECT'},
        {'from_status': 'FINANCE_APPROVED', 'to_status': 'DRAFT', 'action': 'RETURN'}
    ]
}
```

### ویژگی‌های کلیدی
- 🔄 **گردش کار کامل**: از پیش‌نویس تا تایید نهایی
- 👥 **سطوح تایید**: مدیر، مالی، مدیرعامل
- ↩️ **قابلیت برگشت**: امکان برگرداندن به مرحله قبل
- ❌ **قابلیت رد**: امکان رد در هر مرحله
- 📊 **گزارش‌گیری**: امکان ردیابی وضعیت‌ها

---

## 🏛️ تمپلیت‌های سازمان مرکزی

### تعریف سازمان مرکزی
```python
class Organization(models.Model):
    name = models.CharField(max_length=200)
    is_central_office = models.BooleanField(default=False)
    parent_organization = models.ForeignKey('self', null=True, blank=True)
    
    def is_central(self):
        return self.is_central_office
```

### قوانین خاص مرکزی
```python
CENTRAL_APPROVAL_RULES = {
    'PAYMENTORDER': {
        'min_amount': 1000000,  # حداقل مبلغ برای تایید مرکزی
        'required_approvals': ['MANAGER', 'FINANCE', 'CEO'],
        'central_only': True,
        'workflow': 'CENTRAL_PAYMENT_APPROVAL'
    },
    'FACTOR': {
        'min_amount': 500000,
        'required_approvals': ['MANAGER', 'FINANCE'],
        'central_only': False,
        'workflow': 'LOCAL_FACTOR_APPROVAL'
    }
}
```

### تمپلیت مرکزی دستور پرداخت
```python
CENTRAL_PAYMENT_TEMPLATE = {
    'name': 'تمپلیت مرکزی دستور پرداخت',
    'organization': 'دفتر مرکزی',
    'entity_type': 'PAYMENTORDER',
    'is_central_specific': True,
    'rules': {
        'min_amount': 1000000,
        'max_amount': 100000000,
        'required_documents': ['INVOICE', 'CONTRACT', 'BUDGET_ALLOCATION'],
        'approval_levels': [
            {'level': 1, 'role': 'MANAGER', 'required': True},
            {'level': 2, 'role': 'FINANCE', 'required': True},
            {'level': 3, 'role': 'CEO', 'required': True}
        ]
    }
}
```

---

## 🎯 بهترین روش‌ها

### 1. طراحی تمپلیت
- ✅ **ساده شروع کنید**: ابتدا یک تمپلیت ساده ایجاد کنید
- ✅ **منطقی باشید**: قوانین باید منطقی باشند
- ✅ **تست کنید**: هر مرحله را تست کنید
- ✅ **مستند کنید**: تغییرات را مستند کنید

### 2. نام‌گذاری
```python
# نام‌گذاری مناسب
GOOD_NAMES = [
    'تمپلیت تایید دستور پرداخت',
    'تمپلیت مرکزی فاکتور',
    'تمپلیت محلی تنخواه'
]

# نام‌گذاری نامناسب
BAD_NAMES = [
    'تمپلیت 1',
    'تمپلیت جدید',
    'تمپلیت تست'
]
```

### 3. سازمان‌دهی
```python
# ساختار پیشنهادی
TEMPLATE_STRUCTURE = {
    'central_templates': {
        'payment_orders': 'تمپلیت مرکزی دستور پرداخت',
        'factors': 'تمپلیت مرکزی فاکتور',
        'tankhahs': 'تمپلیت مرکزی تنخواه'
    },
    'local_templates': {
        'payment_orders': 'تمپلیت محلی دستور پرداخت',
        'factors': 'تمپلیت محلی فاکتور',
        'tankhahs': 'تمپلیت محلی تنخواه'
    }
}
```

---

## ❌ مشکلات رایج

### 1. خطای HTTP 405
```bash
# مشکل: Method Not Allowed
# علت: View فقط POST را می‌پذیرد
# حل: اضافه کردن GET method
@login_required
def apply_template_to_organization(request, template_id):
    if request.method == 'GET':
        # نمایش فرم
    elif request.method == 'POST':
        # پردازش فرم
```

### 2. خطای فیلد organization
```bash
# مشکل: Cannot resolve keyword 'organization'
# علت: فیلد organization در مدل Status وجود ندارد
# حل: حذف فیلد organization از query
# قبل: Status.objects.filter(organization=org)
# بعد: Status.objects.filter(is_active=True)
```

### 3. خطای postaction
```bash
# مشکل: Cannot resolve keyword 'postaction'
# علت: نام فیلد اشتباه
# حل: اصلاح نام فیلد
# قبل: .exclude(postaction__isnull=False)
# بعد: .exclude(postruleassignment__isnull=False)
```

### 4. خطای object_list
```bash
# مشکل: 'ComprehensiveBudgetReportView' object has no attribute 'object_list'
# علت: object_list در get_context_data موجود نیست
# حل: ایجاد context دستی
def get_context_data(self, **kwargs):
    periods = self.get_queryset()
    context = {
        'object_list': periods,
        'is_paginated': False,
        'paginator': None,
        'page_obj': None,
    }
```

---

## 🔍 بررسی کدهای هاردکد

### 1. شناسایی هاردکدها
```bash
# جستجوی هاردکدها
grep -r "if.*organization" core/
grep -r "if.*entity_type" core/
grep -r "hardcoded" core/
```

### 2. مثال‌های هاردکد
```python
# هاردکد (بد)
if organization.name == "دفتر مرکزی":
    # کد خاص مرکزی

# پیکربندی (خوب)
if organization.is_central_office:
    # کد خاص مرکزی
```

### 3. اصلاح هاردکدها
```python
# قبل (هاردکد)
def get_approval_flow(organization_name):
    if organization_name == "دفتر مرکزی":
        return CENTRAL_FLOW
    else:
        return LOCAL_FLOW

# بعد (پیکربندی)
def get_approval_flow(organization):
    if organization.is_central_office:
        return organization.central_flow
    else:
        return organization.local_flow
```

---

## 📊 گزارش‌گیری و آمار

### 1. آمار تمپلیت‌ها
```python
def get_template_statistics():
    return {
        'total_templates': WorkflowRuleTemplate.objects.count(),
        'active_templates': WorkflowRuleTemplate.objects.filter(is_active=True).count(),
        'public_templates': WorkflowRuleTemplate.objects.filter(is_public=True).count(),
        'central_templates': WorkflowRuleTemplate.objects.filter(
            organization__is_central_office=True
        ).count(),
        'by_entity_type': WorkflowRuleTemplate.objects.values('entity_type').annotate(
            count=Count('id')
        )
    }
```

### 2. آمار استفاده
```python
def get_template_usage_stats(template_id):
    template = WorkflowRuleTemplate.objects.get(id=template_id)
    return {
        'applied_count': template.applications.count(),
        'success_rate': template.success_rate,
        'average_processing_time': template.average_processing_time,
        'most_common_errors': template.common_errors
    }
```

---

## 🚀 آینده تمپلیت‌ها

### 1. ویژگی‌های آینده
- 🤖 **هوش مصنوعی**: پیشنهاد تمپلیت‌های بهینه
- 🔄 **گردش کار پویا**: تغییر قوانین در زمان اجرا
- 📱 **موبایل**: مدیریت تمپلیت‌ها از موبایل
- 🔔 **اعلان‌ها**: اعلان‌های هوشمند

### 2. بهبودهای پیشنهادی
- ✅ **کش**: بهبود عملکرد با کش
- ✅ **API**: API کامل برای یکپارچه‌سازی
- ✅ **لاگ**: سیستم لاگ پیشرفته
- ✅ **بک‌آپ**: بک‌آپ خودکار

---

## 📞 پشتیبانی

### 1. تماس با تیم فنی
- 📧 **ایمیل**: tech@budgetsystem.com
- 📞 **تلفن**: 021-12345678
- 💬 **چت**: سیستم چت آنلاین

### 2. منابع مفید
- 📚 **مستندات**: /docs/
- 🎥 **ویدیوها**: /videos/
- ❓ **سوالات متداول**: /faq/
- 🐛 **گزارش باگ**: /bug-report/

---

## 📝 تغییرات

### نسخه 1.0.0 (2025-09-19)
- ✅ ایجاد سیستم تمپلیت‌ها
- ✅ تمپلیت تایید دستور پرداخت
- ✅ رابط کاربری مدیریت تمپلیت‌ها
- ✅ سیستم اعمال تمپلیت‌ها
- ✅ رفع مشکل گزارش جامع بودجه

### نسخه 1.1.0 (آینده)
- 🔄 تمپلیت‌های پویا
- 🤖 هوش مصنوعی
- 📱 رابط موبایل
- 🔔 سیستم اعلان‌ها

---

**تاریخ آخرین به‌روزرسانی**: 2025-09-19  
**نسخه**: 1.0.0  
**نویسنده**: تیم توسعه سیستم بودجه‌بندی
