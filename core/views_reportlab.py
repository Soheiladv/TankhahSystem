import io
import json
import logging
from datetime import datetime
from typing import List
import os

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import HttpResponse, JsonResponse
from django.utils.encoding import smart_str
from django.conf import settings

# ReportLab imports
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape, portrait
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus import PageBreak, KeepTogether
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    # Dummy classes for when ReportLab is not available
    class colors:
        lightgrey = None
        grey = None
        black = None
    class A4:
        pass
    class landscape:
        pass
    class portrait:
        pass
    class getSampleStyleSheet:
        pass
    class SimpleDocTemplate:
        pass
    class Table:
        pass
    class TableStyle:
        pass
    class Paragraph:
        pass
    class Spacer:
        pass
    class pdfmetrics:
        pass
    class TTFont:
        pass
    class RLImage:
        pass
    class PageBreak:
        pass
    class KeepTogether:
        pass

# Jalali date (optional)
try:
    import jdatetime
    HAS_JALALI = True
except Exception:
    HAS_JALALI = False

PERSIAN_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')


def _to_persian_digits(text: str) -> str:
    try:
        return str(text).translate(PERSIAN_DIGITS)
    except Exception:
        return str(text)


def _format_date(dt: datetime, persian: bool = True) -> str:
    if not dt:
        return ''
    if persian and HAS_JALALI:
        try:
            jdt = jdatetime.datetime.fromgregorian(datetime=dt)
            return _to_persian_digits(jdt.strftime('%Y/%m/%d %H:%M'))
        except Exception:
            pass
    # fallback gregorian
    return (dt.strftime('%Y/%m/%d %H:%M'))


logger = logging.getLogger(__name__)

# Optional RTL support
try:
    import arabic_reshaper
    from bidi.algorithm import get_display as bidi_get_display
    HAS_RTL = True
except Exception:
    HAS_RTL = False

# Try register Persian font
PERSIAN_FONT_NAME = 'Vazirmatn'


def _register_persian_font(explicit_path: str = None):
    try:
        # 1) explicit path (override)
        if explicit_path and os.path.exists(explicit_path):
            pdfmetrics.registerFont(TTFont(PERSIAN_FONT_NAME, explicit_path))
            logger.info(f'[RPT] Registered Persian font (explicit) from {explicit_path}')
            return True
        # 2) settings override
        settings_path = getattr(settings, 'REPORTLAB_PERSIAN_FONT', None)
        if settings_path and os.path.exists(settings_path):
            pdfmetrics.registerFont(TTFont(PERSIAN_FONT_NAME, settings_path))
            logger.info(f'[RPT] Registered Persian font (settings) from {settings_path}')
            return True
        # 3) common candidates
        base_dir = getattr(settings, 'BASE_DIR', '')
        static_root = getattr(settings, 'STATIC_ROOT', '')
        static_dirs = getattr(settings, 'STATICFILES_DIRS', []) if hasattr(settings, 'STATICFILES_DIRS') else []
        candidates = [
            os.path.join(base_dir, 'static', 'admin', 'fonts', 'Vazirmatn-Regular.ttf'),
            os.path.join(base_dir, 'static', 'fonts', 'Vazirmatn-Regular.ttf'),
            os.path.join(base_dir, 'fonts', 'Vazirmatn-Regular.ttf'),
            os.path.join(static_root, 'admin', 'fonts', 'Vazirmatn-Regular.ttf') if static_root else None,
        ]
        # add static files dirs
        for sd in static_dirs:
            candidates.append(os.path.join(sd, 'admin', 'fonts', 'Vazirmatn-Regular.ttf'))
            candidates.append(os.path.join(sd, 'fonts', 'Vazirmatn-Regular.ttf'))
        # fallback local
        candidates.append(os.path.join(os.path.dirname(__file__), 'fonts', 'Vazirmatn-Regular.ttf'))
        font_path = None
        for c in candidates:
            if c and os.path.exists(c):
                font_path = c
                break
        if not font_path:
            logger.warning('[RPT] فونت فارسی پیدا نشد; استفاده از فونت پیش فرض Helvetica')
            return False
        pdfmetrics.registerFont(TTFont(PERSIAN_FONT_NAME, font_path))
        # logger.info(f'[RPT] ثبت فونت فارسی از مسیر {font_path}')
        return True
    except Exception as e:
        # logger.error(f'[RPT] مشکل مسیر یابی در فونت: {e}')
        return False


FONT_READY = _register_persian_font()


