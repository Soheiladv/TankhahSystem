# گزارش تست و بررسی سیستم گردش کار

## تاریخ: 2024

## خلاصه

این گزارش شامل بررسی سیستم گردش کار، تست ابزار تست، و شناسایی مشکلات است.

---

## 1. بررسی سیستم گردش کار

### ✅ سیستم جدید (Transition-Based)

سیستم جدید بر اساس چهار مدل اصلی کار می‌کند:

1. **EntityType**: نوع موجودیت‌ها (FACTORITEM, TANKHAH, PAYMENTORDER)
2. **Status**: وضعیت‌ها (DRAFT, PENDING_APPROVAL, APPROVED, REJECTED)
3. **Action**: اقدامات (SUBMIT, APPROVE, REJECT, FINAL_APPROVE)
4. **Transition**: گذارها که این چهار بخش را به هم متصل می‌کند

### ✅ ترتیب سازمانی

سیستم بر اساس `Post.level` کار می‌کند:

- **level=1**: مدیرعامل (بالاترین سطح)
- **level=2**: معاون
- **level=3**: مدیر
- **level=4**: کارشناس ارشد
- **level=5**: کارشناس (پایین‌ترین سطح)

**نکته**: هر چه `level` کمتر باشد، سطح بالاتر است.

### ✅ چرخه تایید

چرخه تایید از **پایین به بالا** انجام می‌شود:

1. کارشناس (level=5) فاکتور را ثبت می‌کند
2. کارشناس ارشد (level=4) تایید می‌کند
3. مدیر (level=3) تایید می‌کند
4. معاون (level=2) تایید می‌کند
5. مدیرعامل (level=1) تایید نهایی می‌کند

---

## 2. مشکلات شناسایی شده

### ❌ مشکل 1: ApprovalLog.stage_rule

**مشکل**: در کد `view_FactorItemApprove.py` از `stage_rule=transition` استفاده می‌شود، اما در مدل `ApprovalLog` فیلد `stage_rule` وجود ندارد.

**کد مشکل‌دار**:

```python
# در view_FactorItemApprove.py خط 780
ApprovalLog.objects.create(
    ...
    stage_rule=transition  # ❌ این فیلد وجود ندارد
)

# در view_FactorItemApprove.py خط 796
ApprovalLog.objects.filter(
    factor=factor,
    stage_rule__from_status=current_status_obj  # ❌ این فیلد وجود ندارد
)
```

**راه‌حل**: باید فیلد `stage_rule` را به مدل `ApprovalLog` اضافه کنیم یا از `from_status` و `to_status` استفاده کنیم.

**راه‌حل پیشنهادی**:

```python
# اضافه کردن فیلد به ApprovalLog
stage_rule = models.ForeignKey(
    'core.Transition',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name=_("گذار گردش کار")
)

# یا استفاده از from_status و to_status
ApprovalLog.objects.filter(
    factor=factor,
    from_status=current_status_obj
)
```

### ❌ مشکل 2: get_allowed_actions_for_user خروجی

**مشکل**: در کد تست از `allowed_actions.get('allowed_actions', [])` استفاده شده، اما خروجی تابع `{"allowed": [...], "blocked": [...]}` است.

**کد مشکل‌دار**:

```python
# در views_factor_approval_test.py خط 270 (قبل از اصلاح)
if action_code and action_code in allowed_actions.get('allowed_actions', []):
    # ❌ باید 'allowed' باشد نه 'allowed_actions'
```

**راه‌حل**: ✅ اصلاح شده - استفاده از `allowed_actions.get('allowed', [])`

### ⚠️ مشکل 3: Property stage_name و stage_order

**مشکل**: در مدل `ApprovalLog` property‌های `stage_name` و `stage_order` وجود دارند که به `stage_rule` اشاره می‌کنند، اما فیلد `stage_rule` وجود ندارد.

**کد مشکل‌دار**:

```python
# در tankhah/models.py خط 1277-1281
@property
def stage_name(self):
    return self.stage_rule.name if self.stage_rule else _("وضعیت نامشخص")

@property
def stage_order(self):
    return self.stage_rule.stage_order if self.stage_rule else None
```

