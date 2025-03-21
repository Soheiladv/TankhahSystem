from django import template

register = template.Library()

def to_persian_number(value):
    persian_digits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']
    latin_digits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    return str(value).translate(str.maketrans(''.join(latin_digits), ''.join(persian_digits)))

register.filter('to_persian_number', to_persian_number)