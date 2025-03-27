# tanbakh/templatetags/factor_tags.py
from django import template
register = template.Library()

@register.filter
def sum_items_amount(items):
    return sum(item.amount * item.quantity for item in items)