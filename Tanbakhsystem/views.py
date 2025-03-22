
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _

class Tanbakhsystem_DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "index.html"  # مسیر تمپلیت
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # تعریف کارت‌ها
        cards = [
            # مدیریت هزینه‌ها (Tanbakh)
            {
                "title": _("مدیریت هزینه‌ها"),
                "icon": "fas fa-cog",
                "items": [
                    {"label": _("لیست تنخواه‌ها"), "url": "tanbakh_list", "icon": "fas fa-list", "color": "info",
                     "perm": "tanbakh.Tanbakh_view"},
                    {"label": _("ایجاد تنخواه"), "url": "tanbakh_create", "icon": "fas fa-plus", "color": "success",
                     "perm": "tanbakh.Tanbakh_add"},
                    {"label": _("لیست فاکتورها"), "url": "factor_list", "icon": "fas fa-file-invoice", "color": "info",
                     "perm": "tanbakh.Factor_view"},
                    {"label": _("ایجاد فاکتور"), "url": "factor_create", "icon": "fas fa-plus", "color": "success",
                     "perm": "tanbakh.Factor_add"},
                ],
            },
            {
                "title": _("مدیریت سازمان"),
                "icon": "fas fa-cog",
                "items": [
                    {"label": _("لیست تنخواه‌ها"), "url": "tanbakh_list", "icon": "fas fa-list", "color": "info",
                     "perm": "tanbakh.Tanbakh_view"},
                    {"label": _("ایجاد تنخواه"), "url": "tanbakh_create", "icon": "fas fa-plus", "color": "success",
                     "perm": "tanbakh.Tanbakh_add"},
                    {"label": _("لیست فاکتورها"), "url": "factor_list", "icon": "fas fa-file-invoice", "color": "info",
                     "perm": "tanbakh.Factor_view"},
                    {"label": _("ایجاد فاکتور"), "url": "factor_create", "icon": "fas fa-plus", "color": "success",
                     "perm": "tanbakh.Factor_add"},
                ],
            },
            # عملیات هزینه (Approval)
            {
                "title": _("عملیات هزینه"),
                "icon": "fas fa-dollar-sign",
                "items": [
                    {"label": _("لیست تأییدات"), "url": "approval_list", "icon": "fas fa-list", "color": "info",
                     "perm": "tanbakh.Approval_view"},
                    {"label": _("ثبت تأیید"), "url": "approval_create", "icon": "fas fa-check", "color": "success",
                     "perm": "tanbakh.Approval_add"},
                ],
            },
            # مدیریت کاربران (Accounts)
            {
                "title": _("مدیریت کاربران"),
                "icon": "fas fa-users",
                "items": [
                    {"label": _("لیست کاربران"), "url": "accounts:user_list", "icon": "fas fa-list", "color": "info",
                     "perm": "accounts.view_user"},
                    {"label": _("افزودن کاربر"), "url": "accounts:user_create", "icon": "fas fa-user-plus",
                     "color": "success", "perm": "accounts.add_user"},
                    {"label": _("تغییر رمز عبور"), "url": "accounts:password_change", "icon": "fas fa-key",
                     "color": "warning", "perm": "accounts.change_user"},
                ],
            },
            # مدیریت نقش‌ها
            {
                "title": _("مدیریت نقش‌ها"),
                "icon": "fas fa-user-tag",
                "items": [
                    {"label": _("لیست نقش‌ها"), "url": "accounts:role_list", "icon": "fas fa-list", "color": "info",
                     "perm": "accounts.view_role"},
                    {"label": _("ایجاد نقش جدید"), "url": "accounts:role_create", "icon": "fas fa-plus",
                     "color": "success", "perm": "accounts.add_role"},
                ],
            },
            # مدیریت گروه‌ها
            {
                "title": _("مدیریت گروه‌ها"),
                "icon": "fas fa-users-cog",
                "items": [
                    {"label": _("لیست گروه‌ها"), "url": "accounts:group_list", "icon": "fas fa-list", "color": "info",
                     "perm": "auth.view_group"},
                    {"label": _("ایجاد گروه جدید"), "url": "accounts:group_create", "icon": "fas fa-plus",
                     "color": "success", "perm": "auth.add_group"},
                ],
            },
            # پروفایل کاربری
            {
                "title": _("پروفایل کاربری"),
                "icon": "fas fa-id-card",
                "items": [
                    {"label": _("ویرایش پروفایل"), "url": "accounts:profile_update", "icon": "fas fa-user-edit",
                     "color": "primary", "perm": "accounts.change_user"},
                    {"label": _("حذف پروفایل"), "url": "accounts:profile_delete", "icon": "fas fa-trash",
                     "color": "danger", "perm": "accounts.delete_user"},
                ],
            },
            # گزارش‌ها و لاگ‌ها
            {
                "title": _("گزارش‌ها و لاگ‌ها"),
                "icon": "fas fa-file-alt",
                "items": [
                    {"label": _("گزارش فعالیت‌ها"), "url": "accounts:audit_log_list", "icon": "fas fa-history",
                     "color": "secondary", "perm": "accounts.view_auditlog"},
                ],
            },
            # مدیریت نسخه
            {
                "title": _("مدیریت نسخه"),
                "icon": "fas fa-lock",
                "items": [
                    {"label": _("ثبت قفل جدید و نمایش وضعیت"), "url": "accounts:set_time_lock", "icon": "fas fa-lock",
                     "color": "warning", "perm": "accounts.view_timelock"},
                    {"label": _("نمایش لیست تنظیمات قفل"), "url": "accounts:timelock_list", "icon": "fas fa-list",
                     "color": "warning", "perm": "accounts.view_timelock"},
                    {"label": _("وضعیت قفل"), "url": "accounts:lock_status", "icon": "fas fa-info-circle", "color": "warning",
                     "perm": "accounts.view_timelock"},
                    {"label": _("فهرست کاربران فعال سیستم"), "url": "accounts:active_user_list", "icon": "fas fa-users",
                     "color": "warning", "perm": "accounts.view_user"},
                ],
            },
        ]

        # فیلتر کردن آیتم‌ها بر اساس پرمیشن‌ها
        filtered_cards = []
        for card in cards:
            filtered_items = [item for item in card["items"] if user.has_perm(item["perm"])]
            if filtered_items:  # فقط کارت‌هایی که حداقل یک آیتم مجاز دارند
                card["items"] = filtered_items
                filtered_cards.append(card)

        context["cards"] = filtered_cards
        return context

