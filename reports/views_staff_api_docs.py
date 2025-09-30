# reports/views_staff_api_docs.py
"""
Staff-only API Documentation View
نمایش تمامی API های سیستم برای دسترسی فقط staff
"""

from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _


class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin برای بررسی دسترسی staff"""
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def handle_no_permission(self):
        messages.error(self.request, _('شما دسترسی لازم برای مشاهده این صفحه را ندارید.'))
        return super().handle_no_permission()


class StaffAPIDocumentationView(StaffRequiredMixin, TemplateView):
    """
    نمایش مستندات کامل API های سیستم برای staff
    """
    template_name = 'reports/staff_api_documentation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # تعریف تمامی API های سیستم
        apis = {
            'reports_apis': {
                'title': 'API های گزارش‌گیری',
                'description': 'API های مربوط به گزارش‌گیری و تحلیل داده‌ها',
                'apis': [
                    {
                        'name': 'ComprehensiveBudgetReportView',
                        'class_name': 'ComprehensiveBudgetReportView',
                        'url': '/reports/comprehensive-budget/',
                        'method': 'GET',
                        'description': 'گزارش جامع بودجه با آمار تخصیص و مصرف',
                        'permissions': 'PermissionBaseView',
                        'features': [
                            'نمایش دوره‌های بودجه',
                            'آمار تخصیص و مصرف',
                            'خروجی Excel',
                            'جستجو و فیلتر',
                            'صفحه‌بندی'
                        ],
                        'template': 'reports/v2/comprehensive_report_main.html',
                        'usage': 'برای نمایش گزارش جامع بودجه در داشبورد اصلی'
                    },
                    {
                        'name': 'BudgetWarningReportView',
                        'class_name': 'BudgetWarningReportView',
                        'url': '/reports/budget/warnings/',
                        'method': 'GET',
                        'description': 'گزارش هشدارهای بودجه و وضعیت تخصیص',
                        'permissions': 'PermissionBaseView',
                        'features': [
                            'نمایش هشدارهای بودجه',
                            'فیلتر بر اساس وضعیت',
                            'خروجی HTML',
                            'جستجو و فیلتر'
                        ],
                        'template': 'budgets/reports_budgets/budget_warning_report.html',
                        'usage': 'برای نمایش هشدارهای بودجه در داشبورد'
                    },
                    {
                        'name': 'PaymentOrderReportView',
                        'class_name': 'PaymentOrderReportView',
                        'url': '/reports/report/paymentorderreport/',
                        'method': 'GET',
                        'description': 'گزارش دستورات پرداخت با جزئیات کامل',
                        'permissions': 'PermissionBaseView',
                        'features': [
                            'گزارش دستورات پرداخت',
                            'فیلتر بر اساس تاریخ',
                            'خروجی Excel',
                            'جستجو و فیلتر'
                        ],
                        'template': 'reports/PaymentOrderReport/payment_order_report.html',
                        'usage': 'برای گزارش‌گیری از دستورات پرداخت'
                    },
                    {
                        'name': 'APIOrganizationsForPeriodView',
                        'class_name': 'APIOrganizationsForPeriodView',
                        'url': '/reports/api/organizations-for-period/<int:period_pk>/',
                        'method': 'GET',
                        'description': 'دریافت سازمان‌های یک دوره بودجه',
                        'permissions': 'PermissionBaseView',
                        'features': [
                            'AJAX endpoint',
                            'فیلتر بر اساس دوره',
                            'خروجی HTML'
                        ],
                        'usage': 'برای بارگذاری سازمان‌ها در فرم‌های AJAX'
                    },
                    {
                        'name': 'BudgetItemsForOrgPeriodAPIView',
                        'class_name': 'BudgetItemsForOrgPeriodAPIView',
                        'url': '/reports/api/budget-items-for-org-period/<int:period_pk>/<int:org_pk>/',
                        'method': 'GET',
                        'description': 'دریافت سرفصل‌های بودجه برای سازمان و دوره',
                        'permissions': 'APIView (DRF)',
                        'features': [
                            'REST API endpoint',
                            'فیلتر بر اساس سازمان و دوره',
                            'خروجی JSON با HTML content'
                        ],
                        'usage': 'برای نمایش سرفصل‌های بودجه در رابط کاربری'
                    },
                    {
                        'name': 'APIFactorsForTankhahView',
                        'class_name': 'APIFactorsForTankhahView',
                        'url': '/api/factors-for-tankhah/<int:tankhah_pk>/',
                        'method': 'GET',
                        'description': 'دریافت فاکتورهای یک تنخواه',
                        'permissions': 'View (Django)',
                        'features': [
                            'AJAX endpoint',
                            'فیلتر بر اساس تنخواه',
                            'خروجی JSON'
                        ],
                        'usage': 'برای نمایش فاکتورهای مربوط به یک تنخواه'
                    },
                    {
                        'name': 'APITankhahsForAllocationView',
                        'class_name': 'APITankhahsForAllocationView',
                        'url': '/api/tankhahs-for-allocation/<int:alloc_pk>/',
                        'method': 'GET',
                        'description': 'دریافت تنخواه‌های یک تخصیص بودجه',
                        'permissions': 'View (Django)',
                        'features': [
                            'AJAX endpoint',
                            'فیلتر بر اساس تخصیص',
                            'خروجی JSON'
                        ],
                        'usage': 'برای نمایش تنخواه‌های مربوط به یک تخصیص'
                    },
                    {
                        'name': 'OrganizationAllocationsAPIView',
                        'class_name': 'OrganizationAllocationsAPIView',
                        'url': '/api/period/<int:period_pk>/organization-allocations/',
                        'method': 'GET',
                        'description': 'دریافت تخصیص‌های سازمان برای دوره',
                        'permissions': 'PermissionBaseView',
                        'features': [
                            'AJAX endpoint',
                            'فیلتر بر اساس دوره',
                            'خروجی JSON با HTML content'
                        ],
                        'usage': 'برای نمایش تخصیص‌های سازمان در رابط کاربری'
                    }
                ]
            },
            'dashboard_apis': {
                'title': 'API های داشبورد',
                'description': 'API های مربوط به داشبورد و نمایش آمار',
                'apis': [
                    {
                        'name': 'ReportsDashboardMainView',
                        'class_name': 'ReportsDashboardMainView',
                        'url': '/reports/dashboard/',
                        'method': 'GET',
                        'description': 'داشبورد اصلی گزارشات با چارت‌های تعاملی',
                        'permissions': 'PermissionBaseView',
                        'features': [
                            'چارت‌های تعاملی',
                            'آمار کلی سیستم',
                            'فیلتر بر اساس دوره',
                            'خروجی HTML'
                        ],
                        'template': 'reports/dashboard/main_dashboard.html',
                        'usage': 'برای نمایش داشبورد اصلی گزارشات'
                    },
                    {
                        'name': 'TabbedFinancialDashboardView',
                        'class_name': 'TabbedFinancialDashboardView',
                        'url': '/dashboard/',
                        'method': 'GET',
                        'description': 'داشبورد مالی با تب‌های مختلف',
                        'permissions': 'PermissionBaseView',
                        'features': [
                            'تب‌های مختلف',
                            'آمار مالی',
                            'چارت‌های پیشرفته',
                            'خروجی HTML'
                        ],
                        'template': 'BudgetsSystem/Dashboard_Project/dashboard_main.html',
                        'usage': 'برای نمایش داشبورد مالی اصلی'
                    },
                    {
                        'name': 'DashboardView',
                        'class_name': 'DashboardView',
                        'url': '/',
                        'method': 'GET',
                        'description': 'داشبورد اصلی سیستم',
                        'permissions': 'PermissionBaseView',
                        'features': [
                            'نمایش کلی سیستم',
                            'دسترسی سریع',
                            'آمار کلی',
                            'خروجی HTML'
                        ],
                        'template': 'BudgetsSystem/view/dashboard_main.html',
                        'usage': 'برای نمایش صفحه اصلی سیستم'
                    }
                ]
            },
            'budget_apis': {
                'title': 'API های بودجه',
                'description': 'API های مربوط به مدیریت بودجه و تخصیص',
                'apis': [
                    {
                        'name': 'PayeeSearchAPI',
                        'class_name': 'PayeeSearchAPI',
                        'url': '/budgets/api/payee-search/',
                        'method': 'GET',
                        'description': 'جستجوی دریافت‌کنندگان پرداخت',
                        'permissions': 'APIView (DRF)',
                        'features': [
                            'جستجوی پیشرفته',
                            'خروجی JSON',
                            'فیلتر بر اساس نام'
                        ],
                        'usage': 'برای جستجوی دریافت‌کنندگان در فرم‌های پرداخت'
                    },
                    {
                        'name': 'ProjectAllocationFreeBudgetAPI',
                        'class_name': 'ProjectAllocationFreeBudgetAPI',
                        'url': '/budgets/api/project-allocation-free-budget/<int:pk>/',
                        'method': 'GET',
                        'description': 'دریافت بودجه آزاد تخصیص پروژه',
                        'permissions': 'APIView (DRF)',
                        'features': [
                            'محاسبه بودجه آزاد',
                            'خروجی JSON',
                            'فیلتر بر اساس پروژه'
                        ],
                        'usage': 'برای نمایش بودجه قابل تخصیص'
                    },
                    {
                        'name': 'ProjectAllocationsAPI',
                        'class_name': 'ProjectAllocationsAPI',
                        'url': '/budgets/api/project-allocations/',
                        'method': 'GET',
                        'description': 'دریافت تمامی تخصیص‌های پروژه',
                        'permissions': 'APIView (DRF)',
                        'features': [
                            'لیست کامل تخصیص‌ها',
                            'خروجی JSON',
                            'فیلتر و جستجو'
                        ],
                        'usage': 'برای نمایش لیست تخصیص‌های پروژه'
                    },
                    {
                        'name': 'ProjectAllocationAPI',
                        'class_name': 'ProjectAllocationAPI',
                        'url': '/budgets/api/project-allocation/',
                        'method': 'GET',
                        'description': 'API عمومی تخصیص پروژه (DRF Generic)',
                        'permissions': 'ListAPIView (DRF)',
                        'features': [
                            'Generic API View',
                            'Serializer-based',
                            'خروجی JSON استاندارد'
                        ],
                        'usage': 'برای دسترسی استاندارد به تخصیص‌های پروژه'
                    }
                ]
            },
            'tankhah_apis': {
                'title': 'API های تنخواه',
                'description': 'API های مربوط به مدیریت تنخواه و فاکتور',
                'apis': [
                    {
                        'name': 'PerformFactorTransitionAPI',
                        'class_name': 'PerformFactorTransitionAPI',
                        'url': '/tankhah/api/factor/<int:pk>/transition/<int:transition_id>/',
                        'method': 'POST',
                        'description': 'اجرای ترنزیشن فاکتور',
                        'permissions': 'APIView (DRF)',
                        'features': [
                            'تغییر وضعیت فاکتور',
                            'اعتبارسنجی ترنزیشن',
                            'خروجی JSON'
                        ],
                        'usage': 'برای تغییر وضعیت فاکتور در workflow'
                    },
                    {
                        'name': 'ReturnExpiredBudgetAPIView',
                        'class_name': 'ReturnExpiredBudgetAPIView',
                        'url': '/tankhah/api/return-expired-budget/',
                        'method': 'POST',
                        'description': 'بازگشت بودجه منقضی شده',
                        'permissions': 'PermissionBaseView',
                        'features': [
                            'بازگشت خودکار بودجه',
                            'اعتبارسنجی تاریخ انقضا',
                            'خروجی JSON'
                        ],
                        'usage': 'برای بازگشت خودکار بودجه‌های منقضی'
                    }
                ]
            },
            'core_apis': {
                'title': 'API های هسته سیستم',
                'description': 'API های مربوط به هسته سیستم و مدیریت',
                'apis': [
                    {
                        'name': 'OrganizationChartAPIView',
                        'class_name': 'OrganizationChartAPIView',
                        'url': '/core/api/organization-chart/',
                        'method': 'GET',
                        'description': 'دریافت چارت سازمانی',
                        'permissions': 'PermissionBaseView',
                        'features': [
                            'نمایش ساختار سازمانی',
                            'خروجی JSON',
                            'فیلتر بر اساس سطح'
                        ],
                        'usage': 'برای نمایش چارت سازمانی در داشبورد'
                    },
                    {
                        'name': 'PostActiveUsersAPIView',
                        'class_name': 'PostActiveUsersAPIView',
                        'url': '/core/api/post/<int:post_id>/active-users/',
                        'method': 'GET',
                        'description': 'دریافت کاربران فعال یک پست',
                        'permissions': 'PermissionBaseView',
                        'features': [
                            'لیست کاربران فعال',
                            'فیلتر بر اساس پست',
                            'خروجی JSON'
                        ],
                        'usage': 'برای نمایش کاربران فعال در مدیریت'
                    },
                    {
                        'name': 'PostSearchAPIView',
                        'class_name': 'PostSearchAPIView',
                        'url': '/core/api/post-search/',
                        'method': 'GET',
                        'description': 'جستجوی پست‌های سازمانی',
                        'permissions': 'PermissionBaseView',
                        'features': [
                            'جستجوی پیشرفته',
                            'فیلتر بر اساس سازمان',
                            'خروجی JSON'
                        ],
                        'usage': 'برای جستجوی پست‌ها در فرم‌ها'
                    }
                ]
            },
            'notification_apis': {
                'title': 'API های اعلان‌ها',
                'description': 'API های مربوط به سیستم اعلان‌ها و اطلاع‌رسانی',
                'apis': [
                    {
                        'name': 'NotificationInboxView',
                        'class_name': 'NotificationInboxView',
                        'url': '/inbox/notifications/',
                        'method': 'GET',
                        'description': 'صندوق ورودی اعلان‌ها',
                        'permissions': 'LoginRequiredMixin',
                        'features': [
                            'نمایش اعلان‌ها',
                            'فیلتر بر اساس وضعیت',
                            'خروجی HTML',
                            'صفحه‌بندی'
                        ],
                        'template': 'notificationApp/inbox.html',
                        'usage': 'برای نمایش اعلان‌های کاربر'
                    },
                    {
                        'name': 'MarkNotificationReadView',
                        'class_name': 'MarkNotificationReadView',
                        'url': '/inbox/notifications/mark-read/<int:pk>/',
                        'method': 'POST',
                        'description': 'علامت‌گذاری اعلان به عنوان خوانده شده',
                        'permissions': 'LoginRequiredMixin',
                        'features': [
                            'تغییر وضعیت اعلان',
                            'AJAX endpoint',
                            'خروجی JSON'
                        ],
                        'usage': 'برای تغییر وضعیت اعلان‌ها'
                    }
                ]
            },
            'usb_key_apis': {
                'title': 'API های کلید USB',
                'description': 'API های مربوط به اعتبارسنجی کلید USB',
                'apis': [
                    {
                        'name': 'USBKeyValidatorView',
                        'class_name': 'USBKeyValidatorView',
                        'url': '/usb-key-validator/',
                        'method': 'GET',
                        'description': 'اعتبارسنجی کلید USB',
                        'permissions': 'LoginRequiredMixin',
                        'features': [
                            'اعتبارسنجی کلید',
                            'بررسی دسترسی',
                            'خروجی HTML',
                            'امنیت بالا'
                        ],
                        'template': 'usb_key_validator/validator.html',
                        'usage': 'برای اعتبارسنجی دسترسی USB'
                    }
                ]
            },
            'version_tracker_apis': {
                'title': 'API های ردیابی نسخه',
                'description': 'API های مربوط به ردیابی و مدیریت نسخه‌ها',
                'apis': [
                    {
                        'name': 'VersionTrackerAPI',
                        'class_name': 'VersionTrackerAPI',
                        'url': '/version_tracker/',
                        'method': 'GET',
                        'description': 'ردیابی نسخه‌های سیستم',
                        'permissions': 'StaffRequiredMixin',
                        'features': [
                            'نمایش نسخه‌ها',
                            'تاریخچه تغییرات',
                            'خروجی JSON',
                            'مقایسه نسخه‌ها'
                        ],
                        'template': 'version_tracker/version_list.html',
                        'usage': 'برای ردیابی تغییرات سیستم'
                    }
                ]
            },
            'transition_access_apis': {
                'title': 'API های دسترسی و مجوز',
                'description': 'API های مربوط به مدیریت دسترسی‌ها و مجوزها',
                'apis': [
                    {
                        'name': 'UserPermissionReportView',
                        'class_name': 'UserPermissionReportView',
                        'url': '/reports/user-permissions/',
                        'method': 'GET',
                        'description': 'گزارش دسترسی‌های کاربران',
                        'permissions': 'StaffRequiredMixin',
                        'features': [
                            'نمایش دسترسی‌های کاربر',
                            'فیلتر بر اساس کاربر',
                            'خروجی HTML'
                        ],
                        'usage': 'برای مدیریت دسترسی‌های کاربران'
                    },
                    {
                        'name': 'ToggleTransitionAccessView',
                        'class_name': 'ToggleTransitionAccessView',
                        'url': '/reports/toggle-transition-access/<int:user_id>/<int:transition_id>/',
                        'method': 'POST',
                        'description': 'تغییر دسترسی ترنزیشن کاربر',
                        'permissions': 'StaffRequiredMixin',
                        'features': [
                            'تغییر دسترسی AJAX',
                            'اعتبارسنجی دسترسی',
                            'خروجی JSON'
                        ],
                        'usage': 'برای فعال/غیرفعال کردن دسترسی ترنزیشن'
                    },
                    {
                        'name': 'TransitionAccessReportView',
                        'class_name': 'TransitionAccessReportView',
                        'url': '/reports/transition-access-report/',
                        'method': 'GET',
                        'description': 'گزارش جامع دسترسی‌های ترنزیشن',
                        'permissions': 'StaffRequiredMixin',
                        'features': [
                            'گزارش جامع دسترسی‌ها',
                            'فیلتر و جستجو',
                            'خروجی HTML'
                        ],
                        'usage': 'برای بررسی کلی دسترسی‌های سیستم'
                    },
                    {
                        'name': 'ExportUserPermissionsView',
                        'class_name': 'ExportUserPermissionsView',
                        'url': '/reports/user-permissions/<int:user_id>/export/<str:format_type>/',
                        'method': 'GET',
                        'description': 'خروجی دسترسی‌های کاربر (Excel/CSV)',
                        'permissions': 'StaffRequiredMixin',
                        'features': [
                            'خروجی Excel و CSV',
                            'فیلتر بر اساس کاربر',
                            'دانلود فایل'
                        ],
                        'usage': 'برای خروجی گرفتن از دسترسی‌های کاربر'
                    },
                    {
                        'name': 'GenerateRuleTextView',
                        'class_name': 'GenerateRuleTextView',
                        'url': '/reports/user-permissions/<int:user_id>/rule-text/',
                        'method': 'GET',
                        'description': 'تولید متن قانون برای کپی',
                        'permissions': 'StaffRequiredMixin',
                        'features': [
                            'تولید متن قانون',
                            'فرمت قابل کپی',
                            'خروجی JSON'
                        ],
                        'usage': 'برای تولید قوانین دسترسی'
                    },
                    {
                        'name': 'CopyUserPermissionsView',
                        'class_name': 'CopyUserPermissionsView',
                        'url': '/reports/user-permissions/copy/',
                        'method': 'POST',
                        'description': 'کپی دسترسی‌های یک کاربر به کاربر دیگر',
                        'permissions': 'StaffRequiredMixin',
                        'features': [
                            'کپی دسترسی‌ها',
                            'اعتبارسنجی کاربران',
                            'خروجی JSON'
                        ],
                        'usage': 'برای کپی کردن دسترسی‌ها بین کاربران'
                    },
                    {
                        'name': 'GetUserPermissionsSummaryView',
                        'class_name': 'GetUserPermissionsSummaryView',
                        'url': '/reports/user-permissions/<int:user_id>/summary/',
                        'method': 'GET',
                        'description': 'دریافت خلاصه دسترسی‌های کاربر',
                        'permissions': 'StaffRequiredMixin',
                        'features': [
                            'خلاصه دسترسی‌ها',
                            'آمار کلی',
                            'خروجی JSON'
                        ],
                        'usage': 'برای نمایش خلاصه دسترسی‌های کاربر'
                    }
                ]
            },
            'simple_apis': {
                'title': 'API های ساده',
                'description': 'API های ساده برای تست و توسعه',
                'apis': [
                    {
                        'name': 'SimpleOrganizationsAPI',
                        'class_name': 'simple_organizations_api',
                        'url': '/reports/test-api/organizations/',
                        'method': 'GET',
                        'description': 'API ساده برای دریافت سازمان‌ها',
                        'permissions': 'LoginRequiredMixin',
                        'features': [
                            'خروجی JSON ساده',
                            'برای تست',
                            'بدون پیچیدگی'
                        ],
                        'usage': 'برای تست و توسعه'
                    },
                    {
                        'name': 'SimpleProjectsAPI',
                        'class_name': 'simple_projects_api',
                        'url': '/reports/test-api/projects/',
                        'method': 'GET',
                        'description': 'API ساده برای دریافت پروژه‌ها',
                        'permissions': 'LoginRequiredMixin',
                        'features': [
                            'خروجی JSON ساده',
                            'برای تست',
                            'بدون پیچیدگی'
                        ],
                        'usage': 'برای تست و توسعه'
                    }
                ]
            }
        }
        
        # محاسبه آمار کلی
        total_apis = sum(len(category['apis']) for category in apis.values())
        total_categories = len(apis)
        
        context.update({
            'apis': apis,
            'total_apis': total_apis,
            'total_categories': total_categories,
            'page_title': 'مستندات API های سیستم',
            'page_description': 'نمایش کامل تمامی API های موجود در سیستم بودجه‌ریزی'
        })
        
        return context