**راه‌حل**: باید فیلد `stage_rule` را اضافه کنیم یا این property‌ها را حذف/اصلاح کنیم.

---

## 3. تست ابزار تست

### ✅ ایجاد فاکتور تستی

ابزار تست می‌تواند فاکتور تستی ایجاد کند:

- ✅ ایجاد تنخواه تستی
- ✅ ایجاد فاکتور تستی با وضعیت DRAFT
- ✅ استفاده از Status اولیه

### ✅ شبیه‌سازی چرخه تایید

ابزار تست می‌تواند چرخه تایید را شبیه‌سازی کند:

- ✅ پیدا کردن Transition‌های ممکن از وضعیت فعلی
- ✅ بررسی دسترسی کاربران بر اساس Post.level
- ✅ ایجاد ApprovalLog
- ✅ به‌روزرسانی وضعیت فاکتور

### ⚠️ بررسی پیشرفت گردش کار

**مشکل**: در کد تست، منطق پیشرفت گردش کار کامل نیست. باید بررسی شود که آیا **همه** پست‌های مجاز اقدام کرده‌اند.

**کد فعلی**:

```python
# در views_factor_approval_test.py
# فقط یک Transition را اجرا می‌کند، اما باید بررسی کند که آیا همه پست‌های مجاز اقدام کرده‌اند
```

**راه‌حل**: باید منطق `_check_workflow_advancement` را اضافه کنیم.

---

## 4. بررسی صحت سیستم گردش کار

### ✅ تعریف Transition‌ها

سیستم می‌تواند Transition‌ها را تعریف کند:

- ✅ از وضعیت فعلی به وضعیت بعدی
- ✅ با Action مشخص
- ✅ با پست‌های مجاز مشخص

### ✅ بررسی دسترسی

سیستم می‌تواند دسترسی کاربران را بررسی کند:

- ✅ استفاده از `get_allowed_actions_for_user`
- ✅ بررسی پست‌های فعال کاربر
- ✅ بررسی Transition‌های فعال

### ⚠️ پیشرفت گردش کار

**مشکل**: منطق پیشرفت گردش کار در کد تست کامل نیست. باید بررسی شود که آیا **همه** پست‌های مجاز اقدام کرده‌اند.

**کد مورد نیاز**:

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
            from_status=factor.status
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

## 5. توصیه‌ها

### 1. اضافه کردن فیلد stage_rule به ApprovalLog

برای رفع مشکل `stage_rule`، باید فیلد را به مدل اضافه کنیم:

```python
# در tankhah/models.py
class ApprovalLog(models.Model):
    ...
    stage_rule = models.ForeignKey(
        'core.Transition',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("گذار گردش کار")
    )
```

سپس migration ایجاد کنیم:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. تکمیل منطق پیشرفت گردش کار در ابزار تست

باید منطق `_check_workflow_advancement` را به ابزار تست اضافه کنیم.

### 3. تست کامل سیستم

باید تست کامل سیستم را انجام دهیم:

1. ایجاد فاکتور تستی
2. شبیه‌سازی چرخه تایید
3. بررسی پیشرفت گردش کار
4. بررسی دسترسی‌ها

---

## 6. نتیجه‌گیری

### ✅ نقاط قوت

1. سیستم جدید (Transition-Based) به خوبی طراحی شده است
2. ترتیب سازمانی به درستی رعایت می‌شود
3. ابزار تست ایجاد شده است

### ⚠️ نقاط ضعف

1. فیلد `stage_rule` در `ApprovalLog` وجود ندارد
2. منطق پیشرفت گردش کار در ابزار تست کامل نیست
3. Property‌های `stage_name` و `stage_order` به فیلد وجود نداشته اشاره می‌کنند

### 📋 اقدامات لازم

1. ✅ اضافه کردن فیلد `stage_rule` به `ApprovalLog`
2. ✅ تکمیل منطق پیشرفت گردش کار در ابزار تست
3. ✅ تست کامل سیستم

---

## 7. مراجع

- [مستندات سیستم گردش کار](./WORKFLOW_SYSTEM_DOCUMENTATION.md)
- [مستندات منسوخ شدن سیستم قدیمی](./workflow_deprecation.md)