def _shape_text(text: str) -> str:
    if not isinstance(text, str):
        text = smart_str(text)
    if HAS_RTL:
        try:
            reshaped = arabic_reshaper.reshape(text)
            return bidi_get_display(reshaped)
        except Exception:
            return text
    return text


def _get_model(app_label: str, model_name: str):
    try:
        return apps.get_model(app_label=app_label, model_name=model_name)
    except Exception as e:
        logger.error(f"[RPT] Unable to resolve model {app_label}.{model_name}: {e}")
        return None


def _qs_to_dicts(qs: QuerySet, fields: List[str] = None):
    if fields:
        return list(qs.values(*fields))
    return list(qs.values())


def _sanitize_rows(rows: List[dict]) -> List[dict]:
    if not rows:
        return rows
    out = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            if isinstance(v, datetime):
                if v.tzinfo is not None:
                    v = v.replace(tzinfo=None)
                clean[k] = v.strftime('%Y-%m-%d %H:%M:%S')
            else:
                clean[k] = v
        out.append(clean)
    return out


def _cm_to_pt(val_cm: float) -> float:
    return float(val_cm) * 28.3464567


def _load_report_settings() -> dict:
    """Load report settings (page size, margins, presets) from config/report_settings.json if present."""
    try:
        base_dir = getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
        cfg_path = os.path.join(base_dir, 'config', 'report_settings.json')
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data or {}
    except Exception as e:
        logger.warning(f"[RPT] Failed to load report_settings.json: {e}")
    return {}


def _resolve_page_setup(request, fallback_page_size: str = 'A4', fallback_landscape: bool = False) -> tuple:
    """Resolve page size (tuple in points) and margins (tuple of 4 pts) using request params and config file.

    Priority: request params > preset in config > defaults in config > fallbacks.
    """
    cfg = _load_report_settings()

    # Resolve preset if provided
    preset_name = (request.GET.get('preset') or '').strip()
    preset = cfg.get('presets', {}).get(preset_name, {}) if preset_name else {}

    # Resolve page_size string
    page_size_str = request.GET.get('page_size') or preset.get('page_size') or cfg.get('default', {}).get('page_size') or fallback_page_size

    # Resolve orientation
    landscape_param = request.GET.get('landscape')
    if landscape_param is not None:
        landscape_mode = (landscape_param.lower() == 'true')
    else:
        landscape_mode = bool(preset.get('landscape', cfg.get('default', {}).get('landscape', fallback_landscape)))

    # Resolve margins (in cm if not specified otherwise)
    margins_cfg = preset.get('margins', cfg.get('default', {}).get('margins', {}))
    top_cm = float(margins_cfg.get('top_cm', 1.5))
    right_cm = float(margins_cfg.get('right_cm', 1.5))
    bottom_cm = float(margins_cfg.get('bottom_cm', 1.5))
    left_cm = float(margins_cfg.get('left_cm', 1.5))

    margins_pt = (_cm_to_pt(left_cm), _cm_to_pt(right_cm), _cm_to_pt(top_cm), _cm_to_pt(bottom_cm))

    # Resolve page size tuple (pts)
    page_size_tuple = None
    try:
        if page_size_str:
            ps = str(page_size_str).strip()
            if ps.upper() == 'A4':
                page_size_tuple = A4
            elif 'x' in ps.lower():
                parts = ps.lower().split('x')
                if len(parts) == 2:
                    w_cm = float(parts[0])
                    h_cm = float(parts[1])
                    page_size_tuple = (_cm_to_pt(w_cm), _cm_to_pt(h_cm))
    except Exception:
        page_size_tuple = None

    if not page_size_tuple:
        page_size_tuple = A4

    if landscape_mode:
        page_size_tuple = (page_size_tuple[1], page_size_tuple[0])

    return page_size_tuple, margins_pt