# class Tanbakhsystem_DashboardView(LoginRequiredMixin, TemplateView):
#     template_name = 'index.html'  # استفاده از index.html شما
#     extra_context = {'title': _('منوی مدیریت سیستم')}
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         user = self.request.user
#
#         # تعریف لینک‌ها در دسته‌بندی‌های مختلف
#         context['cards'] = {
#             'مدیریت هزینه‌ها': [
#                 {'url': 'tanbakh_list', 'label': _('لیست تنخواه‌ها'), 'perm': 'tanbakh.Tanbakh_view'},
#                 {'url': 'tanbakh_create', 'label': _('ایجاد تنخواه'), 'perm': 'tanbakh.Tanbakh_add'},
#                 {'url': 'factor_list', 'label': _('لیست فاکتورها'), 'perm': 'tanbakh.Factor_view'},
#                 {'url': 'factor_create', 'label': _('ایجاد فاکتور'), 'perm': 'tanbakh.Factor_add'},
#             ],
#
#             'عملیات هزینه': [
#                 {'url': 'approval_list', 'label': _('لیست تأییدات'), 'perm': 'tanbakh.Approval_view'},
#                 {'url': 'approval_create', 'label': _('ثبت تأیید'), 'perm': 'tanbakh.Approval_add'},
#             ],
#
#         }
#
#         # فیلتر کردن لینک‌ها بر اساس دسترسی کاربر
#         for card_title, links in context['cards'].items():
#             context['cards'][card_title] = [link for link in links if user.has_perm(link['perm'])] if links else []
#
#         return context