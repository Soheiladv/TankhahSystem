from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django_jalali.admin.filters import JDateFieldListFilter
from core.models import Organization, OrganizationType, Project, Post, UserPost, PostHistory, WorkflowStage, \
    SystemSettings,AccessRule


# تابع کمکی برای کوتاه کردن متن
def truncate_text(text, max_length=50):
    return text[:max_length] + '...' if text and len(text) > max_length else text

# admin.site.register(OrganizationType)
# ادمین پایه با تنظیمات مشترک
class BaseAdmin(admin.ModelAdmin):
    list_per_page = 20  # تعداد آیتم‌ها در هر صفحه
    ordering = ('-id',)  # ترتیب پیش‌فرض
    search_fields = ('name',)  # فیلد جستجوی پیش‌فرض

@admin.register(OrganizationType)
class OrganizationTypeAdmin(admin.ModelAdmin):
    list_display = ('get_primary_name', 'get_secondary_name', 'is_budget_allocatable')
    search_fields = ('fname', 'org_type')
    list_filter = ('is_budget_allocatable',)

    # استفاده از fieldsets برای کنترل فرم ویرایش/افزودن
    fieldsets = (
        (None, {
            'fields': (
                # برچسب واضح تر برای fname در فرم ادمین
                ('fname',),
                # برچسب واضح تر برای org_type در فرم ادمین
                ('org_type',),
                'is_budget_allocatable',
            ),
            # می توان توضیحات کلی هم اضافه کرد
            # 'description': _("توضیح در مورد نحوه استفاده از انواع سازمان...")
        }),
    )

    # یا استفاده از فیلد 'fields' برای کنترل ساده تر
    # fields = ('fname', 'org_type', 'is_budget_allocatable')

    # اضافه کردن help_text به فیلدهای فرم (روش دیگر)
    # formfield_overrides = {
    #     models.CharField: {'widget': admin.widgets.AdminTextInputWidget(attrs={'size':'40'})},
    # }
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # تغییر برچسب ها و اضافه کردن راهنما در فرم ادمین
        if 'fname' in form.base_fields:
            form.base_fields['fname'].label = _("نام اصلی/رایج نوع سازمان")
            form.base_fields['fname'].help_text = _("مثلاً: مجتمع مسکونی، شعبه استانی، دفتر مرکزی.")
        if 'org_type' in form.base_fields:
            form.base_fields['org_type'].label = _("نام جایگزین/کد نوع سازمان (اختیاری)")
            form.base_fields['org_type'].help_text = _("در صورت نیاز به یک نام یا کد دیگر برای این نوع سازمان استفاده شود.")
        return form

    # توابع برای نمایش در list_display با نام بهتر
    @admin.display(description=_('نام اصلی نوع سازمان'))
    def get_primary_name(self, obj):
        return obj.fname or _("-")

    @admin.display(description=_('نام جایگزین/کد'))
    def get_secondary_name(self, obj):
        return obj.org_type or _("-")

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'get_org_type_display', 'parent_organization', 'is_active', 'is_core')
    list_filter = ('is_active', 'is_core', 'org_type')
    search_fields = ('code', 'name', 'description', 'org_type__fname', 'org_type__org_type')
    autocomplete_fields = ('parent_organization', 'org_type') # بهبود انتخاب والد و نوع
    ordering = ('code',)

    fieldsets = (
        (_('اطلاعات اصلی'), {'fields': ('code', 'name', 'org_type', 'is_active', 'is_core')}),
        (_('ساختار سازمانی'), {'fields': ('parent_organization',)}),
        (_('توضیحات'), {'fields': ('description',), 'classes': ('collapse',)}),
    )

    @admin.display(description=_('نوع سازمان'))
    def get_org_type_display(self, obj):
        # در ادمین هم از fname استفاده می کنیم تا با __str__ سازگار باشد
        # اما می توان بر اساس نیاز تغییر داد
        if obj.org_type:
            return obj.org_type.fname or _("نامشخص")
        return _("تعیین نشده")