def _build_pdf_table(buffer: io.BytesIO, title: str, fields: List[str], rows: List[dict], landscape_mode: bool = False,
                      footer_text: str = None, page_size: str = 'A4', margins_pt: tuple = None, request=None) -> bytes:
    # Select page size (supports 'A4' or custom like '20x28' in cm)
    if request is not None and margins_pt is None:
        page_size_tuple, margins_pt = _resolve_page_setup(request, fallback_page_size=page_size, fallback_landscape=landscape_mode)
    else:
        # Backward compatibility path
        base_size = A4
        page_size_tuple = None
        try:
            if page_size:
                ps = str(page_size).strip()
                if ps.upper() == 'A4':
                    page_size_tuple = A4
                elif 'x' in ps.lower():
                    parts = ps.lower().split('x')
                    if len(parts) == 2:
                        w_cm = float(parts[0])
                        h_cm = float(parts[1])
                        page_size_tuple = (_cm_to_pt(w_cm), _cm_to_pt(h_cm))
        except Exception:
            page_size_tuple = None
        if not page_size_tuple:
            page_size_tuple = A4
        if landscape_mode:
            page_size_tuple = (page_size_tuple[1], page_size_tuple[0])
        if margins_pt is None:
            margins_pt = (_cm_to_pt(1.5), _cm_to_pt(1.5), _cm_to_pt(1.5), _cm_to_pt(1.5))

    left_m, right_m, top_m, bottom_m = margins_pt if margins_pt else (_cm_to_pt(1.5), _cm_to_pt(1.5), _cm_to_pt(1.5), _cm_to_pt(1.5))
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size_tuple,
        title=title,
        leftMargin=left_m,
        rightMargin=right_m,
        topMargin=top_m,
        bottomMargin=bottom_m,
    )
    styles = getSampleStyleSheet()

    # Use Persian font when available
    if FONT_READY:
        styles['Normal'].fontName = PERSIAN_FONT_NAME
        styles['Heading2'].fontName = PERSIAN_FONT_NAME

    story = []
    story.append(Paragraph(_shape_text(smart_str(title or 'گزارش')), styles['Heading2']))
    story.append(Spacer(1, 12))

    # Build table data with shaping and wrapping
    # Create a compact paragraph style for table cells
    cell_style = styles['Normal']
    try:
        from reportlab.lib.styles import ParagraphStyle
        cell_style = ParagraphStyle(
            name='TableCellSmall',
            parent=styles['Normal'],
            fontName=(PERSIAN_FONT_NAME if FONT_READY else 'Helvetica'),
            fontSize=8,
            leading=10,
            alignment=2,  # RIGHT
        )
        header_style = ParagraphStyle(
            name='TableHeaderSmall',
            parent=styles['Normal'],
            fontName=(PERSIAN_FONT_NAME if FONT_READY else 'Helvetica'),
            fontSize=8.5,
            leading=11,
            alignment=2,
        )
    except Exception:
        header_style = cell_style

    header = [Paragraph(_shape_text(smart_str(f)), header_style) for f in (fields or [])]
    data = [header]
    for r in rows:
        row_cells = []
        for f in fields:
            txt = _shape_text(smart_str(r.get(f, '')))
            row_cells.append(Paragraph(txt, cell_style))
        data.append(row_cells)

    # Equal column widths to fit available doc width
    try:
        num_cols = max(1, len(fields))
        col_width = (doc.width / num_cols)
        col_widths = [col_width for _ in range(num_cols)]
    except Exception:
        col_widths = None

    tbl = Table(data, repeatRows=1, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), PERSIAN_FONT_NAME if FONT_READY else 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    story.append(tbl)
    story.append(Spacer(1, 12))

    if footer_text:
        story.append(Paragraph(_shape_text(smart_str(footer_text)), styles['Normal']))

    doc.build(story)
    return buffer.getvalue()


@login_required
def reportlab_pdf_api(request):
    """
    GET: تولید PDF از یک مدل با فیلتر/فیلدها
      params: app, model, fields (comma), filters (json), order_by, title, landscape=true|false, page_size=A4
      optional: font_path (absolute path to TTF)
    """
    if not HAS_REPORTLAB:
        return JsonResponse({'error': 'ReportLab نصب نیست. لطفاً pip install reportlab را اجرا کنید.'}, status=500)
    
    try:
        # Allow runtime font override
        font_path = request.GET.get('font_path')
        if font_path:
            _register_persian_font(font_path)

        app_label = request.GET.get('app')
        model_name = request.GET.get('model')
        if not app_label or not model_name:
            return JsonResponse({'error': 'app و model الزامی هستند.'}, status=400)

        model = _get_model(app_label, model_name)
        if model is None:
            return JsonResponse({'error': 'مدل یافت نشد.'}, status=404)

        fields_param = request.GET.get('fields')
        fields = [f.strip() for f in fields_param.split(',')] if fields_param else [f.name for f in model._meta.fields]
        filters_param = request.GET.get('filters')
        order_by = request.GET.get('order_by')
        title = request.GET.get('title') or f"گزارش {app_label}.{model_name}"
        landscape_mode = (request.GET.get('landscape', 'false').lower() == 'true')
        page_size = request.GET.get('page_size', 'A4')

        qs = model.objects.all()
        if filters_param:
            try:
                raw = json.loads(filters_param)
                safe = {}
                model_fields = set(f.name for f in model._meta.fields)
                for k, v in raw.items():
                    if k in model_fields:
                        safe[k] = v
                if safe:
                    qs = qs.filter(**safe)
            except Exception as e:
                logger.warning(f"[RPT] invalid filters ignored: {e}")
        if order_by:
            try:
                qs = qs.order_by(order_by)
            except Exception as e:
                logger.warning(f"[RPT] invalid order_by ignored: {e}")

        rows = _sanitize_rows(_qs_to_dicts(qs, fields))
        buf = io.BytesIO()
        pdf_bytes = _build_pdf_table(
            buf,
            title=title,
            fields=fields,
            rows=rows,
            landscape_mode=landscape_mode,
            footer_text=f"تاریخ تهیه: {datetime.now():%Y-%m-%d %H:%M}",
            page_size=page_size,
            request=request,
        )
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f"attachment; filename={smart_str(model_name)}.pdf"
        return resp
    except Exception as e:
        logger.error(f"[RPT] reportlab_pdf_api failed: {e}", exc_info=True)
        return JsonResponse({'error': 'خطای تولید PDF'}, status=500)


