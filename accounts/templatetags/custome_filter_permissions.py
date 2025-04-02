from django.template import Library
register = Library()

@register.filter(name='filter_permissions')
def filter_permissions(permissions, selected_ids):
    """فیلتر برای نمایش تعداد مجوزهای انتخاب شده در هر تب"""
    if not selected_ids:
        return []
    return [p for p in permissions if str(p.id) in selected_ids]
