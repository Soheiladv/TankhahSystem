# سیستم مدیریت یکپارچه قوانین گردش کار

این سیستم برای سازماندهی، مدیریت و اعمال قوانین گردش کار در سیستم بودجه‌بندی طراحی شده است.

## ویژگی‌های اصلی

### 1. تمپلیت‌های قوانین گردش کار
- **ایجاد تمپلیت**: امکان ایجاد تمپلیت از قوانین موجود
- **کپی و استفاده مجدد**: قابلیت کپی تمپلیت‌ها برای سازمان‌های مختلف
- **مدیریت نسخه‌ها**: ردیابی تغییرات و نسخه‌های مختلف تمپلیت‌ها

### 2. سازماندهی قوانین
- **دسته‌بندی بر اساس نوع موجودیت**: فاکتور، تنخواه، دستور پرداخت، تخصیص بودجه
- **قوانین از وضعیت → اقدام → به وضعیت**: ساختار واضح و منظم
- **قوانین پست‌ها**: تعریف قوانین خاص برای هر پست سازمانی

### 3. اعتبارسنجی و کنترل کیفیت
- **اعتبارسنجی خودکار**: بررسی سازگاری قوانین
- **تشخیص تداخل**: شناسایی قوانین متضاد یا تکراری
- **گزارش‌گیری**: ارائه گزارش‌های جامع از وضعیت قوانین

## ساختار مدل‌ها

### WorkflowRuleTemplate
```python
class WorkflowRuleTemplate(models.Model):
    name = models.CharField(max_length=200)  # نام تمپلیت
    description = models.TextField()  # توضیحات
    organization = models.ForeignKey(Organization)  # سازمان
    entity_type = models.CharField(choices=ENTITY_TYPES)  # نوع موجودیت
    rules_data = models.JSONField()  # داده‌های قوانین
    is_active = models.BooleanField(default=True)  # فعال
    is_public = models.BooleanField(default=False)  # عمومی
```

### PostRuleAssignment
```python
class PostRuleAssignment(models.Model):
    post = models.ForeignKey(Post)  # پست
    rule_template = models.ForeignKey(WorkflowRuleTemplate)  # تمپلیت قانون
    entity_type = models.CharField(choices=ENTITY_TYPES)  # نوع موجودیت
    custom_settings = models.JSONField(default=dict)  # تنظیمات سفارشی
    is_active = models.BooleanField(default=True)  # فعال
```

## نحوه استفاده

### 1. راه‌اندازی اولیه
```bash
# ایجاد قوانین پیش‌فرض برای یک سازمان
python manage.py setup_workflow_rules --organization-id 1 --entity-type FACTOR

# ایجاد تمپلیت از قوانین موجود
python manage.py setup_workflow_rules --organization-id 1 --entity-type FACTOR --create-template
```

### 2. ایجاد تمپلیت از قوانین موجود
```python
from core.workflow_management import WorkflowRuleManager

# ایجاد تمپلیت
template = WorkflowRuleManager.create_rule_template_from_existing(
    organization=organization,
    entity_type='FACTOR',
    name='تمپلیت فاکتور پیش‌فرض',
    description='تمپلیت پیش‌فرض برای فاکتورها',
    user=request.user
)
```

### 3. اعمال تمپلیت به سازمان
```python
# اعمال تمپلیت به سازمان جدید
success = template.apply_to_organization(target_organization, user)
```

### 4. اعتبارسنجی قوانین
```python
# بررسی سازگاری قوانین
validation_result = WorkflowRuleManager.validate_workflow_consistency(
    organization, 'FACTOR'
)

if validation_result['is_valid']:
    print("قوانین معتبر هستند")
else:
    print("خطاها:", validation_result['errors'])
    print("هشدارها:", validation_result['warnings'])
```

### 5. دریافت خلاصه قوانین
```python
# دریافت آمار قوانین
summary = WorkflowRuleManager.get_workflow_summary(organization, 'FACTOR')
print(f"تعداد وضعیت‌ها: {summary['statuses']['total']}")
print(f"تعداد گذارها: {summary['transitions']}")
print(f"تعداد قوانین پست‌ها: {summary['post_rules']}")
```

## ساختار قوانین JSON

### وضعیت‌ها (Statuses)
```json
{
  "statuses": [
    {
      "name": "پیش‌نویس",
      "code": "DRAFT",
      "is_initial": true,
      "is_final_approve": false,
      "is_final_reject": false,
      "description": "وضعیت اولیه"
    }
  ]
}
```

### اقدامات (Actions)
```json
{
  "actions": [
    {
      "name": "تأیید",
      "code": "APPROVE",
      "description": "تأیید سند"
    }
  ]
}
```

### گذارها (Transitions)
```json
{
  "transitions": [
    {
      "name": "تأیید فاکتور",
      "from_status": "PENDING_APPROVAL",
      "action": "APPROVE",
      "to_status": "APPROVED",
      "allowed_posts": [1, 2, 3]
    }
  ]
}
```

### قوانین پست‌ها (Post Rules)
```json
{
  "post_rules": [
    {
      "post_id": 1,
      "stage_code": "PENDING_APPROVAL",
      "action_type": "APPROVE",
      "min_level": 2,
      "triggers_payment_order": false,
      "allowed_actions": ["APPROVE", "REJECT"]
    }
  ]
}
```