@login_required
def reportlab_pdf_custom_api(request):
    """
    POST: تولید PDF سفارشی از JSON
    body JSON example:
    {
      "title": "گزارش سفارشی",
      "fields": ["ستون۱","ستون۲"],
      "rows": [["a","b"],["c","d"]] یا [{"ستون۱":"a","ستون۲":"b"}, ...],
      "landscape": true,
      "page_size": "A4",
      "footer": "توضیحات پایانی"
    }
    """
    if not HAS_REPORTLAB:
        return JsonResponse({'error': 'ReportLab نصب نیست. لطفاً pip install reportlab را اجرا کنید.'}, status=500)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'فقط POST'}, status=405)
    try:
        payload = json.loads(request.body or '{}')
        title = payload.get('title') or 'گزارش'
        fields = payload.get('fields') or []
        rows_in = payload.get('rows') or []
        landscape_mode = bool(payload.get('landscape', False))
        page_size = payload.get('page_size', 'A4')
        footer = payload.get('footer')

        # Normalize rows: accept list of lists or list of dicts
        rows: List[dict] = []
        if rows_in and isinstance(rows_in[0], list):
            # list of lists must have fields
            for r in rows_in:
                rows.append({f: (r[idx] if idx < len(r) else '') for idx, f in enumerate(fields)})
        else:
            # assume list of dicts
            rows = [dict(r) for r in rows_in]

        rows = _sanitize_rows(rows)
        buf = io.BytesIO()
        pdf_bytes = _build_pdf_table(buf, title=title, fields=fields, rows=rows,
                                     landscape_mode=landscape_mode, footer_text=footer,
                                     page_size=page_size)
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f"attachment; filename={smart_str(title)}.pdf"
        return resp
    except Exception as e:
        logger.error(f"[RPT] reportlab_pdf_custom_api failed: {e}", exc_info=True)
        return JsonResponse({'error': 'خطای تولید PDF'}, status=500)


