from django.contrib.auth.models import Permission


def get_user_permissions(user):
    """
    جمع‌آوری تمام مجوزهای کاربر از نقش‌ها و مجوزهای مستقیم.
    """
    if not user.is_authenticated:
        return set()

    # لیست مجوزها
    permissions = set()

    # کاربر سوپر یوزر است؟
    if user.is_superuser:
        return set(Permission.objects.values_list('codename', flat=True))

    # مجوزهای مرتبط با نقش‌ها
    for role in user.roles.all():
        permissions.update(role.permissions.values_list('codename', flat=True))

    # مجوزهای مستقیم کاربر
    permissions.update(user.user_permissions.values_list('codename', flat=True))

    return permissions

################################################################################
from threading import current_thread
from django.contrib.auth import get_user_model
"""    کلاس برای مدیریت کاربر فعال جاری."""
class CurrentUser:
    """
    کلاس برای مدیریت کاربر فعال جاری.
    """
    @staticmethod
    def get_current_user():
        """
        دریافت کاربر لاگین‌شده فعلی از درخواست جاری.
        """
        request = getattr(current_thread(), '_request', None)
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return request.user
        return None  # یا می‌توانید یک کاربر پیش‌فرض برگردانید

    @staticmethod
    def set_user_for_model(instance, field_name='created_by'):
        """
        تنظیم کاربر فعال در فیلد مشخص‌شده مدل.
        """
        if hasattr(instance, field_name):
            current_user = CurrentUser.get_current_user()
            if current_user and getattr(instance, field_name) is None:
                setattr(instance, field_name, current_user)


################################################################################