## URL Patterns

```python
# داشبورد
/workflow/dashboard/

# تمپلیت‌ها
/workflow/templates/
/workflow/templates/<id>/
/workflow/templates/create/

# عملیات تمپلیت‌ها
/workflow/templates/create-from-existing/
/workflow/templates/<id>/apply/

# تخصیص قوانین به پست‌ها
/workflow/post-assignments/
/workflow/post-assignments/assign/

# API endpoints
/workflow/api/validation/<org_id>/<entity_type>/
/workflow/api/summary/<org_id>/<entity_type>/
/workflow/api/export/<org_id>/<entity_type>/
```

## مجوزهای مورد نیاز

### WorkflowRuleTemplate
- `WorkflowRuleTemplate_add`: افزودن تمپلیت
- `WorkflowRuleTemplate_view`: نمایش تمپلیت
- `WorkflowRuleTemplate_update`: ویرایش تمپلیت
- `WorkflowRuleTemplate_delete`: حذف تمپلیت
- `WorkflowRuleTemplate_copy`: کپی تمپلیت

### PostRuleAssignment
- `PostRuleAssignment_add`: افزودن تخصیص
- `PostRuleAssignment_view`: نمایش تخصیص
- `PostRuleAssignment_update`: ویرایش تخصیص
- `PostRuleAssignment_delete`: حذف تخصیص

## مثال‌های کاربردی

### 1. ایجاد سیستم تأیید فاکتور
```python
# 1. ایجاد وضعیت‌ها
draft_status = Status.objects.create(
    name='پیش‌نویس',
    code='DRAFT',
    is_initial=True
)

pending_status = Status.objects.create(
    name='در انتظار تأیید',
    code='PENDING_APPROVAL'
)

approved_status = Status.objects.create(
    name='تأیید شده',
    code='APPROVED',
    is_final_approve=True
)

# 2. ایجاد اقدامات
submit_action = Action.objects.create(
    name='ارسال برای تأیید',
    code='SUBMIT'
)

approve_action = Action.objects.create(
    name='تأیید',
    code='APPROVE'
)

# 3. ایجاد گذارها
Transition.objects.create(
    name='ارسال فاکتور برای تأیید',
    entity_type=EntityType.objects.get(code='FACTOR'),
    from_status=draft_status,
    action=submit_action,
    to_status=pending_status,
    organization=organization
)

Transition.objects.create(
    name='تأیید فاکتور',
    entity_type=EntityType.objects.get(code='FACTOR'),
    from_status=pending_status,
    action=approve_action,
    to_status=approved_status,
    organization=organization
)
```

### 2. ایجاد تمپلیت و اعمال آن
```python
# ایجاد تمپلیت از قوانین موجود
template = WorkflowRuleManager.create_rule_template_from_existing(
    organization=source_organization,
    entity_type='FACTOR',
    name='تمپلیت فاکتور استاندارد',
    user=request.user
)

# اعمال تمپلیت به سازمان جدید
template.apply_to_organization(target_organization, request.user)
```

### 3. تخصیص قانون به پست
```python
# تخصیص قانون به پست
assignment = PostRuleAssignment.objects.create(
    post=post,
    rule_template=template,
    entity_type='FACTOR',
    custom_settings={
        'min_level': 3,
        'requires_approval': True
    },
    created_by=request.user
)

# دریافت قوانین مؤثر
effective_rules = assignment.get_effective_rules()
```

## نکات مهم

1. **یکتایی قوانین**: هر تمپلیت باید نام یکتا در هر سازمان داشته باشد
2. **اعتبارسنجی**: همیشه قبل از اعمال قوانین، اعتبارسنجی انجام دهید
3. **پشتیبان‌گیری**: قبل از تغییرات مهم، از قوانین پشتیبان تهیه کنید
4. **تست**: قوانین جدید را در محیط تست آزمایش کنید
5. **مستندسازی**: تغییرات قوانین را مستند کنید

## عیب‌یابی

### خطاهای رایج
1. **وضعیت اولیه تکراری**: فقط یک وضعیت اولیه مجاز است
2. **گذار تکراری**: هر ترکیب از وضعیت مبدا، اقدام و سازمان باید یکتا باشد
3. **پست غیرفعال**: نمی‌توان قانون را به پست غیرفعال تخصیص داد

### راه‌حل‌ها
```python
# بررسی وضعیت‌های اولیه
initial_statuses = Status.objects.filter(is_initial=True)
if initial_statuses.count() > 1:
    print("خطا: بیش از یک وضعیت اولیه وجود دارد")

# بررسی گذارهای تکراری
duplicate_transitions = Transition.objects.filter(
    entity_type=entity_type,
    from_status=from_status,
    action=action,
    organization=organization
)
if duplicate_transitions.count() > 1:
    print("خطا: گذار تکراری وجود دارد")
```

این سیستم به شما امکان مدیریت یکپارچه و منظم قوانین گردش کار را می‌دهد و از پراکندگی و تداخل قوانین جلوگیری می‌کند.
