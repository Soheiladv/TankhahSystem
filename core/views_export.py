import io
import json
import logging
from typing import List
from datetime import datetime

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import QuerySet
from django.http import HttpResponse, JsonResponse
from django.utils.encoding import smart_str

logger = logging.getLogger(__name__)


def _get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label=app_label, model_name=model_name)
    except Exception as e:
        logger.error(f"[EXPORT] Unable to resolve model {app_label}.{model_name}: {e}")
        return None


def _queryset_to_dicts(qs: QuerySet, fields: List[str] = None):
    if fields:
        return list(qs.values(*fields))
    return list(qs.values())


def _response_filename(base_name: str, ext: str) -> str:
    return smart_str(f"{base_name}.{ext}")


def _sanitize_rows_for_excel(rows: List[dict]) -> List[dict]:
    """Convert timezone-aware datetimes to timezone-unaware strings to satisfy Excel engines."""
    if not rows:
        return rows
    sanitized = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            # Handle datetime with tzinfo or any non-serializable types for Excel
            if isinstance(v, datetime):
                # Convert to ISO without timezone (Excel doesn't like tz-aware)
                if v.tzinfo is not None:
                    v = v.replace(tzinfo=None)
                # Keep as ISO string to avoid Excel engine tz issues
                new_row[k] = v.strftime('%Y-%m-%d %H:%M:%S')
            else:
                new_row[k] = v
        sanitized.append(new_row)
    return sanitized


@login_required
def export_api(request):
    """
    API عمومی خروجی گرفتن از هر مدل با فرمت‌های CSV/XLSX/JSON/PDF

    پارامترها (GET):
    - app: نام اپ (مثال: budgets)
    - model: نام مدل (مثال: PaymentOrder)
    - format: یکی از csv|xlsx|json|pdf (پیش‌فرض: csv)
    - filename: نام فایل خروجی بدون پسوند (اختیاری)
    - fields: لیست فیلدهای مورد نیاز (کامای جدا، اختیاری)
    - filters: JSON فیلتر ساده بر اساس فیلدها (اختیاری)
    - order_by: رشته مرتب‌سازی (اختیاری)

    نکته امنیتی: فیلترها فقط روی فیلدهای مستقیم مدل اعمال می‌شود.
    """
    app_label = request.GET.get('app')
    model_name = request.GET.get('model')
    export_format = (request.GET.get('format') or 'csv').lower()
    filename = request.GET.get('filename') or f"export-{app_label}.{model_name}"
    fields_param = request.GET.get('fields')
    order_by = request.GET.get('order_by')
    filters_param = request.GET.get('filters')

    if not app_label or not model_name:
        return JsonResponse({'error': 'app و model الزامی هستند.'}, status=400)

    model = _get_model(app_label, model_name)
    if model is None:
        return JsonResponse({'error': 'مدل یافت نشد.'}, status=404)

    # ساخت کوئری‌ست پایه
    qs = model.objects.all()

    # اعمال فیلدها
    fields = None
    if fields_param:
        fields = [f.strip() for f in fields_param.split(',') if f.strip()]

    # اعمال فیلترها (ساده و امن)
    try:
        if filters_param:
            raw_filters = json.loads(filters_param)
            safe_filters = {}
            model_fields = set(f.name for f in model._meta.fields)
            for key, value in raw_filters.items():
                if key in model_fields:
                    safe_filters[key] = value
                else:
                    logger.warning(f"[EXPORT] Ignored unsafe filter key: {key}")
            if safe_filters:
                qs = qs.filter(**safe_filters)
    except Exception as e:
        logger.error(f"[EXPORT] Invalid filters JSON: {e}")
        return JsonResponse({'error': 'ساختار filters نامعتبر است.'}, status=400)

    # اعمال مرتب‌سازی
    if order_by:
        try:
            qs = qs.order_by(order_by)
        except Exception as e:
            logger.warning(f"[EXPORT] Invalid order_by ignored: {e}")

    # تولید داده
    data_rows = _queryset_to_dicts(qs, fields)

    logger.info(
        f"[EXPORT] user={request.user.username} model={app_label}.{model_name} format={export_format} "
        f"rows={len(data_rows)} fields={fields or 'ALL'}"
    )

    # فرمت JSON
    if export_format == 'json':
        return JsonResponse(data_rows, safe=False, json_dumps_params={'ensure_ascii': False, 'cls': DjangoJSONEncoder})

    # برای CSV/XLSX مشکلات datetime timezone را sanitize کنیم
    safe_rows = _sanitize_rows_for_excel(data_rows)

    # فرمت CSV
    if export_format == 'csv':
        import csv
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=(fields or (safe_rows[0].keys() if safe_rows else [])))
        writer.writeheader()
        for row in safe_rows:
            writer.writerow(row)
        resp = HttpResponse(buf.getvalue(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f"attachment; filename={_response_filename(filename, 'csv')}"
        return resp

    # فرمت XLSX (در صورت وجود pandas و openpyxl)
    if export_format == 'xlsx':
        try:
            import pandas as pd
            df = pd.DataFrame(safe_rows)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Export')
            resp = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp['Content-Disposition'] = f"attachment; filename={_response_filename(filename, 'xlsx')}"
            return resp
        except Exception as e:
            logger.error(f"[EXPORT] XLSX export failed: {e}")
            return JsonResponse({'error': 'خروجی XLSX در دسترس نیست (pandas/openpyxl نصب شود).'}, status=500)

    # فرمت PDF (WeasyPrint در صورت نصب)
    if export_format == 'pdf':
        try:
            from django.template.loader import render_to_string
            try:
                from weasyprint import HTML
                engine = 'weasyprint'
            except Exception:
                HTML = None
                engine = None
            html = render_to_string('core/export_pdf.html', {
                'rows': data_rows,
                'fields': (fields or (list(data_rows[0].keys()) if data_rows else [])),
                'title': filename,
            })
            if engine == 'weasyprint':
                pdf_io = io.BytesIO()
                HTML(string=html).write_pdf(pdf_io)
                resp = HttpResponse(pdf_io.getvalue(), content_type='application/pdf')
                resp['Content-Disposition'] = f"attachment; filename={_response_filename(filename, 'pdf')}"
                return resp
            else:
                # Fallback: xhtml2pdf (pure Python)
                try:
                    from xhtml2pdf import pisa
                    pdf_io = io.BytesIO()
                    result = pisa.CreatePDF(src=html, dest=pdf_io, encoding='utf-8')
                    if result.err:
                        raise RuntimeError('xhtml2pdf conversion failed')
                    resp = HttpResponse(pdf_io.getvalue(), content_type='application/pdf')
                    resp['Content-Disposition'] = f"attachment; filename={_response_filename(filename, 'pdf')}"
                    return resp
                except Exception as e2:
                    logger.error(f"[EXPORT] PDF export fallback failed: {e2}")
                    return JsonResponse({'error': 'خروجی PDF در دسترس نیست (WeasyPrint/xhtml2pdf نصب شود).'}, status=500)
        except Exception as e:
            logger.error(f"[EXPORT] PDF export failed: {e}")
            return JsonResponse({'error': 'خروجی PDF در دسترس نیست (WeasyPrint/xhtml2pdf نصب شود).'}, status=500)

    return JsonResponse({'error': 'فرمت خروجی نامعتبر است.'}, status=400)