'''
### توضیح جامع درباره تابع `get_user_permissions` و ارتباط آن با منوها

#### **1. نقش تابع `get_user_permissions` چیست؟**
این تابع وظیفه دارد که **تمام مجوزهای مرتبط با یک کاربر** را از منابع مختلف (نقش‌ها، مجوزهای مستقیم و سایر مکان‌ها) جمع‌آوری کرده و در قالب یک مجموعه (Set) بازگرداند. این مجوزها می‌توانند برای کنترل دسترسی به منوها، صفحات یا هر بخش دیگری از برنامه مورد استفاده قرار گیرند.

---

#### **2. بررسی دقیق اجزای تابع**
##### **ورودی تابع**
- ورودی تابع یک آبجکت کاربر (User) است که از درخواست (Request) ارسال می‌شود.
  
##### **منابع جمع‌آوری مجوزها**
1. **سوپر یوزر (Superuser):**
   اگر کاربر `is_superuser=True` باشد، تابع تمام مجوزهای موجود در سیستم را بازمی‌گرداند. این به معنی دسترسی کامل به تمام بخش‌ها است.

2. **نقش‌ها (Roles):**
   اگر کاربر دارای نقش‌های تعریف‌شده باشد، تابع تمام مجوزهای مرتبط با آن نقش‌ها را جمع‌آوری می‌کند.

3. **مجوزهای مستقیم کاربر (User Permissions):**
   علاوه بر نقش‌ها، ممکن است کاربر مجوزهایی به صورت مستقیم دریافت کرده باشد. این مجوزها نیز به مجموعه اضافه می‌شوند.

##### **خروجی تابع**
- خروجی یک مجموعه (`set`) از `codename`های مجوزها است. این `codename`ها برای کنترل دسترسی و تطبیق با منوها و بخش‌های مختلف سیستم استفاده می‌شوند.

---

#### **3. `codename` چیست و چرا اهمیت دارد؟**

##### **تعریف `codename`:**
`codename` یک شناسه کوتاه و یکتا برای هر مجوز در سیستم Django است. این شناسه در کدنویسی استفاده می‌شود تا بررسی مجوزها سریع‌تر و ساده‌تر باشد.

##### **ساختار `codename`:**
`codename` معمولاً از ترکیب یک عمل (مثل `add`، `change`، `delete` یا `view`) و نام مدل مربوطه تشکیل می‌شود.

##### **مثال:**
برای مدلی به نام `Post`، چهار مجوز پیش‌فرض با این `codename`ها ساخته می‌شود:
- `add_post`: ایجاد یک پست جدید.
- `change_post`: ویرایش پست موجود.
- `delete_post`: حذف پست.
- `view_post`: مشاهده پست.

---

#### **4. کاربرد `get_user_permissions` برای کنترل منوها**

##### **مراحل استفاده از تابع برای هماهنگی منوها با دسترسی‌ها:**

1. **جمع‌آوری مجوزهای کاربر:**
   با استفاده از این تابع، تمام مجوزهای کاربر به صورت مجموعه‌ای از `codename`ها جمع‌آوری می‌شود.
   ```python
   user_permissions = get_user_permissions(request.user)
   ```

2. **ارسال مجوزها به قالب:**
   مجوزها از طریق کانتکست به قالب ارسال می‌شوند.
   ```python
   return render(request, 'dashboard.html', {'user_permissions': user_permissions})
   ```

3. **نمایش یا مخفی کردن منوها در قالب:**
   در قالب می‌توانید با استفاده از شرط‌های `if` بر اساس `codename`ها، منوها را نمایش یا مخفی کنید.

##### **مثال در قالب:**
```html
<ul class="menu">
    {% if 'view_dashboard' in user_permissions %}
    <li><a href="{% url 'dashboard' %}">داشبورد</a></li>
    {% endif %}

    {% if 'edit_settings' in user_permissions %}
    <li><a href="{% url 'settings' %}">تنظیمات</a></li>
    {% endif %}
</ul>
```

---

#### **5. چطور `codename`های موجود را مشاهده کنیم؟**

##### **مشاهده تمام مجوزها در پایگاه داده**
می‌توانید از ابزارهای مدیریتی پایگاه داده (مثل Admin Django یا SQL) برای مشاهده جدول `auth_permission` استفاده کنید.

##### **مشاهده در Django Shell**
با استفاده از دستورات زیر، می‌توانید تمام مجوزها و `codename`های مرتبط را بررسی کنید:
```bash
python manage.py shell
```

```python
from django.contrib.auth.models import Permission

permissions = Permission.objects.all()
for perm in permissions:
    print(perm.codename, perm.name)
```

---

#### **6. مثال جامع: نمایش منوها بر اساس مجوز**

##### **مدل‌های نمونه (با مجوزهای سفارشی):**
مدل‌های تعریف‌شده شما، مثل `Role` و `Permission`، مجوزهای مختلفی دارند. مثلاً:
- مجوز `accounts_add_user` برای اضافه کردن کاربر.
- مجوز `accounts_view_user` برای مشاهده لیست کاربران.

##### **کد در View:**
```python
def dashboard_view(request):
    # جمع‌آوری مجوزهای کاربر
    user_permissions = get_user_permissions(request.user)

    # ارسال به قالب
    return render(request, 'dashboard.html', {
        'user_permissions': user_permissions
    })
```

##### **کد در قالب:**
```html
<ul>
    {% if 'accounts_view_user' in user_permissions %}
    <li><a href="{% url 'user_list' %}">لیست کاربران</a></li>
    {% endif %}

    {% if 'accounts_add_user' in user_permissions %}
    <li><a href="{% url 'user_create' %}">ایجاد کاربر جدید</a></li>
    {% endif %}
</ul>
```

---

#### **7. استفاده در جاوااسکریپت**
اگر منوها در سمت کلاینت و با استفاده از جاوااسکریپت مدیریت می‌شوند، می‌توانید لیست مجوزها را به صورت JSON به جاوااسکریپت ارسال کنید:
```html
<script>
    const userPermissions = {{ user_permissions|json_script:"userPermissions" }};
    console.log(userPermissions);

    if (userPermissions.includes('accounts_view_user')) {
        // نمایش منو
    }
</script>
```

---

### نتیجه‌گیری:
تابع `get_user_permissions` یک ابزار قدرتمند برای جمع‌آوری مجوزهاست. با استفاده از آن می‌توانید منوها، صفحات و حتی بخش‌های مختلف برنامه را بر اساس نقش‌ها و دسترسی‌های کاربران هماهنگ کنید. مهم‌ترین نکته، استفاده از `codename`ها به عنوان شناسه یکتا برای تطبیق مجوزها است.
'''

# ================
'''
یک helper function بنویسیم که بعد از ذخیره کاربر، همه‌ی مسیرهای دسترسیش رو لاگ کنه:
'''
def debug_user_permissions(user):
    print(f"User: {user.username}")
    print("Direct roles:", [r.name for r in user.roles.all()])
    print("Django groups:", [g.name for g in user.groups.all()])
    for g in user.groups.all():
        print(f"  Group {g.name} roles:", [r.name for r in g.roles.all()])
    print("Effective perms:", list(user.get_all_permissions()))

'''
from accounts.utils import debug_user_permissions
debug_user_permissions(u)
'''
