from django.contrib import admin

admin.site.site_header = "مدیریت سایت"
admin.site.site_title = "پنل مدیریت"
admin.site.index_title = "داشبورد"

class MyAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('admin/css/admin_custom.css',)
        }

# مثال:
# admin.site.register(MyModel, MyAdmin)
