# مستندات جامع سیستم گردش کار (Workflow System)

## فهرست مطالب

1. [معرفی](#معرفی)
2. [معماری سیستم](#معماری-سیستم)
3. [مدل‌های اصلی](#مدل‌های-اصلی)
4. [چرخه تایید فاکتور](#چرخه-تایید-فاکتور)
5. [نحوه کار سیستم](#نحوه-کار-سیستم)
6. [ابزار تست](#ابزار-تست)
7. [مشکلات و راه‌حل‌ها](#مشکلات-و-راه‌حل‌ها)
8. [بهترین روش‌ها](#بهترین-روش‌ها)

---

## معرفی

سیستم گردش کار این پروژه یک سیستم **Transition-Based** است که بر اساس چهار مدل اصلی کار می‌کند:

- **EntityType**: نوع موجودیت‌هایی که دارای گردش کار هستند
- **Status**: وضعیت‌های ممکن برای یک موجودیت
- **Action**: اقدامات یا "فعل"هایی که کاربر می‌تواند انجام دهد
- **Transition**: قلب تپنده سیستم که این چهار بخش را به هم متصل می‌کند

### سیستم قدیمی (منسوخ شده)

سیستم قدیمی بر اساس `WorkflowStage` و `AccessRule` بود که **کاملاً منسوخ شده** و دیگر استفاده نمی‌شود.

---

## معماری سیستم

### نمودار جریان

```
┌─────────────┐
│   Entity    │ (Factor, Tankhah, PaymentOrder)
│  (DRAFT)    │
└──────┬──────┘
       │
       │ Transition (SUBMIT)
       │ allowed_posts: [کارشناس]
       ▼
┌─────────────┐
│   Status    │ (PENDING_APPROVAL)
└──────┬──────┘
       │
       │ Transition (APPROVE)
       │ allowed_posts: [مدیر واحد, مدیر مالی]
       │ (باید همه تایید کنند)
       ▼
┌─────────────┐
│   Status    │ (APPROVED)
└─────────────┘
```

### ترتیب سازمانی

سیستم بر اساس `Post.level` کار می‌کند:

- **level=1**: مدیرعامل (بالاترین سطح)
- **level=2**: معاون
- **level=3**: مدیر
- **level=4**: کارشناس ارشد
- **level=5**: کارشناس (پایین‌ترین سطح)

**نکته مهم**: هر چه `level` کمتر باشد، سطح بالاتر است.

### چرخه تایید

چرخه تایید از **پایین به بالا** انجام می‌شود:

1. کارشناس (level=5) فاکتور را ثبت می‌کند
2. کارشناس ارشد (level=4) تایید می‌کند
3. مدیر (level=3) تایید می‌کند
4. معاون (level=2) تایید می‌کند
5. مدیرعامل (level=1) تایید نهایی می‌کند

**قوانین مهم**:

- بعد از تایید خود کارشناس، دیگر نمی‌تواند تغییر دهد
- قبل از تایید کارشناس، سطوح بالاتر نمی‌توانند تایید کنند
- بعد از تایید یک سطح، دیگر نمی‌تواند تغییر دهد

---

## مدل‌های اصلی

### 1. EntityType

تعریف نوع موجودیت‌هایی که دارای گردش کار هستند:

```python
class EntityType(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)  # FACTORITEM, TANKHAH, PAYMENTORDER
    description = models.TextField(blank=True)
```

**مثال‌ها**:

- `FACTORITEM`: ردیف فاکتور
- `TANKHAH`: تنخواه
- `PAYMENTORDER`: دستور پرداخت

### 2. Status

تعریف وضعیت‌های ممکن برای یک موجودیت:

```python
class Status(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)  # DRAFT, PENDING_APPROVAL, APPROVED, REJECTED
    is_initial = models.BooleanField(default=False)  # آیا این وضعیت اولیه است؟
    is_final_approve = models.BooleanField(default=False)  # آیا این وضعیت تایید نهایی است؟
    is_final_reject = models.BooleanField(default=False)  # آیا این وضعیت رد نهایی است？
```

**وضعیت‌های استاندارد**:

- `DRAFT`: پیش‌نویس
- `PENDING_APPROVAL`: در انتظار تایید
- `APPROVED_INTERMEDIATE`: تایید میانی
- `APPROVED`: تایید نهایی
- `REJECTED`: رد شده

### 3. Action

تعریف اقدامات یا "فعل"هایی که کاربر می‌تواند انجام دهد:

```python
class Action(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)  # SUBMIT, APPROVE, REJECT, FINAL_APPROVE
    description = models.TextField(blank=True)
    display_name = models.CharField(max_length=100, blank=True)
    button_style = models.CharField(max_length=50, blank=True)  # primary, success, danger
    icon = models.CharField(max_length=50, blank=True)  # نام آیکون FontAwesome
```

**اقدامات استاندارد**:

- `SUBMIT`: ارسال برای تایید
- `APPROVE`: تایید
- `REJECT`: رد
- `FINAL_APPROVE`: تایید نهایی

### 4. Transition

قلب تپنده سیستم که این چهار بخش را به هم متصل می‌کند:

```python
class Transition(models.Model):
    name = models.CharField(max_length=255)
    entity_type = models.ForeignKey(EntityType, on_delete=models.PROTECT)
    from_status = models.ForeignKey(Status, on_delete=models.PROTECT, related_name='transitions_from')
    action = models.ForeignKey(Action, on_delete=models.PROTECT)
    to_status = models.ForeignKey(Status, on_delete=models.PROTECT, related_name='transitions_to')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    allowed_posts = models.ManyToManyField(Post)  # پست‌های مجاز برای این اقدام
    is_active = models.BooleanField(default=True)
```

**مثال Transition**:

```
نام: "ارسال فاکتور برای تایید"
entity_type: FACTORITEM
from_status: DRAFT
action: SUBMIT
to_status: PENDING_APPROVAL
allowed_posts: [کارشناس (level=5)]
```

---

## چرخه تایید فاکتور

### مرحله 1: ثبت فاکتور

کارشناس (level=5) فاکتور را در وضعیت `DRAFT` ایجاد می‌کند.

### مرحله 2: ارسال برای تایید

کارشناس با انجام اقدام `SUBMIT`، فاکتور را به وضعیت `PENDING_APPROVAL` منتقل می‌کند.

**Transition مورد نیاز**:

```python
Transition.objects.create(
    name="ارسال فاکتور برای تایید",
    entity_type=EntityType.objects.get(code='FACTORITEM'),
    from_status=Status.objects.get(code='DRAFT'),
    action=Action.objects.get(code='SUBMIT'),
    to_status=Status.objects.get(code='PENDING_APPROVAL'),
    organization=organization,
    allowed_posts=[post_level_5]  # فقط کارشناس
)
```

### مرحله 3: تایید میانی

پس از ارسال، فاکتور در وضعیت `PENDING_APPROVAL` قرار می‌گیرد. حالا باید **همه** پست‌های مجاز تایید کنند:

**Transition مورد نیاز**:

```python
Transition.objects.create(
    name="تایید فاکتور توسط مدیر واحد",
    entity_type=EntityType.objects.get(code='FACTORITEM'),
    from_status=Status.objects.get(code='PENDING_APPROVAL'),
    action=Action.objects.get(code='APPROVE'),
    to_status=Status.objects.get(code='APPROVED_INTERMEDIATE'),
    organization=organization,
    allowed_posts=[post_level_4, post_level_3]  # کارشناس ارشد و مدیر
)
```

**منطق پیشرفت**:

- سیستم بررسی می‌کند که آیا **همه** پست‌های مجاز تایید کرده‌اند؟
- اگر بله، فاکتور به وضعیت بعدی (`APPROVED_INTERMEDIATE`) منتقل می‌شود
- اگر خیر، فاکتور در وضعیت فعلی باقی می‌ماند و منتظر تایید سایر کاربران می‌ماند

### مرحله 4: تایید نهایی

پس از تایید میانی، فاکتور به وضعیت `APPROVED_INTERMEDIATE` منتقل می‌شود. حالا باید تایید نهایی انجام شود:

**Transition مورد نیاز**:

```python
Transition.objects.create(
    name="تایید نهایی فاکتور",
    entity_type=EntityType.objects.get(code='FACTORITEM'),
    from_status=Status.objects.get(code='APPROVED_INTERMEDIATE'),
    action=Action.objects.get(code='FINAL_APPROVE'),
    to_status=Status.objects.get(code='APPROVED'),
    organization=organization,
    allowed_posts=[post_level_2, post_level_1]  # معاون و مدیرعامل
)
```

### مرحله 5: رد فاکتور

در هر مرحله، اگر یک پست مجاز اقدام `REJECT` را انجام دهد، فاکتور به وضعیت `REJECTED` منتقل می‌شود:

**Transition مورد نیاز**:

```python
Transition.objects.create(
    name="رد فاکتور",
    entity_type=EntityType.objects.get(code='FACTORITEM'),
    from_status=Status.objects.get(code='PENDING_APPROVAL'),
    action=Action.objects.get(code='REJECT'),
    to_status=Status.objects.get(code='REJECTED'),
    organization=organization,
    allowed_posts=[post_level_4, post_level_3, post_level_2, post_level_1]  # همه سطوح
)
```

---

## نحوه کار سیستم

### 1. بررسی دسترسی کاربر

سیستم از تابع `get_allowed_actions_for_user` استفاده می‌کند:

```python
from core.utils_workflow import get_allowed_actions_for_user

allowed_actions = get_allowed_actions_for_user(
    user=user,
    organization=organization,
    entity_type_code='FACTORITEM',
    from_status=factor.status
)

# خروجی:
# {
#     "allowed": ["SUBMIT", "APPROVE"],
#     "blocked": []
# }
```

**منطق بررسی**:

1. دریافت پست‌های فعال کاربر
2. پیدا کردن Transition‌هایی که:
   - `from_status` = وضعیت فعلی موجودیت
   - `allowed_posts` شامل پست کاربر باشد
   - `is_active=True`
3. استخراج `action.code` از Transition‌های پیدا شده
4. اعمال `UserRuleOverride` (اگر وجود داشته باشد)

### 2. اجرای Transition

وقتی کاربر یک اقدام را انجام می‌دهد:

```python
# پیدا کردن Transition مناسب
transition = Transition.objects.get(
    organization=organization,
    entity_type=entity_type,
    from_status=current_status,
    action=action,
    is_active=True,
    allowed_posts__in=[user_post.post]
)

# ایجاد ApprovalLog
ApprovalLog.objects.create(
    factor=factor,
    user=user,
    post=user_post.post,
    action=action,
    from_status=transition.from_status,
    to_status=transition.to_status,
    comment="تایید فاکتور"
)

# بررسی پیشرفت گردش کار
_check_workflow_advancement(factor, transition)
```

### 3. بررسی پیشرفت گردش کار

سیستم بررسی می‌کند که آیا **همه** پست‌های مجاز اقدام کرده‌اند:

```python
def _check_workflow_advancement(factor, transition):
    # پیدا کردن همه Transition‌هایی که از وضعیت فعلی شروع می‌شوند
    transitions_in_status = Transition.objects.filter(
        from_status=factor.status,
        organization=factor.tankhah.organization,
        entity_type__code='FACTORITEM'
    )

    # استخراج همه پست‌های مجاز
    required_posts_pks = set()
    for trans in transitions_in_status.prefetch_related('allowed_posts'):
        for post in trans.allowed_posts.all():
            required_posts_pks.add(post.pk)

    # پیدا کردن پست‌هایی که اقدام کرده‌اند
    acted_posts_pks = set(
        ApprovalLog.objects.filter(
            factor=factor,
            stage_rule__from_status=factor.status
        ).values_list('post_id', flat=True)
    )

    # اگر همه پست‌های مجاز اقدام کرده‌اند، به وضعیت بعدی برو
    if required_posts_pks.issubset(acted_posts_pks):
        factor.status = transition.to_status
        factor.save(update_fields=['status'])
        return True

    return False
```

---

## ابزار تست

یک ابزار تست برای بررسی صحت سیستم گردش کار ایجاد شده است:

**URL**: `/tankhah/factor/approval-cycle-test/`

**قابلیت‌ها**:

1. ایجاد فاکتور تستی
2. شبیه‌سازی چرخه تایید بر اساس Transition
3. بررسی دسترسی‌ها بر اساس Post.level
4. نمایش نتایج تست

**استفاده**:

1. دسترسی به صفحه تست
2. کلیک روی "ایجاد فاکتور تستی جدید"
3. کلیک روی "شبیه‌سازی تایید" برای هر فاکتور
4. بررسی نتایج

---

## مشکلات و راه‌حل‌ها

### مشکل 1: ApprovalLog.stage_rule

در کد قدیمی، `ApprovalLog` دارای فیلد `stage_rule` بود که به `Transition` اشاره می‌کرد. اما در مدل فعلی این فیلد وجود ندارد.

**راه‌حل**: استفاده از `from_status` و `to_status` برای فیلتر کردن لاگ‌ها:

```python
# به جای:
ApprovalLog.objects.filter(stage_rule=transition)

# استفاده کنید:
ApprovalLog.objects.filter(
    factor=factor,
    from_status=transition.from_status,
    to_status=transition.to_status
)
```

### مشکل 2: بررسی پیشرفت گردش کار

سیستم باید بررسی کند که آیا **همه** پست‌های مجاز اقدام کرده‌اند، نه فقط یک پست.

**راه‌حل**: استفاده از `issubset` برای مقایسه:

```python
required_posts_pks = {post.pk for trans in transitions for post in trans.allowed_posts.all()}
acted_posts_pks = set(ApprovalLog.objects.filter(...).values_list('post_id', flat=True))

if required_posts_pks.issubset(acted_posts_pks):
    # همه تایید کرده‌اند، به وضعیت بعدی برو
```

### مشکل 3: ترتیب سازمانی

سیستم باید ترتیب سازمانی را رعایت کند: از پایین به بالا (level=5 → level=1).

**راه‌حل**: استفاده از `order_by('-level')` برای مرتب‌سازی:

```python
posts = Post.objects.filter(organization=organization).order_by('-level')
# level=5, level=4, level=3, level=2, level=1
```

---

## بهترین روش‌ها

### 1. تعریف Transition‌ها

- همیشه `is_active=True` را برای Transition‌های فعال تنظیم کنید
- `allowed_posts` را به دقت تعریف کنید
- از کدهای استاندارد برای `Status` و `Action` استفاده کنید

### 2. بررسی دسترسی

- همیشه از `get_allowed_actions_for_user` استفاده کنید
- بررسی کنید که کاربر پست فعال داشته باشد
- بررسی کنید که `Transition` فعال باشد

### 3. اجرای Transition

- همیشه از `transaction.atomic()` استفاده کنید
- `ApprovalLog` را ایجاد کنید
- وضعیت موجودیت را به‌روزرسانی کنید
- پیشرفت گردش کار را بررسی کنید

### 4. تست

- از ابزار تست استفاده کنید
- بررسی کنید که Transition‌ها درست تعریف شده‌اند
- بررسی کنید که دسترسی‌ها درست کار می‌کنند

---

## خلاصه

سیستم گردش کار این پروژه یک سیستم **Transition-Based** است که:

1. بر اساس چهار مدل اصلی کار می‌کند: `EntityType`, `Status`, `Action`, `Transition`
2. ترتیب سازمانی را رعایت می‌کند: از پایین به بالا (level=5 → level=1)
3. بررسی می‌کند که آیا **همه** پست‌های مجاز اقدام کرده‌اند
4. یک ابزار تست برای بررسی صحت سیستم دارد

**نکته مهم**: سیستم قدیمی (`WorkflowStage` و `AccessRule`) کاملاً منسوخ شده و دیگر استفاده نمی‌شود.
