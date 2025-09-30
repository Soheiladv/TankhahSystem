# راهنمای کامل سیستم گردش کار (Workflow Management System)

## 📋 فهرست مطالب
1. [معرفی سیستم](#معرفی-سیستم)
2. [مفاهیم کلیدی](#مفاهیم-کلیدی)
3. [نحوه استفاده](#نحوه-استفاده)
4. [مدیریت تمپلیت‌ها](#مدیریت-تمپلیت‌ها)
5. [قوانین و محدودیت‌ها](#قوانین-و-محدودیت‌ها)
6. [سازمان‌های مرکزی](#سازمان‌های-مرکزی)
7. [تست و اعتبارسنجی](#تست-و-اعتبارسنجی)
8. [مشکلات رایج](#مشکلات-رایج)
9. [بهترین روش‌ها](#بهترین-روش‌ها)

---

## 🎯 معرفی سیستم

سیستم گردش کار یک سیستم پیشرفته برای مدیریت فرآیندهای تایید در سیستم بودجه‌بندی است که شامل:

- **تمپلیت‌های گردش کار**: قالب‌های از پیش تعریف شده برای فرآیندهای مختلف
- **وضعیت‌ها**: مراحل مختلف یک فرآیند (پیش‌نویس، تایید، رد)
- **اقدامات**: عملیات قابل انجام در هر مرحله
- **انتقال‌ها**: مسیرهای مجاز بین وضعیت‌ها
- **سازمان‌ها**: مراکز مختلف که قوانین خاص خود را دارند

---

## 🔧 مفاهیم کلیدی

### 1. وضعیت‌ها (Statuses)
```python
# انواع وضعیت‌ها
DRAFT = "پیش‌نویس"           # وضعیت اولیه
SUBMITTED = "ارسال شده"      # در انتظار تایید
APPROVED = "تایید شده"       # تایید شده
REJECTED = "رد شده"          # رد شده
FINAL = "نهایی"             # وضعیت نهایی
```

### 2. اقدامات (Actions)
```python
# اقدامات قابل انجام
SUBMIT = "ارسال"            # ارسال برای تایید
APPROVE = "تایید"           # تایید
REJECT = "رد"               # رد
RETURN = "برگرداندن"        # برگرداندن برای اصلاح
```

### 3. انتقال‌ها (Transitions)
```python
# مثال انتقال
{
    'from_status': 'DRAFT',
    'to_status': 'SUBMITTED',
    'action': 'SUBMIT',
    'organization': 'دفتر مرکزی',
    'entity_type': 'PAYMENTORDER'
}
```

---

## 🚀 نحوه استفاده

### 1. ایجاد تمپلیت جدید
```bash
# URL: /workflow-management/templates/create/
# مراحل:
1. انتخاب نام و توضیحات
2. انتخاب سازمان
3. انتخاب نوع موجودیت
4. تعریف وضعیت‌ها
5. تعریف اقدامات
6. تعریف انتقال‌ها
```

### 2. اعمال تمپلیت
```bash
# URL: /workflow-management/templates/{id}/apply/
# مراحل:
1. انتخاب سازمان مقصد
2. تایید اعمال
3. بررسی نتیجه
```

### 3. مدیریت قوانین
```bash
# URL: /workflow-management/templates/
# قابلیت‌ها:
- مشاهده لیست تمپلیت‌ها
- ویرایش تمپلیت‌ها
- حذف تمپلیت‌ها
- کپی تمپلیت‌ها
```

---

## 📝 مدیریت تمپلیت‌ها

### تمپلیت تایید دستور پرداخت
```python
# ساختار تمپلیت
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
    ]
}
```

---

## 🏢 قوانین و محدودیت‌ها

### 1. قوانین عمومی
- ✅ هر تمپلیت باید حداقل یک وضعیت اولیه داشته باشد
- ✅ هر تمپلیت باید حداقل یک وضعیت نهایی داشته باشد
- ✅ انتقال‌ها باید منطقی باشند
- ✅ اقدامات باید با وضعیت‌ها سازگار باشند

### 2. قوانین سازمانی
- 🏢 **دفتر مرکزی**: تاییدیه‌های نهایی
- 🏢 **شعب**: تاییدیه‌های محلی
- 🏢 **بخش مالی**: تاییدیه‌های مالی
- 🏢 **مدیریت**: تاییدیه‌های مدیریتی

### 3. محدودیت‌های دسترسی
```python
# مثال محدودیت دسترسی
def can_approve(user, organization, entity_type):
    if organization.is_central_office:
        return user.has_perm('core.central_approve')
    else:
        return user.has_perm('core.local_approve')
```

---

## 🏛️ سازمان‌های مرکزی

### تعریف سازمان مرکزی
```python
# در مدل Organization
class Organization(models.Model):
    name = models.CharField(max_length=200)
    is_central_office = models.BooleanField(default=False)
    parent_organization = models.ForeignKey('self', null=True, blank=True)
    
    def is_central(self):
        return self.is_central_office
```

### قوانین خاص مرکزی
```python
# مثال قوانین مرکزی
CENTRAL_APPROVAL_RULES = {
    'PAYMENTORDER': {
        'min_amount': 1000000,  # حداقل مبلغ برای تایید مرکزی
        'required_approvals': ['MANAGER', 'FINANCE', 'CEO'],
        'central_only': True
    },
    'FACTOR': {
        'min_amount': 500000,
        'required_approvals': ['MANAGER', 'FINANCE'],
        'central_only': False
    }
}
```

---

## 🧪 تست و اعتبارسنجی

### 1. اعتبارسنجی خودکار
```python
# بررسی سازگاری قوانین
def validate_workflow_consistency(organization, entity_type):
    issues = []
    
    # بررسی وجود وضعیت اولیه
    if not Status.objects.filter(is_initial=True).exists():
        issues.append("هیچ وضعیت اولیه‌ای تعریف نشده است")
    
    # بررسی وجود وضعیت نهایی
    if not Status.objects.filter(is_final_approve=True).exists():
        issues.append("هیچ وضعیت نهایی‌ای تعریف نشده است")
    
    return issues
```

### 2. تست تمپلیت
```python
# تست تمپلیت
def test_template(template_id):
    template = WorkflowRuleTemplate.objects.get(id=template_id)
    
    # تست ایجاد وضعیت‌ها
    for status_data in template.rules_data['statuses']:
        status = Status.objects.create(**status_data)
        assert status.is_active
    
    # تست ایجاد اقدامات
    for action_data in template.rules_data['actions']:
        action = Action.objects.create(**action_data)
        assert action.is_active
    
    # تست ایجاد انتقال‌ها
    for transition_data in template.rules_data['transitions']:
        transition = Transition.objects.create(**transition_data)
        assert transition.is_active
```

---

## ❌ مشکلات رایج

### 1. خطای HTTP 405
```bash
# مشکل: Method Not Allowed
# حل: اضافه کردن GET method به view
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
# حل: حذف فیلد organization از query
# قبل: Status.objects.filter(organization=org)
# بعد: Status.objects.filter(is_active=True)
```

### 3. خطای postaction
```bash
# مشکل: Cannot resolve keyword 'postaction'
# حل: اصلاح نام فیلد
# قبل: .exclude(postaction__isnull=False)
# بعد: .exclude(postruleassignment__isnull=False)
```

---

## 💡 بهترین روش‌ها

### 1. طراحی تمپلیت
- ✅ **ساده شروع کنید**: ابتدا یک تمپلیت ساده ایجاد کنید
- ✅ **تست کنید**: هر مرحله را تست کنید
- ✅ **مستند کنید**: تغییرات را مستند کنید
- ✅ **بک‌آپ بگیرید**: قبل از تغییرات مهم بک‌آپ بگیرید

### 2. مدیریت قوانین
- ✅ **منطقی باشید**: قوانین باید منطقی باشند
- ✅ **سازگار باشید**: قوانین باید با یکدیگر سازگار باشند
- ✅ **انعطاف‌پذیر باشید**: قوانین باید قابل تغییر باشند
- ✅ **امن باشید**: دسترسی‌ها را کنترل کنید

### 3. نگهداری سیستم
- ✅ **منظم باشید**: کد را منظم نگه دارید
- ✅ **تست کنید**: تغییرات را تست کنید
- ✅ **مستند کنید**: تغییرات را مستند کنید
- ✅ **بک‌آپ بگیرید**: بک‌آپ منظم بگیرید

---

## 🔍 بررسی کدهای هاردکد

### 1. بررسی فایل‌های مهم
```bash
# فایل‌های مهم برای بررسی
grep -r "hardcoded" core/
grep -r "if.*organization" core/
grep -r "if.*entity_type" core/
```

### 2. مثال‌های هاردکد
```python
# مثال هاردکد (بد)
if organization.name == "دفتر مرکزی":
    # کد خاص مرکزی

# مثال بهتر
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

## 📊 گزارش‌گیری

### 1. گزارش تمپلیت‌ها
```python
# آمار تمپلیت‌ها
def get_template_stats():
    return {
        'total_templates': WorkflowRuleTemplate.objects.count(),
        'active_templates': WorkflowRuleTemplate.objects.filter(is_active=True).count(),
        'public_templates': WorkflowRuleTemplate.objects.filter(is_public=True).count(),
        'by_organization': WorkflowRuleTemplate.objects.values('organization__name').annotate(count=Count('id'))
    }
```

### 2. گزارش قوانین
```python
# آمار قوانین
def get_workflow_stats(organization):
    return {
        'statuses': Status.objects.filter(is_active=True).count(),
        'actions': Action.objects.filter(is_active=True).count(),
        'transitions': Transition.objects.filter(organization=organization, is_active=True).count(),
        'post_actions': PostAction.objects.filter(is_active=True).count()
    }
```

---

## 🚀 آینده سیستم

### 1. ویژگی‌های آینده
- 🔄 **گردش کار پویا**: قوانین قابل تغییر در زمان اجرا
- 🤖 **هوش مصنوعی**: پیشنهاد قوانین بهینه
- 📱 **موبایل**: رابط موبایل
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
- ✅ ایجاد سیستم گردش کار پایه
- ✅ تمپلیت تایید دستور پرداخت
- ✅ رابط کاربری مدیریت تمپلیت‌ها
- ✅ سیستم اعمال تمپلیت‌ها

### نسخه 1.1.0 (آینده)
- 🔄 گردش کار پویا
- 🤖 هوش مصنوعی
- 📱 رابط موبایل
- 🔔 سیستم اعلان‌ها

---

**تاریخ آخرین به‌روزرسانی**: 2025-09-19  
**نسخه**: 1.0.0  
**نویسنده**: تیم توسعه سیستم بودجه‌بندی