# ===== Detailed PaymentOrder report =====
@login_required
def reportlab_paymentorder_detail(request, pk: int):
    if not HAS_REPORTLAB:
        return JsonResponse({'error': 'ReportLab نصب نیست. لطفاً pip install reportlab را اجرا کنید.'}, status=500)
    
    try:
        # runtime font override via ?font_path=
        font_path = request.GET.get('font_path')
        if font_path:
            _register_persian_font(font_path)
        from budgets.models import PaymentOrder
        from tankhah.models import ApprovalLog
        from django.contrib.contenttypes.models import ContentType
        from core.models import EntityType, Transition

        show_factors = (request.GET.get('show_factors', 'true').lower() == 'true')
        show_logs = (request.GET.get('show_logs', 'true').lower() == 'true')
        show_images = (request.GET.get('show_images', 'false').lower() == 'true')
        image_fields_param = request.GET.get('image_fields', '')
        image_fields = [f.strip() for f in image_fields_param.split(',') if f.strip()] if image_fields_param else []
        rtl = True  # enforced
        persian_dates = True
        use_landscape = (request.GET.get('landscape', 'true').lower() == 'true')  # پیش‌فرض landscape برای دستور پرداخت

        po = PaymentOrder.objects.select_related('status', 'organization', 'created_by', 'tankhah').get(pk=pk)
        buf = io.BytesIO()

        base_size = A4
        page_size_tuple = landscape(base_size) if use_landscape else portrait(base_size)
        doc = SimpleDocTemplate(buf, pagesize=page_size_tuple, title=f'گزارش دستور پرداخت {po.order_number}',
                                rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
        styles = getSampleStyleSheet()
        if FONT_READY:
            styles['Normal'].fontName = PERSIAN_FONT_NAME
            styles['Heading2'].fontName = PERSIAN_FONT_NAME
            styles['Heading3'].fontName = PERSIAN_FONT_NAME

        story = []
        # Cover title
        story.append(Paragraph(_shape_text(f'گزارش دستور پرداخت {po.order_number}'), styles['Heading2']))
        story.append(Spacer(1, 12))

        # ========== Section: Payment Order Info ==========
        # RTL Info table key-values
        info_fields = ['تاریخ ایجاد', 'ایجادکننده', 'سازمان', 'وضعیت', 'مبلغ (ریال)', 'شماره']
        def _full_name(u):
            try:
                fn = (u.get_full_name() or '').strip()
                return fn if fn else getattr(u, 'username', '')
            except Exception:
                return getattr(u, 'username', '')
        info_values = [
            _shape_text(_format_date(po.created_at, persian=persian_dates)),
            _shape_text(_full_name(getattr(po, 'created_by', None))),
            _shape_text(getattr(po.organization, 'name', '')),
            _shape_text(getattr(po.status, 'name', '')),
            _to_persian_digits(f"{po.amount:,}"),
            _to_persian_digits(po.order_number),
        ]
        info_data = [
            [ _shape_text('مشخصات دستور پرداخت'), '' ],
            *[ [_shape_text(k), v] for k, v in zip(info_fields, info_values) ]
        ]
        # RTL column widths
        info_tbl = Table(info_data, colWidths=[doc.width*0.72, doc.width*0.28])
        info_tbl.setStyle(TableStyle([
            ('SPAN', (0,0), (-1,0)),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,-1), PERSIAN_FONT_NAME if FONT_READY else 'Helvetica'),
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
        ]))
        story.append(info_tbl)
        story.append(Spacer(1, 10))

        # ========== Section: Stakeholders ==========
        try:
            stakeholders = []
            # creator
            if getattr(po, 'created_by', None):
                stakeholders.append((_shape_text('ایجادکننده دستور'), _shape_text(_full_name(po.created_by))))
            # tankhah owner
            if getattr(po, 'tankhah', None) and getattr(po.tankhah, 'created_by', None):
                stakeholders.append((_shape_text('ایجادکننده تنخواه'), _shape_text(_full_name(po.tankhah.created_by))))
            # related factors creators
            if hasattr(po, 'related_factors'):
                creator_names = set()
                for f in po.related_factors.all():
                    u = getattr(f, 'created_by', None)
                    if u:
                        nm = _full_name(u)
                        if nm not in creator_names:
                            creator_names.add(nm)
                            stakeholders.append((_shape_text('ایجادکننده فاکتور'), _shape_text(nm)))
            # approvers/users in logs
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(po)
            for lg in ApprovalLog.objects.filter(content_type=ct, object_id=po.id).select_related('user').order_by('-timestamp'):
                u = getattr(lg, 'user', None)
                if u:
                    nm = _full_name(u)
                    stakeholders.append((_shape_text('کاربر اقدام‌کننده'), _shape_text(nm)))
            if stakeholders:
                story.append(Paragraph(_shape_text('ذینفعان مرتبط'), styles['Heading3']))
                story.append(Spacer(1, 6))
                # RTL column order: نام, نقش
                st_data = [[_shape_text('نام'), _shape_text('نقش')]] + [[v, k] for k, v in stakeholders]
                st_tbl = Table(st_data, colWidths=[doc.width*0.70, doc.width*0.30])
                st_tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, -1), PERSIAN_FONT_NAME if FONT_READY else 'Helvetica'),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ]))
                story.append(st_tbl)
                story.append(Spacer(1, 12))
        except Exception as e:
            logger.warning(f"[RPT] stakeholders section skipped: {e}")

        # ========== Section: Required Approvers (Based on Workflow) ==========
        try:
            from django.contrib.contenttypes.models import ContentType
            from core.models import EntityType, Transition, Post, UserPost
            
            # Get EntityType for PaymentOrder
            ct = ContentType.objects.get_for_model(po)
            entity_type = EntityType.objects.filter(content_type=ct).first() or EntityType.objects.filter(code='PAYMENTORDER').first()
            
            if entity_type:
                # Get all active transitions for current status
                transitions = Transition.objects.filter(
                    entity_type=entity_type,
                    from_status=po.status,
                    organization=po.organization,
                    is_active=True
                ).prefetch_related('allowed_posts', 'action', 'to_status')
                
                required_approvers = []
                for transition in transitions:
                    for post in transition.allowed_posts.all():
                        # Get users with this post in the same organization
                        user_posts = UserPost.objects.filter(
                            post=post,
                            organization=po.organization,
                            is_active=True
                        ).select_related('user')
                        
                        for user_post in user_posts:
                            user = user_post.user
                            # Check if this user has already approved
                            has_approved = ApprovalLog.objects.filter(
                                content_type=ct,
                                object_id=po.id,
                                user=user,
                                action__in=['APPROVE', 'REJECT']
                            ).exists()
                            
                            required_approvers.append({
                                'post_name': post.name,
                                'user_name': _full_name(user),
                                'username': user.username,
                                'has_approved': has_approved,
                                'action_type': transition.action.name if transition.action else 'نامشخص',
                                'to_status': transition.to_status.name if transition.to_status else 'نامشخص'
                            })
                
                if required_approvers:
                    story.append(Paragraph(_shape_text('تاییدکنندگان مورد نیاز (بر اساس گردش کار)'), styles['Heading3']))
                    story.append(Spacer(1, 6))
                    
                    # RTL table data
                    approver_data = [[
                        _shape_text('وضعیت بعدی'),
                        _shape_text('نوع اقدام'),
                        _shape_text('وضعیت تایید'),
                        _shape_text('نام کاربر'),
                        _shape_text('پست')
                    ]]
                    
                    for approver in required_approvers:
                        status_text = _shape_text('تایید شده' if approver['has_approved'] else 'در انتظار تایید')
                        approver_data.append([
                            _shape_text(approver['to_status']),      # وضعیت بعدی
                            _shape_text(approver['action_type']),    # نوع اقدام
                            status_text,                             # وضعیت تایید
                            _shape_text(approver['user_name']),      # نام کاربر
                            _shape_text(approver['post_name'])       # پست
                        ])
                    
                    # RTL column widths
                    approver_tbl = Table(approver_data, colWidths=[
                        doc.width*0.20,  # وضعیت بعدی
                        doc.width*0.20,  # نوع اقدام
                        doc.width*0.15,  # وضعیت تایید
                        doc.width*0.25,  # نام کاربر
                        doc.width*0.20   # پست
                    ])
                    approver_tbl.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                        ('FONTNAME', (0, 0), (-1, -1), PERSIAN_FONT_NAME if FONT_READY else 'Helvetica'),
                        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    story.append(approver_tbl)
                    story.append(Spacer(1, 12))
                    
        except Exception as e:
            logger.warning(f"[RPT] required approvers section skipped: {e}")

        # ========== Section: Signature & Approvers ==========
        try:
            # Resolve entity type for PAYMENTORDER
            et = EntityType.objects.filter(code='PAYMENTORDER').first()
            if not et:
                ct_po = ContentType.objects.get_for_model(po)
                et = EntityType.objects.filter(content_type=ct_po).first()
            approver_posts = {}
            if et:
                tr_qs = Transition.objects.filter(
                    entity_type=et,
                    from_status=po.status,
                    organization=po.organization,
                    is_active=True,
                ).prefetch_related('allowed_posts')
                for tr in tr_qs:
                    for p in tr.allowed_posts.all():
                        approver_posts[p.id] = p
            # Collect latest approver per post from logs
            ct = ContentType.objects.get_for_model(po)
            logs_all = list(ApprovalLog.objects.filter(content_type=ct, object_id=po.id).select_related('user', 'post', 'action').order_by('-timestamp'))
            latest_by_post = {}
            for lg in logs_all:
                if lg.post_id and lg.post_id not in latest_by_post:
                    latest_by_post[lg.post_id] = lg
            if approver_posts:
                story.append(Paragraph(_shape_text('امضا و تایید'), styles['Heading3']))
                story.append(Spacer(1, 6))
                # RTL column order: امضا, وضعیت, زمان, آخرین اقدام, نام تاییدکننده, پست, ردیف
                s_fields = ['امضا', 'وضعیت', 'زمان', 'آخرین اقدام', 'نام تاییدکننده', 'پست', 'ردیف']
                s_data = [ [_shape_text(h) for h in s_fields] ]
                for idx, (pid, post) in enumerate(approver_posts.items(), start=1):
                    lg = latest_by_post.get(pid)
                    approver_name = _shape_text(_full_name(getattr(lg, 'user', None))) if lg else _shape_text('—')
                    last_action = _shape_text(getattr(getattr(lg, 'action', None), 'name', '—')) if lg else _shape_text('—')
                    last_time = _shape_text(_format_date(getattr(lg, 'timestamp', None), persian=persian_dates)) if lg else _shape_text('—')
                    status_txt = _shape_text('تایید شد') if lg else _shape_text('در انتظار')
                    # RTL row data order
                    s_data.append([
                        _shape_text(''),  # امضا
                        status_txt,       # وضعیت
                        last_time,        # زمان
                        last_action,      # آخرین اقدام
                        approver_name,    # نام تاییدکننده
                        _shape_text(getattr(post, 'name', '')),  # پست
                        _to_persian_digits(idx)  # ردیف
                    ])
                # RTL column widths
                col_w = [doc.width*0.08, doc.width*0.12, doc.width*0.15, doc.width*0.15, doc.width*0.25, doc.width*0.20, doc.width*0.05]
                s_tbl = Table(s_data, repeatRows=1, colWidths=col_w)
                s_tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, -1), PERSIAN_FONT_NAME if FONT_READY else 'Helvetica'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ROWHEIGHT', (0,1), (-1,-1), 26),
                ]))
                story.append(s_tbl)
                story.append(Spacer(1, 16))
            else:
                story.append(Paragraph(_shape_text('لیست پست‌های تاییدکننده برای وضعیت فعلی یافت نشد.'), styles['Normal']))
                story.append(Spacer(1, 10))
        except Exception as e:
            logger.warning(f"[RPT] signature section skipped: {e}")

        # ========== Section: Factors (Summary + Details) ==========
        factors_qs = po.related_factors.all() if hasattr(po, 'related_factors') else []
        if show_factors and factors_qs:
            story.append(PageBreak())
            story.append(Paragraph(_shape_text('فاکتورهای مرتبط'), styles['Heading3']))
            story.append(Spacer(1, 8))
            factors = list(factors_qs.select_related('status'))
            # RTL column order: وضعیت, مبلغ, شماره, ردیف
            f_fields = ['وضعیت', 'مبلغ (ریال)', 'شماره', 'ردیف']
            f_data = [ [_shape_text(h) for h in f_fields] ]
            for idx, f in enumerate(factors, start=1):
                f_data.append([
                    _shape_text(getattr(getattr(f, 'status', None), 'name', '')),  # وضعیت
                    _to_persian_digits(f"{getattr(f, 'amount', 0):,}"),            # مبلغ
                    _shape_text(getattr(f, 'number', '')),                         # شماره
                    _to_persian_digits(idx),                                       # ردیف
                ])
            f_tbl = Table(f_data, repeatRows=1, colWidths=[doc.width*0.30, doc.width*0.30, doc.width*0.30, doc.width*0.10])
            f_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), PERSIAN_FONT_NAME if FONT_READY else 'Helvetica'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ]))
            story.append(f_tbl)
            story.append(Spacer(1, 14))

            # Per-factor detailed sections (optional images)
            if show_images and image_fields:
                for f in factors:
                    kt = []
                    kt.append(Paragraph(_shape_text(f"فاکتور {getattr(f, 'number', '')}"), styles['Heading3']))
                    kt.append(Spacer(1, 6))
                    # RTL column order: وضعیت, مبلغ, شماره
                    fd_fields = ['وضعیت', 'مبلغ (ریال)', 'شماره']
                    fd_vals = [
                        _shape_text(getattr(getattr(f, 'status', None), 'name', '')),  # وضعیت
                        _to_persian_digits(f"{getattr(f, 'amount', 0):,}"),            # مبلغ
                        _shape_text(getattr(f, 'number', '')),                         # شماره
                    ]
                    fd_data = list(zip([_shape_text(k) for k in fd_fields], fd_vals))
                    fd_tbl = Table([[_shape_text('مشخصات فاکتور'), '']] + fd_data, colWidths=[doc.width*0.28, doc.width*0.72])
                    fd_tbl.setStyle(TableStyle([
                        ('SPAN', (0,0), (-1,0)),
                        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
                        ('FONTNAME', (0,0), (-1,-1), PERSIAN_FONT_NAME if FONT_READY else 'Helvetica'),
                        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                    ]))
                    kt.append(fd_tbl)
                    kt.append(Spacer(1, 6))

                    for field_name in image_fields:
                        try:
                            img_obj = getattr(f, field_name, None)
                            if not img_obj:
                                continue
                            img_path = None
                            if hasattr(img_obj, 'path'):
                                img_path = img_obj.path
                            elif isinstance(img_obj, str) and os.path.exists(img_obj):
                                img_path = img_obj
                            if img_path and os.path.exists(img_path):
                                kt.append(Paragraph(_shape_text(f'تصویر {field_name}'), styles['Normal']))
                                img = RLImage(img_path)
                                max_w = doc.width
                                max_h = 420
                                iw, ih = img.wrap(0, 0)
                                scale = min((max_w/iw) if iw else 1, (max_h/ih) if ih else 1, 1)
                                img.drawWidth = iw * scale
                                img.drawHeight = ih * scale
                                kt.append(img)
                                kt.append(Spacer(1, 10))
                        except Exception as e:
                            logger.warning(f"[RPT] skip factor image: {e}")
                    story.append(KeepTogether(kt))
                    story.append(Spacer(1, 12))

        # ========== Section: Logs ==========
        if show_logs:
            ct = ContentType.objects.get_for_model(po)
            logs_qs = ApprovalLog.objects.filter(content_type=ct, object_id=po.id).select_related('user', 'post', 'action').order_by('-timestamp')
            logs = list(logs_qs)
            story.append(PageBreak())
            story.append(Paragraph(_shape_text('تاریخچه اقدامات'), styles['Heading3']))
            story.append(Spacer(1, 6))
            if logs:
                # RTL column order: توضیح, زمان, به وضعیت, از وضعیت, اقدام, پست, کاربر, ردیف
                l_fields = ['توضیح', 'زمان', 'به وضعیت', 'از وضعیت', 'اقدام', 'پست', 'کاربر', 'ردیف']
                l_data = [ [_shape_text(h) for h in l_fields] ]
                for idx, lg in enumerate(logs, start=1):
                    user_name = _full_name(getattr(lg, 'user', None))
                    l_data.append([
                        _shape_text(getattr(lg, 'comment', '')),  # توضیح
                        _shape_text(_format_date(getattr(lg, 'timestamp', None), persian=persian_dates)),  # زمان
                        _shape_text(getattr(getattr(lg, 'to_status', None), 'name', '')),  # به وضعیت
                        _shape_text(getattr(getattr(lg, 'from_status', None), 'name', '')),  # از وضعیت
                        _shape_text(getattr(getattr(lg, 'action', None), 'name', '')),  # اقدام
                        _shape_text(getattr(getattr(lg, 'post', None), 'name', '')),  # پست
                        _shape_text(user_name),  # کاربر
                        _to_persian_digits(idx),  # ردیف
                    ])
                # RTL column widths for logs table
                l_col_w = [doc.width*0.20, doc.width*0.12, doc.width*0.12, doc.width*0.12, doc.width*0.12, doc.width*0.15, doc.width*0.12, doc.width*0.05]
                l_tbl = Table(l_data, repeatRows=1, colWidths=l_col_w)
                l_tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, -1), PERSIAN_FONT_NAME if FONT_READY else 'Helvetica'),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ]))
                story.append(l_tbl)
            else:
                story.append(Paragraph(_shape_text('تاریخچه‌ای ثبت نشده است.'), styles['Normal']))

        # Footer
        story.append(Spacer(1, 12))
        story.append(Paragraph(_shape_text(f'تاریخ تهیه گزارش: {_format_date(datetime.now(), persian=True)}'), styles['Normal']))

        doc.build(story)
        resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f"attachment; filename=PO-{smart_str(po.order_number)}.pdf"
        return resp
    except Exception as e:
        logger.error(f"[RPT] reportlab_paymentorder_detail failed: {e}", exc_info=True)
        return JsonResponse({'error': 'خطای تولید PDF جزئیات دستور پرداخت'}, status=500)



# # افقی با همه بخش‌ها
# /budgets/api/reportlab/paymentorder/3/detail/?landscape=true&show_factors=true&show_logs=true

# # عمودی بدون تصاویر
# /budgets/api/reportlab/paymentorder/3/detail/?landscape=false&show_factors=true&show_logs=true

# # با فونت سفارشی
# /budgets/api/reportlab/paymentorder/3/detail/?font_path=/path/to/font.ttf