# ادمین سازمان
# @admin.register(Organization)
# class OrganizationAdmin(BaseAdmin):
#     list_display = ('code', 'name', 'org_type', 'description_short', 'parent_organization')
#     list_filter = ('org_type',)
#     search_fields = ('code', 'name', 'description')
#     ordering = ('code',)
#     fieldsets = (
#         (None, {'fields': ('code', 'name', 'org_type' ,'parent_organization')}),
#         (_('توضیحات'), {'fields': ('description',), 'classes': ('collapse',)}),
#     )
#
#     def description_short(self, obj):
#         return truncate_text(obj.description)
#     description_short.short_description = _('توضیحات کوتاه')

# ادمین پروژه
@admin.register(Project)
class ProjectAdmin(BaseAdmin):
    list_display = ('code', 'name', 'start_date', 'end_date',  'org_count')
    list_filter = (('start_date', JDateFieldListFilter), ('end_date', JDateFieldListFilter))
    search_fields = ('code', 'name', 'description')
    filter_horizontal = ('organizations',)
    ordering = ('-start_date',)
    fieldsets = (
        (None, {'fields': ('code',  'name', 'organizations', 'start_date', 'end_date')}),
        (_('توضیحات'), {'fields': ('description',), 'classes': ('collapse',)}),
    )

    def org_count(self, obj):
        return obj.organizations.count()
    org_count.short_description = _('تعداد مجتمع‌ها')

# ادمین پست سازمانی
@admin.register(Post)
class PostAdmin(BaseAdmin):
    list_display = ('name', 'organization', 'parent', 'level', 'branch')
    list_filter = ('organization', 'branch', 'level')
    search_fields = ('name', 'description')
    list_select_related = ('organization', 'parent')
    autocomplete_fields = ('parent',)
    ordering = ('organization', 'level', 'name')
    fieldsets = (
        (None, {'fields': ('name', 'organization', 'parent', 'level', 'branch')}),
        (_('توضیحات'), {'fields': ('description',), 'classes': ('collapse',)}),
    )

# ادمین اتصال کاربر به پست
@admin.register(UserPost)
class UserPostAdmin(BaseAdmin):
    list_display = ('user', 'post', 'user_fullname')
    list_filter = ('post__organization', 'post__branch')
    search_fields = ('user__username', 'post__name')
    autocomplete_fields = ('user', 'post')
    ordering = ('user__username',)

    def user_fullname(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_fullname.short_description = _('نام کامل کاربر')


# ادمین تاریخچه پست
@admin.register(PostHistory)
class PostHistoryAdmin(BaseAdmin):
    list_display = ('post', 'changed_field', 'old_value_short', 'new_value_short', 'changed_at', 'changed_by')
    list_filter = (('changed_at', JDateFieldListFilter), 'changed_field', 'post__organization')
    search_fields = ('post__name', 'changed_field', 'old_value', 'new_value', 'changed_by__username')
    ordering = ('-changed_at',)
    readonly_fields = ('changed_at',)
    autocomplete_fields = ('post', 'changed_by')

    def old_value_short(self, obj):
        return truncate_text(obj.old_value)
    old_value_short.short_description = _('مقدار قبلی (کوتاه)')

    def new_value_short(self, obj):
        return truncate_text(obj.new_value)
    new_value_short.short_description = _('مقدار جدید (کوتاه)')


# ادمین مراحل گردش کار
@admin.register(WorkflowStage) # <-- اینجا نام خود کلاس مدل WorkflowStage را بدون ' ' و بدون آدرس اپلیکیشن بنویسید
class WorkflowStageAdmin(BaseAdmin):
    list_display = ('name', 'order', 'description_short')
    search_fields = ('name', 'description')
    ordering = ('order',)

    def description_short(self, obj):
        return truncate_text(obj.description)
    description_short.short_description = _('توضیحات کوتاه')

admin.site.register(SystemSettings)

@admin.register(AccessRule)
class AccessRuleAdmin(admin.ModelAdmin):
    list_display = ('organization', 'branch', 'min_level', 'stage', 'action_type', 'entity_type', 'is_active')
    list_filter = ('organization', 'branch', 'stage', 'action_type', 'entity_type')
    search_fields = ('organization__name', 'stage__name')
    autocomplete_fields = ['organization', 'stage']