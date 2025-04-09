# Tanbakhsystem/Tanbakhsystem/widgets.py
import os

from django import forms
from django.utils.safestring import mark_safe
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


# Tanbakhsystem/Tanbakhsystem/widgets.py
from django import forms
from django.utils.safestring import mark_safe

class NumberToWordsWidget(forms.TextInput):
    def __init__(self, attrs=None, word_label="به حروف:", unit="ریال"):
        self.word_label = word_label
        self.unit = unit
        default_attrs = {
            'inputmode': 'numeric',
            'class': 'form-control persian-number-input',
            'dir': 'ltr',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        # تولید ID منحصر به فرد
        input_id = attrs.get('id', f'id_{name}')
        output_id = f"{input_id}_words"

        # اضافه کردن data-output-target
        if attrs is None:
            attrs = {}
        attrs['id'] = input_id
        attrs['data-output-target'] = f"#{output_id}"

        # رندر ورودی
        input_html = super().render(name, value, attrs, renderer)

        # رندر لیبل
        label_html = (
            f'<label id="{output_id}" class="number-to-words-output">'
            f'{self.word_label} <span></span> {self.unit}</label>'
        )

        # استایل‌ها
        style_html = (
            '<style>'
            f'#{input_id} {{'
            '  width: 100%;'
            '  padding: 1px;'
            '  font-family: "Vazir", sans-serif;'
            '  font-size: 16px;'
            '  text-align: right;'
            '  flex: 1;'
            '}}'
            f'#{output_id} {{'
            '  display: block;'
            '  margin-top: 5px;'
            '  color: #666;'
            '  font-family: "Vazir", sans-serif;'
            '  font-size: 14px;'
            '  font-style: italic;'
            '}}'
            '.number-to-words-wrapper {'
            '  display: flex;'
            '  align-items: center;'
            '  gap: 10px;'
            '}'
            '</style>'
        )

        # ترکیب همه توی یه div
        return mark_safe(
            f'<div class="number-to-words-wrapper">'
            f'{input_html}{label_html}{style_html}'
            f'</div>'
        )
class NumberToWordsWidget__1(forms.TextInput):
    def __init__(self, attrs=None, word_label="به حروف:", unit="ریال"):
        self.word_label = word_label
        self.unit = unit
        default_attrs = {
            'inputmode': 'numeric',
            'class': 'form-control persian-number-input',
            'dir': 'ltr',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        # تولید ID منحصر به فرد
        input_id = attrs.get('id', f'id_{name}')
        output_id = f"{input_id}_words"

        # اضافه کردن data-output-target
        if attrs is None:
            attrs = {}
        attrs['id'] = input_id
        attrs['data-output-target'] = f"#{output_id}"

        # رندر ورودی
        input_html = super().render(name, value, attrs, renderer)

        # رندر لیبل
        label_html = (
            f'<label id="{output_id}" class="number-to-words-output">'
            f'{self.word_label} <span></span> {self.unit}</label>'
        )

        # استایل‌ها
        style_html = (
            '<style>'
            f'#{input_id} {{'
            '  width: 100%;'
            '  padding: 8px;'
            '  font-size: 16px;'
            '  text-align: right;'
            '}}'
            f'#{output_id} {{'
            '  display: block;'
            '  margin-top: 5px;'
            '  color: #666;'
            '  font-family: "Vazir", sans-serif;'
            '  font-size: 14px;'
            '  font-style: italic;'
            '}}'
            '</style>'
        )

        # جاوااسکریپت برای فرمت و تبدیل به حروف
        script_html = (
            '<script>'
            'document.addEventListener("DOMContentLoaded", function() {'
            f'const input = document.querySelector("#{input_id}");'
            f'const output = document.querySelector("#{output_id} span");'
            'if (input && output) {'
            '  if (input.value) {'
            '    input.value = NumberFormatter.separate(input.value);'
            '  }'
            '  input.addEventListener("input", function() {'
            '    let value = NumberFormatter.getRawNumber(this.value);'
            '    let words = NumberFormatter.toPersianWords(value);'
            '    output.textContent = words || "";'
            '    this.value = NumberFormatter.separate(value);'
            '  });'
            '}'
            '});'
            '</script>'
        )

        # ترکیب همه توی یه div
        return mark_safe(
            f'<div class="number-to-words-wrapper">'
            f'{input_html}<br>{label_html}{style_html}{script_html}'
            f'</div>'
        )

class NumberToWordsWidget__(forms.TextInput):
    def __init__(self, attrs=None, word_label="به حروف:", unit="ریال"):
        self.word_label = word_label
        self.unit = unit
        default_attrs = {
            'inputmode': 'numeric',
            'class': 'form-control persian-number-input',
            'dir': 'ltr',
            'style': 'text-align: right;',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        # تولید ID منحصر به فرد برای ورودی و خروجی
        input_id = attrs.get('id', f'id_{name}')
        output_id = f"{input_id}_words"

        # اضافه کردن data-output-target به attrs
        if attrs is None:
            attrs = {}
        attrs['data-output-target'] = f"#{output_id}"

        # رندر ورودی
        input_html = super().render(name, value, attrs, renderer)

        # اضافه کردن لیبل با span
        label_html = (
            f'<label id="{output_id}" class="number-to-words-output">'
            f'{self.word_label} <span></span> {self.unit}</label>'
        )

        # جاوااسکریپت برای اتصال
        script_html = (
            '<script>'
            'document.addEventListener("DOMContentLoaded", function() {'
            f'const input = document.querySelector("#{input_id}");'
            f'const output = document.querySelector("#{output_id} span");'
            'if (input && output) {'
            'input.addEventListener("input", function() {'
            'let value = NumberFormatter.getRawNumber(this.value);'
            'let words = NumberFormatter.toPersianWords(value);'
            'output.textContent = words || "";'
            '});'
            '}'
            '});'
            '</script>'
        )

        # ترکیب همه با هم
        return mark_safe(f'{input_html}<br>{label_html}{script_html}')

class NumberToWordsWidget2(forms.TextInput):
    def __init__(self, attrs=None, output_target_id="number-to-words-output"):
        default_attrs = {
            'inputmode': 'numeric',
            'class': 'form-control persian-number-input',
            'dir': 'ltr',
            'style': 'text-align: right;',
            'data-output-target': f"#{output_target_id}"  # ID لیبل خروجی
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        return mark_safe(html)  # فقط ورودی رو برگردونید

class NumberToWordsWidget1(forms.TextInput):
    # template_name = 'widgets/number_to_words.html'
    # template_name = 'tankhah/Reports/number_to_words.html'

    def __init__(self, attrs=None, word_label="به حروف:", unit="ریال"):
        self.word_label = word_label
        self.unit = unit
        default_attrs = {
            'inputmode': 'numeric',
            'class': 'form-control persian-number-input',
            'dir': 'ltr',
            'style': 'text-align: right;',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        input_id = context['widget']['attrs'].get('id', f'id_{name}')
        output_id = f"{input_id}_words"
        context['widget']['output_id'] = output_id
        context['widget']['word_label'] = self.word_label
        context['widget']['unit'] = self.unit
        context['widget']['attrs']['data-output-target'] = f"#{output_id}"

        # لاگ برای دیباگ
        logger.info(f"Template name: {self.template_name}")
        logger.info(f"DIRS: {settings.TEMPLATES[0]['DIRS']}")
        logger.info(f"Looking for file at: {os.path.join(settings.TEMPLATES[0]['DIRS'][0], self.template_name)}")
        return context
    # روش دوم: رندر مستقیم HTML و JS (اگر نخواهیم از تمپلیت استفاده کنیم)
    # def render(self, name, value, attrs=None, renderer=None):
    #     # گرفتن HTML اصلی اینپوت
    #     input_html = super().render(name, value, attrs, renderer)
    #     input_id = attrs.get('id') if attrs else f'id_{name}' # گرفتن یا ساخت ID
    #     output_id = f"{input_id}_words"

    #     # ساخت HTML برای نمایش حروف
    #     output_html = f'''
    #         <label class="form-label" for="{output_id}">{self.word_label}</label>
    #         <span id="{output_id}" class="d-block p-2 bg-light border rounded text-primary fw-bold number-to-words-output"
    #               style="min-height: 40px; direction: rtl; text-align: right;">
    #              ...
    #         </span>
    #     '''

    #     # کد JavaScript (با ID های داینامیک)
    #     # توجه: این کد JS باید کامل و بدون خطا باشد
    #     js_code = f'''
    #         <script>
    #             (function() {{
    #                 "use strict";
    #                 // ... (کدهای کامل توابع numToWords و threeDigitsToWords اینجا قرار می‌گیرند) ...

    #                 const numberInput_{input_id} = document.getElementById('{input_id}');
    #                 const wordOutput_{input_id} = document.getElementById('{output_id}');
    #                 const unit_{input_id} = "{self.unit or ''}"; // گرفتن واحد پول

    #                 if (numberInput_{input_id} && wordOutput_{input_id}) {{
    #                     numberInput_{input_id}.addEventListener('input', function() {{
    #                         const numberValue = this.value;
    #                         // ابتدا اعداد فارسی را به انگلیسی تبدیل کن (اگر لازم است)
    #                         const latinValue = numberValue.replace(/[۰-۹]/g, d => d.charCodeAt(0) - 1776);
    #                         const words = numToWords(latinValue); // تابع تبدیل را صدا بزن
    #                         if (words && words !== "عدد نامعتبر") {{
    #                              wordOutput_{input_id}.textContent = words + (unit_{input_id} ? " " + unit_{input_id} : "");
    #                              wordOutput_{input_id}.classList.remove('text-danger');
    #                              wordOutput_{input_id}.classList.add('text-primary');
    #                         }} else if (numberValue.trim() === "") {{
    #                              wordOutput_{input_id}.textContent = "...";
    #                              wordOutput_{input_id}.classList.remove('text-danger', 'text-primary');
    #                         }} else {{
    #                              wordOutput_{input_id}.textContent = words; // نمایش "عدد نامعتبر"
    #                              wordOutput_{input_id}.classList.add('text-danger');
    #                              wordOutput_{input_id}.classList.remove('text-primary');
    #                         }}
    #                     }});
    #                     // فراخوانی اولیه برای نمایش مقدار اولیه (اگر وجود دارد)
    #                      if(numberInput_{input_id}.value) {{
    #                          numberInput_{input_id}.dispatchEvent(new Event('input'));
    #                      }}
    #                 }}
    #             }})();
    #         </script>
    #     '''

    #     # ترکیب HTML ها
    #     return mark_safe(f'<div class="number-to-words-widget-container mb-3">{input_html}{output_html}{js_code}</div>')

class PersianNumberInputWidget(forms.TextInput):
    def __init__(self, attrs=None):
        default_attrs = {
            'inputmode': 'numeric',
            'class': 'form-control persian-number-only',
            'dir': 'ltr',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        input_id = attrs.get('id', f'id_{name}')
        input_html = super().render(name, value, attrs, renderer)

        script_html = (
            '<script>'
            f'document.addEventListener("DOMContentLoaded", function() {{'
            f'const input = document.querySelector("#{input_id}");'
            'if (input) {'
            '  input.addEventListener("input", function() {'
            '    let value = this.value;'
            '    // فقط اعداد پارسی رو قبول کن'
            '    value = value.replace(/[^۰-۹]/g, "");'
            '    this.value = value;'
            '    // فرمت به صورت پارسی (اختیاری)'
            '    if (value) {'
            '      let rawValue = NumberFormatter.getRawNumber(value);'
            '      this.value = NumberFormatter.separate(rawValue);'
            '    }'
            '  });'
            '  // مقدار اولیه رو فرمت کن'
            '  if (input.value) {'
            '    let rawValue = NumberFormatter.getRawNumber(input.value);'
            '    input.value = NumberFormatter.separate(rawValue);'
            '  }'
            '}'
            '});'
            '</script>'
        )

        return mark_safe(f'{input_html}{script_html}')

