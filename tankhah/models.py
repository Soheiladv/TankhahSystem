import os
from decimal import Decimal
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum, Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from accounts.models import CustomUser
import logging
from core.models import WorkflowStage, Post, SystemSettings, AccessRule, UserPost

logger = logging.getLogger(__name__)

NUMBER_SEPARATOR = getattr(settings, 'NUMBER_SEPARATOR', '-')
#-----------------------------------------------
def get_default_workflow_stage():

    from core.models import WorkflowStage  # اگر در همان اپلیکیشن است
    try:
        return WorkflowStage.objects.get(name='HQ_INITIAL').id
    except WorkflowStage.DoesNotExist:
        # اگه پیدا نشد، اولین مرحله رو برگردون یا None
        stage = WorkflowStage.objects.order_by('order').first()
        return stage.id if stage else None
def tankhah_document_path(instance, filename):
    # مسیر آپلود: documents/شماره_تنخواه/نام_فایل
    extension = os.path.splitext(filename)[1]  # مثل .pdf
    return f'documents/{instance.tankhah.number}/document{extension}/%Y/%m/%d/'
# --- تابع اصلاح شده ---
def Ok__create_budget_transaction(allocation, transaction_type, amount, related_obj, created_by, description,
                             transaction_id):
    """
    ایجاد تراکنش بودجه با اعتبارسنجی مبلغ و بدون ارسال فیلدهای مربوط به فاکتور/آیتم.

    Args:
        allocation (BudgetAllocation): تخصیص بودجه مرتبط.
        transaction_type (str): نوع تراکنش ('CONSUMPTION', 'RETURN', ...).
        amount (Decimal): مبلغ تراکنش.
        related_obj: شیء مرتبط (Tankhah, Factor, FactorItem) برای تعیین related_tankhah.
        created_by (CustomUser): کاربر ایجادکننده.
        description (str): توضیحات تراکنش.
        transaction_id (str): شناسه منحصربه‌فرد تراکنش.

    Raises:
        ValidationError: اگر مبلغ مصرف بیشتر از باقیمانده باشد یا مبلغ برگشتی نامعتبر باشد.
        Exception: برای سایر خطاهای دیتابیس یا پیش‌بینی نشده.
    """
    # Import models needed within the function
    from budgets.models import BudgetTransaction, BudgetHistory  # Adjust import path
    from tankhah.models import Tankhah, Factor, FactorItem  # Adjust import path

    # Validate input types (optional but good practice)
    if not hasattr(allocation, 'get_remaining_amount'):
        msg = "شیء 'allocation' ارسال شده متد get_remaining_amount را ندارد."
        logger.error(msg)
        raise TypeError(msg)
    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(amount)
        except Exception:
            msg = f"مقدار 'amount' ({amount}) قابل تبدیل به Decimal نیست."
            logger.error(msg)
            raise TypeError(msg)

    try:
        with transaction.atomic():
            # 1. تعیین related_tankhah بر اساس related_obj
            related_tankhah = None
            if isinstance(related_obj, Tankhah):
                related_tankhah = related_obj
            elif isinstance(related_obj, Factor):
                related_tankhah = related_obj.tankhah
            elif isinstance(related_obj, FactorItem):
                related_tankhah = related_obj.factor.tankhah
            else:
                logger.warning(
                    f"Invalid related_obj type '{type(related_obj)}' for BudgetTransaction. related_tankhah will be NULL.")
                # Decide if you want to raise an error here instead
                # raise ValidationError(_("نوع شیء مرتبط برای تراکنش بودجه نامعتبر است."))

            # 2. اعتبارسنجی مبلغ تراکنش
            remaining = allocation.get_remaining_amount()  # Call the method
            logger.debug(
                f"create_budget_transaction check: allocation={allocation.pk}, remaining={remaining}, amount={amount}, type={transaction_type}")

            if transaction_type == 'CONSUMPTION':
                if amount <= Decimal('0'):
                    raise ValidationError(_("مبلغ مصرف باید مثبت باشد."))
                if amount > remaining:
                    logger.error(
                        f"Consumption amount {amount} exceeds remaining allocation {remaining} for allocation {allocation.pk}")
                    raise ValidationError(
                        _("مبلغ مصرف ({:,}) بیشتر از بودجه باقی‌مانده تخصیص ({:,}) است.").format(amount, remaining))

            elif transaction_type == 'RETURN':
                if amount <= Decimal('0'):
                    raise ValidationError(_("مبلغ برگشتی باید مثبت باشد."))
                # Calculate net consumed to validate return amount ceiling
                if hasattr(allocation, 'get_consumed_amount') and hasattr(allocation, 'get_returned_amount'):
                    consumed = allocation.get_consumed_amount()
                    returned_so_far = allocation.get_returned_amount()
                    net_consumed = consumed - returned_so_far
                    if amount > net_consumed:
                        logger.error(
                            f"Return amount {amount} exceeds net consumed {net_consumed} for allocation {allocation.pk}")
                        raise ValidationError(
                            _("مبلغ برگشتی ({:,}) نمی‌تواند بیشتر از مبلغ خالص مصرف شده ({:,}) باشد.").format(amount,
                                                                                                              net_consumed))
                else:
                    logger.warning(
                        f"Cannot validate RETURN amount ceiling for allocation {allocation.pk} due to missing methods.")

            # بررسی بودجه باقی‌مانده
            remaining = allocation.get_remaining_amount()
            if transaction_type == 'CONSUMPTION' and amount > remaining:
                logger.error(f"Insufficient budget: Amount {amount} exceeds remaining {remaining}")
                raise ValueError(f"مبلغ {amount} بیشتر از بودجه باقی‌مانده {remaining} است.")

            # تولید transaction_id اگر ارائه نشده باشد
            if not transaction_id:
                timestamp_str = timezone.now().strftime('%Y%m%d%H%M%S%f')
                transaction_id = f"TX-FACTOR-NEW-{transaction_type[:3]}-{allocation.id}-{timestamp_str}"
                logger.debug(f"Generated transaction_id: {transaction_id}")


            # 3. ایجاد تراکنش بودجه (بدون فیلدهای related_factor/related_factor_item)
            budget_transaction = BudgetTransaction.objects.create(
                allocation=allocation,
                transaction_type=transaction_type,
                amount=amount,
                related_tankhah=related_tankhah,  # فقط فیلدی که در مدل BudgetTransaction وجود دارد
                created_by=created_by,
                description=description,
                transaction_id=transaction_id  # اطمینان از ارسال شناسه یکتا
            )
            logger.info(
                f"BudgetTransaction created successfully: ID={budget_transaction.pk}, TxID={transaction_id}, amount={amount}, type={transaction_type}, allocation={allocation.pk}")

            # 4. (اختیاری) ثبت تاریخچه بودجه
            try:
                # ثبت تاریخچه بودجه
                history_transaction_id = f"HIST-{transaction_id}"

                BudgetHistory.objects.create(
                    content_type=ContentType.objects.get_for_model(allocation),
                    object_id=allocation.id,
                    action=transaction_type,
                    amount=amount,
                    created_by=created_by,
                    details=f"{transaction_type} {amount:,.0f} for allocation {allocation.id}: {description}",
                    transaction_id=history_transaction_id
                )
                logger.info(f"BudgetHistory recorded for transaction: {transaction_id}")
            except NameError:
                logger.warning("BudgetHistory model not found or not imported, skipping history recording.")
            except Exception as hist_exc:
                logger.error(f"Error recording BudgetHistory for transaction {transaction_id}: {hist_exc}",
                             exc_info=True)

            # 5. (مهم - اختیاری) آپدیت کردن فیلد باقیمانده در خود Allocation؟
            # اگر مدل BudgetAllocation فیلدی مثل 'remaining_amount' برای ذخیره باقیمانده دارد،
            # باید آن را اینجا آپدیت کنید تا با get_remaining_amount() هماهنگ باشد.
            # allocation.remaining_amount = remaining - amount # یا + amount برای RETURN
            # allocation.save(update_fields=['remaining_amount'])
            # logger.info(f"Updated remaining_amount on BudgetAllocation {allocation.pk}")

            # Return the created transaction object
            return budget_transaction

    except ValidationError as ve:
        # Log validation errors clearly
        error_message = str(ve.message_dict) if hasattr(ve, 'message_dict') else str(ve)
        logger.error(
            f"Validation Error creating BudgetTransaction: {error_message} (Allocation: {allocation.pk}, Amount: {amount}, Type: {transaction_type})",
            exc_info=False)  # exc_info=False for cleaner logs
        raise  # Re-raise to be handled by the caller (e.g., the view)
    except Exception as e:
        # Log other unexpected errors
        logger.error(
            f"Unexpected Error creating BudgetTransaction: {str(e)} (Allocation: {allocation.pk}, Amount: {amount}, Type: {transaction_type})",
            exc_info=True)
        raise  # Re-raise unexpected errors
#-----------------------------------------------
def factor_document_upload_path(instance, filename):
    """
    مسیر آپلود فایل برای FactorDocument را بر اساس شماره تنخواه و ID فاکتور تعیین می‌کند.
    مسیر نهایی: factors/[شماره_تنخواه]/[ID_فاکتور]/[نام_فایل_اصلی]
    """
    # instance در اینجا یک شیء FactorDocument است
    factor = instance.factor
    if factor and factor.tankhah:
        tankhah_number = factor.tankhah.number
        factor_id = factor.id
        # برای جلوگیری از ذخیره شدن همه فایل‌ها با نام یکسان اگر چند فایل همزمان آپلود شوند،
        # بهتر است نام فایل اصلی را نگه داریم یا یک نام یکتا بسازیم.
        # filename = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}" # مثال: ساخت نام یکتا
        return f'factors/{tankhah_number}/{factor_id}/{filename}'
    else:
        # یک مسیر پیش‌فرض در صورتی که فاکتور یا تنخواه هنوز ذخیره نشده باشند (که نباید اتفاق بیفتد)
        # یا فاکتور به تنخواه لینک نباشد
        return f'factors/orphaned/{filename}'
def create_budget_transaction(allocation, transaction_type, amount, related_obj, created_by, description, transaction_id):
    """
    ایجاد تراکنش بودجه با اعتبارسنجی مبلغ، ثبت تاریخچه و بررسی هشدار/قفل دوره بودجه.

    Args:
        allocation (BudgetAllocation): تخصیص بودجه مرتبط که تراکنش روی آن اعمال می‌شود.
        transaction_type (str): نوع تراکنش ('CONSUMPTION', 'RETURN', ...).
        amount (Decimal): مبلغ تراکنش (باید مثبت باشد).
        related_obj: شیء مرتبط (Tankhah, Factor, FactorItem) که باعث این تراکنش شده.
        created_by (CustomUser): کاربر ایجادکننده تراکنش.
        description (str): توضیحات تراکنش.
        transaction_id (str): شناسه منحصربه‌فرد برای BudgetTransaction (معمولاً از ویو می‌آید).

    Returns:
        BudgetTransaction: نمونه تراکنش ایجاد شده.

    Raises:
        ValidationError: اگر اعتبارسنجی‌ها (مبلغ منفی، عدم بودجه کافی، ...) ناموفق باشند.
        TypeError: اگر نوع ورودی‌ها نامعتبر باشد.
        AttributeError: اگر متدهای لازم روی allocation یا budget_period وجود نداشته باشند.
        Exception: برای سایر خطاهای پیش‌بینی نشده.
    """
    # --- ۰. اعتبارسنجی ورودی‌های اولیه ---
    # بررسی وجود متد لازم در allocation
    if not hasattr(allocation, 'get_remaining_amount'):
        msg = "شیء 'allocation' ارسال شده متد get_remaining_amount را ندارد."
        logger.error(msg + f" (Allocation PK: {allocation.pk if allocation else 'None'})")
        raise AttributeError(msg) # استفاده از AttributeError واضح‌تر است

    # اطمینان از Decimal بودن مبلغ و مثبت بودن آن
    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(str(amount)) # تبدیل امن‌تر
        except Exception:
            msg = f"مقدار 'amount' ({amount}) قابل تبدیل به Decimal معتبر نیست."
            logger.error(msg)
            raise TypeError(msg)
    if amount <= Decimal('0'):
        raise ValidationError(_("مبلغ تراکنش ({}) باید مثبت باشد.").format(amount))

    # اطمینان از وجود کاربر ایجاد کننده
    if not created_by:
        logger.error("کاربر ایجاد کننده (created_by) برای تراکنش بودجه مشخص نشده است.")
        # بسته به سیاست شما، می‌توانید خطا ایجاد کنید یا یک کاربر پیش‌فرض در نظر بگیرید
        raise ValueError("created_by cannot be None for BudgetTransaction.")

    try:
        # استفاده از تراکنش اتمی برای اطمینان از اجرای کامل یا هیچ‌کدام
        with transaction.atomic():

            # --- ۱. تعیین اشیاء مرتبط (برای ذخیره در BudgetTransaction) ---
            related_tankhah = None
            related_factor = None
            related_factor_item = None

            if isinstance(related_obj, Tankhah):
                related_tankhah = related_obj
            elif isinstance(related_obj, Factor):
                related_factor = related_obj
                # دریافت تنخواه از فاکتور (فرض می‌شود هر فاکتور تنخواه دارد)
                if hasattr(related_obj, 'tankhah'):
                    related_tankhah = related_obj.tankhah
                else:
                    logger.warning(f"Factor object (pk={related_obj.pk}) does not have 'tankhah' attribute.")
            elif isinstance(related_obj, FactorItem):
                related_factor_item = related_obj
                # دریافت فاکتور و سپس تنخواه از آیتم
                if hasattr(related_obj, 'factor') and related_obj.factor:
                    related_factor = related_obj.factor
                    if hasattr(related_obj.factor, 'tankhah'):
                        related_tankhah = related_obj.factor.tankhah
                    else:
                         logger.warning(f"Factor object (pk={related_obj.factor.pk}) related to FactorItem (pk={related_obj.pk}) does not have 'tankhah' attribute.")
                else:
                    logger.warning(f"FactorItem object (pk={related_obj.pk}) does not have 'factor' attribute.")
            else:
                # اگر نوع شیء مرتبط متفاوت است یا نمی‌خواهید لینک کنید
                logger.info(f"BudgetTransaction related_obj type '{type(related_obj)}' is not explicitly handled for linking.")

            # --- ۲. بررسی وضعیت قفل بودن دوره بودجه ---
            budget_period = allocation.budget_period
            if hasattr(budget_period, 'is_period_locked'):
                is_locked, lock_message = budget_period.is_period_locked
                if is_locked and transaction_type == 'CONSUMPTION': # فقط مصرف را محدود کن
                    logger.warning(f"Attempted transaction on locked budget period {budget_period.pk}: {lock_message}")
                    raise ValidationError(_("امکان ثبت هزینه وجود ندارد: {}").format(lock_message))
            else:
                 logger.warning(f"Method 'is_period_locked' not found on BudgetPeriod model (pk={budget_period.pk}). Lock check skipped.")


            # --- ۳. اعتبارسنجی مبلغ نسبت به بودجه باقیمانده ---
            remaining_on_allocation = allocation.get_remaining_amount() # فراخوانی متد محاسبه باقیمانده
            logger.debug(f"Budget check: allocation_pk={allocation.pk}, remaining={remaining_on_allocation}, tx_amount={amount}, tx_type={transaction_type}")

            if transaction_type == 'CONSUMPTION':
                # بررسی اینکه آیا مبلغ مصرف از باقیمانده بیشتر است
                if amount > remaining_on_allocation:
                    logger.error(f"Insufficient funds: Consumption amount {amount} exceeds remaining allocation {remaining_on_allocation} for allocation {allocation.pk}")
                    raise ValidationError(
                        _("مبلغ مصرف ({:,}) بیشتر از بودجه باقی‌مانده تخصیص ({:,}) است.").format(amount, remaining_on_allocation)
                    )
            elif transaction_type == 'RETURN':
                # (اختیاری) بررسی سقف بازگشت بر اساس مصرف خالص
                if hasattr(allocation, 'get_consumed_amount') and hasattr(allocation, 'get_returned_amount'):
                    consumed = allocation.get_consumed_amount()
                    returned_so_far = allocation.get_returned_amount()
                    net_consumed = consumed - returned_so_far
                    if amount > net_consumed:
                        logger.error(f"Invalid return: Return amount {amount} exceeds net consumed {net_consumed} for allocation {allocation.pk}")
                        raise ValidationError(
                            _("مبلغ برگشتی ({:,}) نمی‌تواند بیشتر از مبلغ خالص مصرف شده ({:,}) باشد.").format(amount, net_consumed)
                        )
                else:
                    logger.warning(f"Cannot validate RETURN ceiling for allocation {allocation.pk} due to missing check methods.")

            # --- ۴. ایجاد رکورد BudgetTransaction ---
            # **مهم:** مطمئن شوید مدل BudgetTransaction شما فقط فیلدهای زیر را دارد
            # (یا اگر فیلدهای related_factor/item را دارد، آنها را هم اینجا مقداردهی کنید)
            try:
                from budgets.models import  BudgetTransaction
                budget_tx = BudgetTransaction.objects.create(
                    allocation=allocation,                 # تخصیص مرتبط
                    transaction_type=transaction_type,     # نوع تراکنش
                    amount=amount,                         # مبلغ
                    related_tankhah=related_tankhah,       # تنخواه مرتبط (اگر وجود دارد)
                    created_by=created_by,                 # کاربر ایجاد کننده
                    description=description,               # توضیحات
                    transaction_id=transaction_id,         # شناسه یکتای تراکنش (از ویو)
                    # content_type=ContentType.objects.get_for_model(related_obj) if related_obj else None,
                    # object_id=related_obj.id if related_obj else None,
                )
                logger.info(f"BudgetTransaction created: ID={budget_tx.pk}, TxID={transaction_id},"
                            f" amount={amount}, type={transaction_type}, allocation_pk={allocation.pk}")
            except Exception as e:
                logger.error(
                    f"Unexpected Error in create_budget_transaction: {str(e)} "
                    f"(Allocation: {allocation.id}, Amount: {amount}, Type: {transaction_type})",
                    exc_info=True
                )
                raise
            # --- ۵. ثبت تاریخچه بودجه (اختیاری) ---
            try:
                 # **اصلاح:** اطمینان از وجود و مقداردهی فیلدهای لازم در BudgetHistory
                 # فرض می‌کنیم BudgetHistory فیلد transaction_id (برای شناسه اصلی) و action دارد
                 from budgets.models import  BudgetHistory
                 if hasattr(BudgetHistory._meta, 'get_field'): # Check if model has fields before accessing
                      history_data = {
                          'content_type': ContentType.objects.get_for_model(allocation),
                          'object_id': allocation.id,
                          'action': transaction_type, # استفاده از نوع تراکنش به عنوان اکشن
                          'amount': amount,
                          'created_by': created_by,
                          'details': f"{transaction_type} {amount:,.0f} for allocation {allocation.id}: {description}",
                      }
                      # فقط اگر فیلد transaction_id در BudgetHistory وجود دارد، آن را اضافه کن
                      from budgets.models import  BudgetHistory
                      if 'transaction_id' in [f.name for f in BudgetHistory._meta.get_fields()]:
                           history_data['transaction_id'] = transaction_id # استفاده از شناسه اصلی تراکنش
                      # فقط اگر فیلد transaction_type در BudgetHistory وجود دارد، آن را اضافه کن
                      if 'transaction_type' in [f.name for f in BudgetHistory._meta.get_fields()]:
                           history_data['transaction_type'] = transaction_type

                      BudgetHistory.objects.create(**history_data)
                      logger.info(f"BudgetHistory recorded for TxID: {transaction_id}")
                 else:
                      logger.warning("BudgetHistory model structure seems incorrect. Skipping history.")

            except NameError:
                 logger.warning("BudgetHistory model not found or not imported, skipping history recording.")
            except Exception as hist_exc:
                 logger.error(f"Error recording BudgetHistory for transaction {transaction_id}: {hist_exc}", exc_info=True)
                 # در صورت بروز خطا در ثبت تاریخچه، تراکنش اصلی رول‌بک *نمی‌شود* مگر اینکه raise کنید


            # --- ۶. بررسی آستانه هشدار و اقدام لازم (بعد از ثبت موفق تراکنش) ---
            if hasattr(budget_period, 'check_warning_threshold') and callable(budget_period.check_warning_threshold):
                # دوباره باقیمانده را محاسبه کن *بعد* از ثبت تراکنش جدید
                # Note: This might cause an extra query if get_remaining_amount is not cached efficiently
                # remaining_after_tx = allocation.get_remaining_amount()
                # Alternatively, calculate it directly: remaining_after_tx = remaining - amount (for CONSUMPTION) or + amount (for RETURN)
                remaining_after_tx = remaining_on_allocation  + (amount * Decimal('-1.0') if transaction_type == 'CONSUMPTION' else amount)

                # حالا وضعیت هشدار را با مقدار جدید چک کن
                # reached_warning, warning_message = budget_period.check_warning_threshold(current_remaining=remaining_after_tx) # Pass current remaining if method accepts it
                reached_warning, warning_message = budget_period.check_warning_threshold()

                if reached_warning:
                    logger.warning(f"Budget Period {budget_period.pk} reached warning threshold AFTER Tx {transaction_id}: {warning_message}")
                    warning_action = getattr(budget_period, 'warning_action', 'NOTIFY') # Get action, default to NOTIFY

                    if warning_action == 'LOCK':
                        # قفل کردن دوره
                        if hasattr(budget_period, 'is_locked_due_to_warning'):
                             if not budget_period.is_locked_due_to_warning:
                                 budget_period.is_locked_due_to_warning = True
                                 budget_period.save(update_fields=['is_locked_due_to_warning'])
                                 logger.info(f"Budget Period {budget_period.pk} LOCKED due to warning threshold.")
                                 # ارسال اعلان قفل
                                 if hasattr(budget_period, 'send_notification'): budget_period.send_notification('locked', _("بودجه دوره به دلیل رسیدن به آستانه هشدار قفل شد."))
                        else: logger.error("Cannot LOCK period: 'is_locked_due_to_warning' field missing.")

                    elif warning_action == 'RESTRICT' or warning_action == 'NOTIFY':
                        # ارسال اعلان (برای هر دو حالت Notify و Restrict در این مرحله)
                        restrict_msg_part = _(" ثبت هزینه‌های جدید ممکن است محدود شود.") if warning_action == 'RESTRICT' else ""
                        if hasattr(budget_period, 'send_notification'): budget_period.send_notification('warning', warning_message + restrict_msg_part)

            else:
                logger.warning(f"Method 'check_warning_threshold' not found on BudgetPeriod model (pk={budget_period.pk}). Warning check skipped.")

            # --- ۷. بازگرداندن تراکنش ایجاد شده ---
            return budget_tx

    # --- مدیریت خطا ---
    except ValidationError as ve:
        error_message = str(ve.message_dict) if hasattr(ve, 'message_dict') else str(ve)
        logger.error(f"Validation Error in create_budget_transaction: {error_message} (Allocation: {allocation.pk}, Amount: {amount}, Type: {transaction_type})", exc_info=False)
        raise
    except Exception as e:
        logger.error(f"Unexpected Error in create_budget_transaction: {str(e)} (Allocation: {allocation.pk}, Amount: {amount}, Type: {transaction_type})", exc_info=True)
        raise
#-----------------------------------------------
class TankhahDocument(models.Model):
    tankhah  = models.ForeignKey('Tankhah', on_delete=models.CASCADE,verbose_name=_("تنخواه"), related_name='documents')
    document = models.FileField(upload_to=tankhah_document_path,  verbose_name=_("سند"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آپلود")
    file_size = models.IntegerField(null=True, blank=True, verbose_name=_("حجم فایل (بایت)"))

    def save(self, *args, **kwargs):
        if self.document:
            self.file_size = self.document.size
        super().save(*args, **kwargs)

    def __str__(self):
        return f"سند {self.tankhah.number} - {self.uploaded_at}-{self.document.name}"
    class Meta:
        default_permissions = ()
        permissions = [
            ('TankhahDocument_view','نمایش اسناد فاکتور منتهی به تنخواه'),
            ('TankhahDocument_add','افزودن اسناد فاکتور منتهی به تنخواه'),
            ('TankhahDocument_update','بروزرسانی اسناد فاکتور منتهی به تنخواه'),
            ('TankhahDocument_delete','حــذف اسناد فاکتور منتهی به تنخواه'),
        ]
class Tankhah(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', _('پیش‌نویس')),
        ('PENDING', _('در حال بررسی')),
        ('APPROVED', _('تأییدشده')),
        ('SENT_TO_HQ', _('ارسال‌شده به HQ')),
        ('HQ_OPS_PENDING', _('در حال بررسی - بهره‌برداری')),
        ('HQ_OPS_APPROVED', _('تأییدشده - بهره‌برداری')),
        ('HQ_FIN_PENDING', _('در حال بررسی - مالی')),
        ('PAID', _('پرداخت‌شده')),
        ('REJECTED', _('ردشده')),
    )

    number = models.CharField(max_length=150, unique=True, blank=True, verbose_name=_("شماره تنخواه"))
    amount = models.DecimalField(max_digits=25, decimal_places=2, verbose_name=_("مبلغ"))
    date = models.DateTimeField(default=timezone.now, verbose_name=_("تاریخ"))
    due_date = models.DateTimeField(null=True, blank=True, verbose_name=_('مهلت زمانی'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, verbose_name=_('مجموعه/شعبه'))
    project = models.ForeignKey('core.Project', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='tankhah_set', verbose_name=_('پروژه'))
    project_budget_allocation = models.ForeignKey(
        'budgets.BudgetAllocation', on_delete=models.CASCADE, related_name='tankhahs',
        verbose_name=_("تخصیص بودجه پروژه"), null=True, blank=True
    )
    subproject = models.ForeignKey('core.SubProject', on_delete=models.CASCADE, null=True, blank=True,
                                   verbose_name=_("زیر مجموعه پروژه"))
    letter_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره نامه"))
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                                   related_name='tankhah_created', verbose_name=_("ایجادکننده"))
    approved_by = models.ManyToManyField('accounts.CustomUser', blank=True, verbose_name=_('تأییدکنندگان'))
    description = models.TextField(verbose_name=_("توضیحات"))
    current_stage = models.ForeignKey('core.WorkflowStage', on_delete=models.SET_NULL, null=True, default=None,
                                      verbose_name="مرحله فعلی")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', verbose_name=_("وضعیت"))
    hq_status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True,
                                 verbose_name=_("وضعیت در HQ"))
    last_stopped_post = models.ForeignKey('core.Post', null=True, blank=True, on_delete=models.SET_NULL,
                                          verbose_name=_("آخرین پست متوقف‌شده"))
    is_archived = models.BooleanField(default=False, verbose_name=_("آرشیو شده"))
    payment_number = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("شماره پرداخت"))
    is_locked = models.BooleanField(default=False, verbose_name=_("قفل شده"))
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان آرشیو")
    canceled = models.BooleanField(default=False, verbose_name="لغو شده")
    remaining_budget = models.DecimalField(max_digits=25, decimal_places=2, default=0,
                                           verbose_name=_("بودجه باقیمانده"))
    is_emergency = models.BooleanField(default=False, verbose_name=_("اضطراری"))
    request_date = models.DateField(default=timezone.now, verbose_name=_("تاریخ درخواست"))
    payment_ceiling = models.DecimalField(max_digits=25, decimal_places=2, null=True, blank=True,
                                          verbose_name=_("سقف پرداخت"))
    is_payment_ceiling_enabled = models.BooleanField(default=False, verbose_name=_("فعال بودن سقف پرداخت"))

    class Meta:
        verbose_name = _("تنخواه")
        verbose_name_plural = _("تنخواه‌ها")
        indexes = [
            models.Index(fields=['number', 'date', 'status',
                                 'organization','number',
                                 'project_id', 'organization_id',
                                 'status', 'created_at']),
        ]
        default_permissions = ()
        permissions = [
            ('Tankhah_add', _(' + افزودن تنخواه')),
            ('Tankhah_view', _('نمایش تنخواه')),
            ('Tankhah_detail', _('نمایش تنخواه')),
            ('Tankhah_update', _('🆙بروزرسانی تنخواه')),
            ('Tankhah_delete', _('⛔حذف تنخواه')),
            ('Tankhah_approve', _('👍تأیید تنخواه')),
            ('Tankhah_reject', _('رد تنخواه👎')),
            ('Tankhah_view_all', _('نمایش همه تنخواه‌ها (دفتر مرکزی)')),

            ('Tankhah_part_approve', '👍تأیید رئیس قسمت'),

            ('Tankhah_hq_view', 'رصد دفتر مرکزی'),
            ('Tankhah_hq_approve', '👍تأیید رده بالا در دفتر مرکزی'),

            ('Tankhah_HQ_OPS_PENDING', _('در حال بررسی - بهره‌برداری')),
            ('Tankhah_HQ_OPS_APPROVED', _('👍تأییدشده - بهره‌برداری')),
            ('Tankhah_HQ_FIN_PENDING', _('در حال بررسی - مالی')),
            ('Tankhah_PAID', _('پرداخت‌شده')),

            ("FactorItem_approve", "👍تایید/رد ردیف فاکتور (تایید ردیف فاکتور*استفاده در مراحل تایید*)"),
            ('edit_full_tankhah', '👍😊تغییرات کاربری در فاکتور /تایید یا رد ردیف ها '),

            ('Dashboard_Core_view', 'دسترسی به داشبورد Core پایه'),
            ('DashboardView_flows_view', 'دسترسی به روند تنخواه گردانی'),
            ('Dashboard__view', 'دسترسی به داشبورد اصلی 💻'),
            ('Dashboard_Stats_view', 'دسترسی به آمار کلی داشبورد💲'),
        ]

    def __str__(self):
        project_str = self.project.name if self.project else 'بدون پروژه'
        subproject_str = f" ({self.subproject.name})" if self.subproject else ''
        return f"{self.number} - {project_str}{subproject_str} - {self.amount:,.0f} ({self.get_status_display()})"

    def get_remaining_budget(self):
        """محاسبه بودجه باقی‌مانده با در نظر گرفتن سقف پرداخت"""
        remaining = Decimal('0')

        from budgets.budget_calculations import get_subproject_remaining_budget,get_project_remaining_budget
        if self.project_budget_allocation:
            remaining = self.project_budget_allocation.get_remaining_amount()
        elif self.subproject:
            remaining = get_subproject_remaining_budget(self.subproject)
        elif self.project:
            remaining = get_project_remaining_budget(self.project)
        else:
            logger.warning(f"No budget source for Tankhah {self.number}")
            return remaining

        # اعمال سقف پرداخت
        settings = SystemSettings.objects.first()
        if self.is_payment_ceiling_enabled and self.payment_ceiling is not None:
            remaining = min(remaining, self.payment_ceiling)
        elif settings and settings.tankhah_payment_ceiling_enabled_default and settings.tankhah_payment_ceiling_default is not None:
            remaining = min(remaining, settings.tankhah_payment_ceiling_default)

        return remaining

    def update_remaining_budget(self):
        """به‌روزرسانی فیلد remaining_budget بدون فراخوانی save"""
        self.remaining_budget = self.get_remaining_budget()

    def clean(self):
        """اعتبارسنجی تنخواه"""
        super().clean()

        if self.amount is None:
            raise ValidationError({"amount": _("مبلغ تنخواه اجباری است.")})

        if self.amount <= 0:
            raise ValidationError({"amount": _("مبلغ تنخواه باید مثبت باشد.")})

        if self.subproject and self.project and self.subproject.project != self.project:
            raise ValidationError({"subproject": _("زیرپروژه باید متعلق به پروژه انتخاب‌شده باشد.")})

        if self.project_budget_allocation and self.project and self.project_budget_allocation.project != self.project:
            raise ValidationError({"project_budget_allocation": _("تخصیص بودجه باید متعلق به پروژه انتخاب‌شده باشد.")})

        remaining = self.get_remaining_budget()
        if self.amount > remaining:
            raise ValidationError(
                _(f"مبلغ تنخواه ({self.amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده ({remaining:,.0f} ریال) است.")
            )

    # def save(self, *args, **kwargs):
    #     with transaction.atomic():
    #         if not self.number:
    #             self.number = self.generate_number()
    #
    #         # تنظیم project_budget_allocation و اطمینان از سازگاری
    #         allocation = self.project_budget_allocation
    #         if not allocation and self.project:
    #             from budgets.models import BudgetAllocation
    #             allocation = BudgetAllocation.objects.filter(
    #                 project=self.project,
    #                 subproject__isnull=True,
    #                 budget_allocation__is_active=True
    #             ).first()
    #             if allocation:
    #                 self.project_budget_allocation = allocation
    #         if not allocation and self.subproject:
    #             allocation = BudgetAllocation.objects.filter(
    #                 subproject=self.subproject,
    #                 budget_allocation__is_active=True
    #             ).first()
    #             if allocation:
    #                 self.project_budget_allocation = allocation
    #
    #         if not allocation:
    #             raise ValidationError(_("تخصیص بودجه معتبر برای این پروژه/زیرپروژه یافت نشد."))
    #
    #         # به‌روزرسانی remaining_budget
    #         self.update_remaining_budget()
    #
    #         # اعتبارسنجی
    #         self.clean()
    #
    #         if not self.pk:
    #             remaining = allocation.get_remaining_amount()
    #             if self.amount > remaining:
    #                 raise ValidationError(
    #                     _(f"مبلغ تنخواه ({self.amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده تخصیص ({remaining:,.0f} ریال) است.")
    #                 )
    #
    #         if self.status in ['APPROVED', 'PAID'] and not self.is_locked:
    #             if self.status == 'PAID':
    #                 create_budget_transaction(
    #                     allocation=allocation.budget_allocation,
    #                     transaction_type='CONSUMPTION',
    #                     amount=self.amount,
    #                     related_obj=self,
    #                     created_by=self.created_by,
    #                     description=f"Tankhah {self.number} for project {self.project.id}",
    #                     transaction_id=f"TX-TNK-CONS-{self.number}"
    #                 )
    #                 self.is_locked = True
    #
    #         if self.status == 'REJECTED':
    #             initial_stage = WorkflowStage.objects.order_by('order').first()
    #             if self.current_stage == initial_stage:
    #                 factors = Factor.objects.filter(tankhah=self, is_finalized=True)
    #                 factors.update(is_finalized=False, locked=False)
    #                 if allocation:
    #                     target_allocation = BudgetAllocation.objects.filter(organization__is_core=True).first()
    #                     if target_allocation:
    #                         create_budget_transaction(
    #                             allocation=allocation.budget_allocation,
    #                             transaction_type='TRANSFER',
    #                             amount=self.amount,
    #                             related_obj=self,
    #                             created_by=self.created_by,
    #                             description=f"انتقال بودجه به دلیل رد تنخواه {self.number}",
    #                             transaction_id=f"TX-TNK-XFER-{self.number}",
    #                             target_allocation=target_allocation
    #                         )
    #                     else:
    #                         create_budget_transaction(
    #                             allocation=allocation.budget_allocation,
    #                             transaction_type='RETURN',
    #                             amount=self.amount,
    #                             related_obj=self,
    #                             created_by=self.created_by,
    #                             description=f"بازگشت بودجه به دلیل رد تنخواه {self.number}",
    #                             transaction_id=f"TX-TNK-RET-{self.number}"
    #                         )
    #                     self.is_locked = False
    #
    #         super().save(*args, **kwargs)
    #
    #         if allocation and (allocation.is_locked or allocation.budget_allocation.budget_period.is_locked):
    #             self.is_active = False
    #             super().save(update_fields=['is_active'])
    def save(self, *args, **kwargs):
        from budgets.models import BudgetAllocation
        with transaction.atomic():
            if not self.number:
                self.number = self.generate_number()

            # بررسی وجود و فعال بودن project_budget_allocation
            if self.project_budget_allocation:
                try:
                    allocation = BudgetAllocation.objects.get(
                        id=self.project_budget_allocation.id,
                        is_active=True
                    )
                except BudgetAllocation.DoesNotExist:
                    raise ValidationError(_("تخصیص بودجه معتبر نیست یا غیرفعال است."))
            else:
                # اگر project_budget_allocation اجباری است، خطا بدهید
                raise ValidationError(_("تخصیص بودجه پروژه اجباری است."))

            self.update_remaining_budget()
            self.clean()

            if self.project_budget_allocation:
                remaining = self.project_budget_allocation.get_remaining_amount()
                if self.amount > remaining:
                    raise ValidationError(
                        _(f"مبلغ تنخواه ({self.amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده تخصیص ({remaining:,.0f} ریال) است.")
                    )

            # تنظیم فلگ‌ها
            if self.status in ['APPROVED', 'PAID'] and not self.is_locked:
                if self.status == 'PAID':
                    create_budget_transaction(
                        allocation=self.project_budget_allocation,
                        transaction_type='CONSUMPTION',
                        amount=self.amount,
                        related_obj=self,
                        created_by=self.created_by,
                        description=f"Tankhah {self.number} for project {self.project.id}",
                        transaction_id=f"TX-TNK-CONS-{self.number}"
                    )
                    self.is_locked = True

            if self.status == 'REJECTED':
                initial_stage = WorkflowStage.objects.order_by('order').first()
                if self.current_stage == initial_stage:
                    factors = Factor.objects.filter(tankhah=self, is_finalized=True)
                    factors.update(is_finalized=False, locked=False)
                    target_allocation = BudgetAllocation.objects.filter(organization__is_core=True).first()
                    if target_allocation:
                        create_budget_transaction(
                            allocation=self.project_budget_allocation,
                            transaction_type='TRANSFER',
                            amount=self.amount,
                            related_obj=self,
                            created_by=self.created_by,
                            description=f"انتقال بودجه به دلیل رد تنخواه {self.number}",
                            transaction_id=f"TX-TNK-XFER-{self.number}",
                            target_allocation=target_allocation
                        )
                    else:
                        create_budget_transaction(
                            allocation=self.project_budget_allocation,
                            transaction_type='RETURN',
                            amount=self.amount,
                            related_obj=self,
                            created_by=self.created_by,
                            description=f"بازگشت بودجه به دلیل رد تنخواه {self.number}",
                            transaction_id=f"TX-TNK-RET-{self.number}"
                        )
                    self.is_locked = False

            # super().save(*args, **kwargs)
            # بررسی قفل تخصیص
            is_active = False if (
                    self.project_budget_allocation and (
                    self.project_budget_allocation.is_locked or
                    self.project_budget_allocation.budget_period.is_locked
            )
            ) else True
            self.is_active = is_active

            super().save(*args, **kwargs)
            logger.info(f"Tankhah saved 👍with ID: {self.pk}")

    def generate_number(self):
        sep = NUMBER_SEPARATOR
        import jdatetime
        jalali_date = jdatetime.datetime.fromgregorian(datetime=self.date).strftime('%Y%m%d')
        org_code = self.organization.code
        project_code = self.project.code if self.project else 'NOPRJ'

        with transaction.atomic():
            max_serial = Tankhah.objects.filter(
                organization=self.organization,
                date__date=self.date.date()
            ).aggregate(Max('number'))['number__max']
            serial = 1 if not max_serial else int(max_serial.split(sep)[-1]) + 1
            new_number = f"TNKH{sep}{jalali_date}{sep}{org_code}{sep}{project_code}{sep}{serial:03d}"
            while Tankhah.objects.filter(number=new_number).exists():
                serial += 1
                new_number = f"TNKH{sep}{jalali_date}{sep}{org_code}{sep}{project_code}{sep}{serial:03d}"
            return new_number

    def process_approved_factors(self, user):
        with transaction.atomic():
            approved_factors = self.factors.filter(status='APPROVED', is_locked=False)
            processed_count = 0
            for factor in approved_factors:
                if self.get_remaining_budget() < factor.amount:
                    logger.warning(f"Insufficient budget for factor {factor.number} in tankhah {self.number}")
                    continue
                factor.status = 'PAID'
                factor.is_locked = True
                factor.save()
                create_budget_transaction(
                    allocation=self.project_budget_allocation.budget_allocation,
                    transaction_type='CONSUMPTION',
                    amount=factor.amount,
                    related_obj=factor,
                    created_by=user,
                    description=f"پرداخت فاکتور {factor.number} از تنخواه {self.number}",
                    transaction_id=f"TX-FAC-PAY-{factor.number}"
                )
                FactorHistory.objects.create(
                    factor=factor,
                    change_type=FactorHistory.ChangeType.STATUS_CHANGE,
                    changed_by=user,
                    old_data={'status': 'APPROVED'},
                    new_data={'status': 'PAID'},
                    description=f"پرداخت فاکتور از تنخواه {self.number}"
                )
                processed_count += 1
            logger.info(f"Processed {processed_count} approved factors for tankhah {self.number}")
            return processed_count


class TankhActionType(models.Model):
    action_type = models.CharField(max_length=25, verbose_name=_('انواع  اقدام'))
    class Meta:
        verbose_name=_('انواع اقدام')
        verbose_name_plural =  _('انواع اقدام ')
        default_permissions = ()
        permissions = [
            ('TankhActionType_add','افزودن نوع اقدام'),
            ('TankhActionType_view','نمایش نوع اقدام'),
            ('TankhActionType_update','ویرایش نوع اقدام'),
            ('TankhActionType_delete','حذف نوع اقدام'),
        ]
    def __str__(self):
        return self.action_type
class TankhahAction(models.Model):
    # ACTION_TYPES = (
    #     ('ISSUE_PAYMENT_ORDER', _('صدور دستور پرداخت')),
    #     ('FINALIZE', _('اتمام')),
    #     ('INSURANCE', _('ثبت بیمه')),
    #     ('CUSTOM', _('سفارشی')),
    # )

    tankhah = models.ForeignKey(Tankhah, on_delete=models.CASCADE, related_name='actions', verbose_name=_("تنخواه"))
    action_type = models.CharField(max_length=50, choices=TankhActionType, verbose_name=_("نوع اقدام"))
    amount = models.DecimalField(max_digits=25, decimal_places=2, null=True, blank=True, verbose_name=_("مبلغ (برای پرداخت)"))
    stage = models.ForeignKey( WorkflowStage , on_delete=models.PROTECT, verbose_name=_("مرحله"))
    post = models.ForeignKey(  Post , on_delete=models.SET_NULL, null=True, verbose_name=_("پست انجام‌دهنده"))
    user = models.ForeignKey( CustomUser , on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    reference_number = models.CharField(max_length=50, blank=True, verbose_name=_("شماره مرجع"))

    action_type = models.ForeignKey('budgets.TransactionType' , on_delete=models.SET_NULL, null=True,verbose_name=_("نوع اقدام"))
    # جایگزینی ACTION_TYPES با TransactionType


    def save(self, *args, **kwargs):
        # چک کن که پست مجاز به این اقدام باشه
        from core.models import PostAction
        if not PostAction.objects.filter(
            post=self.post, stage=self.stage, action_type=self.action_type
        ).exists():
            raise ValueError(f"پست {self.post} مجاز به {self.action_type} در این مرحله نیست")
        # برای دستور پرداخت، چک کن بودجه
        if self.action_type == 'ISSUE_PAYMENT_ORDER' and self.amount:
            if self.amount > self.tankhah.remaining_budget:
                raise ValueError("مبلغ دستور پرداخت بیشتر از بودجه باقیمانده است")
            self.tankhah.remaining_budget -= self.amount
            self.tankhah.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.action_type} برای {self.tankhah} ({self.created_at})"

    class Meta:
        verbose_name = _("اقدام تنخواه")
        verbose_name_plural = _("اقدامات تنخواه")
        permissions = [
            ('TankhahAction_view', 'نمایش اقدامات تنخواه'),
            ('TankhahAction_add', 'افزودن اقدامات تنخواه'),
            ('TankhahAction_update', 'بروزرسانی اقدامات تنخواه'),
            ('TankhahAction_delete', 'حذف اقدامات تنخواه'),
        ]
class FactorDocument(models.Model):
    factor = models.ForeignKey('Factor', on_delete=models.CASCADE, related_name='documents', verbose_name=_("فاکتور"))
    # file = models.FileField(upload_to='factors/documents/%Y/%m/%d/', verbose_name=_("فایل پیوست"))
    file = models.FileField(upload_to=factor_document_upload_path, verbose_name=_("فایل پیوست"))
    file_size = models.IntegerField(null=True, blank=True, verbose_name=_("حجم فایل (بایت)"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ بارگذاری"))
    uploaded_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, verbose_name=_("آپلود شده توسط"))

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return f"سند برای فاکتور {self.factor.number} ({self.uploaded_at})"

    class Meta:
        verbose_name = _("سند فاکتور")
        verbose_name_plural = _("اسناد فاکتور")
        default_permissions = ()
        permissions = [
            ('FactorDocument_add','افزودن سند فاکتور'),
            ('FactorDocument_update','بروزرسانی سند فاکتور'),
            ('FactorDocument_view','نمایش سند فاکتور'),
            ('FactorDocument_delete','حــذف سند فاکتور'),
        ]
class Factor(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', _('پیش‌نویس')),
        ('PENDING', _('در انتظار تأیید')),
        ('APPROVED', _('تأیید شده')),
        ('REJECTED', _('رد شده')),
        ('PAID', _('پرداخت شده')),
    )

    number = models.CharField(max_length=100, blank=True, verbose_name=_("شماره فاکتور"))
    tankhah = models.ForeignKey('Tankhah', on_delete=models.PROTECT, related_name='factors', verbose_name=_("تنخواه"))
    date = models.DateField(default=timezone.now, verbose_name=_("تاریخ"))
    amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_('مبلغ فاکتور'), default=0)
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))
    approved_by = models.ManyToManyField(CustomUser, blank=True, verbose_name=_("تأییدکنندگان"))
    is_finalized = models.BooleanField(default=False, verbose_name=_("نهایی شده"))
    locked = models.BooleanField(default=False, verbose_name="قفل شده")
    locked_by_stage = models.ForeignKey(WorkflowStage, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("قفل شده توسط مرحله"))
    budget = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name=_("بودجه تخصیصی"))
    remaining_budget = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name=_("بودجه باقیمانده"))
    created_by = models.ForeignKey('accounts.CustomUser',related_name='CustomUser_related', on_delete=models.SET_NULL, null=True, verbose_name=_("ایجادکننده"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    is_emergency = models.BooleanField(default=False, verbose_name=_("اضطراری"))
    category = models.ForeignKey('ItemCategory', on_delete=models.SET_NULL, null=True, blank=False, verbose_name=_("دسته‌بندی"))
    is_locked = models.BooleanField(default=False,verbose_name=_('قفل شود'))


    def unlock(self, user):
        """باز کردن قفل فاکتور توسط کاربر مجاز (مثل BOARD)"""
        if not user.has_perm('tankhah.factor_unlock'):
            raise PermissionError(_("کاربر مجوز باز کردن فاکتور را ندارد."))
        if not self.is_locked:
            return
        self.is_locked = False
        self.status = 'PENDING'  # بازگشت به وضعیت در انتظار تأیید
        self.save()
        ApprovalLog.objects.create(
            factor=self,
            action='APPROVE',
            stage=self.tankhah.current_stage,
            user=user,
            post=user.userpost_set.filter(is_active=True).first().post,
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id,
            comment=f"فاکتور {self.number} توسط {user.username} باز شد.",
            changed_field='is_locked'
        )
        logger.info(f"Factor {self.number} unlocked by {user.username}")
    def revert_to_pending(self, user):
        """بازگرداندن فاکتور ردشده به وضعیت در انتظار تأیید"""
        if self.status != 'REJECTED':
            return
        with transaction.atomic():
            self.status = 'PENDING'
            self.is_locked = False
            self.save()
            ApprovalLog.objects.create(
                factor=self,
                action='STAGE_CHANGE',
                stage=self.tankhah.current_stage,
                user=user,
                post=user.userpost_set.filter(is_active=True).first().post,
                content_type=ContentType.objects.get_for_model(self),
                object_id=self.id,
                comment=f"فاکتور {self.number} به وضعیت در انتظار تأیید بازگشت.",
                changed_field='status'
            )
            FactorHistory.objects.create(
                factor=self,
                change_type=FactorHistory.ChangeType.STATUS_CHANGE,
                changed_by=user,
                old_data={'status': 'REJECTED'},
                new_data={'status': 'PENDING'},
                description=f"بازگشت فاکتور به وضعیت در انتظار تأیید"
            )
            logger.info(f"Factor {self.number} reverted to PENDING by {user.username}")
    def get_remaining_budget(self):
        from budgets.budget_calculations import get_factor_remaining_budget
        return get_factor_remaining_budget(self)
    def get_items_total(self):
        if self.pk:
            total = self.items.aggregate(total=Sum('amount'))['total'] or Decimal('0')
            return total
        return Decimal('0')
    def total_amount(self):
        if self.pk:
            return self.get_items_total()
        return Decimal('0')
    def generate_number(self):
        """تولید شماره یکتا برای فاکتور با استفاده از تاریخ شمسی"""
        sep = '-'  # استفاده از جداکننده ثابت
        from jdatetime import date as jdate
        date_str = jdate.fromgregorian(date=self.date).strftime('%Y%m%d')
        org_code = self.tankhah.organization.code if self.tankhah and self.tankhah.organization else 'NOORG'
        tankhah_number = self.tankhah.number if self.tankhah else 'NOTNKH'

        with transaction.atomic():
            max_serial = Factor.objects.filter(
                tankhah__organization=self.tankhah.organization,
                date=self.date
            ).aggregate(models.Max('number'))['number__max']

            serial = 1
            if max_serial:
                last_number = max_serial.split(sep)[-1]
                try:
                    serial = int(last_number) + 1
                except ValueError:
                    pass

            new_number = f"FAC{sep}{tankhah_number}{sep}{date_str}{sep}{org_code}{sep}{serial:04d}"
            while Factor.objects.filter(number=new_number).exists():
                serial += 1
                new_number = f"FAC{sep}{tankhah_number}{sep}{date_str}{sep}{org_code}{sep}{serial:04d}"
            return new_number
    def clean(self):
        super().clean()
        if self.amount < 0:
            raise ValidationError(_("مبلغ فاکتور نمی‌تواند منفی باشد."))
        if not self.category:
            raise ValidationError(_("دسته‌بندی الزامی است."))
        if self.tankhah and (
                self.tankhah.status not in ['DRAFT', 'PENDING'] ): #or not self.tankhah.workflow_stage.is_initial
            raise ValidationError(_("تنخواه انتخاب‌شده در وضعیت یا مرحله مجاز نیست."))

        #
        # total = self.total_amount()
        # errors = {}
        # if self.pk and total <= 0:
        #     raise ValidationError(_("مبلغ فاکتور باید مثبت باشد."))
        #
        # if abs(self.amount - total) > 0.01:
        #     logger.warning(f"Factor {self.number}: amount ({self.amount}) != items total ({total})")
        #     raise ValidationError(_("مبلغ فاکتور با مجموع آیتم‌ها همخوانی ندارد."))
        #
        # if self.tankhah:
        #     tankhah_remaining = get_tankhah_remaining_budget(self.tankhah)
        #     if total > tankhah_remaining:
        #         raise ValidationError(
        #             _(f"مبلغ فاکتور ({total:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده تنخواه ({tankhah_remaining:,.0f} ریال) باشد.")
        #         )
        #
        # if not self.category:
        #     errors['category'] = ValidationError(_('دسته‌بندی الزامی است.'), code='category_required')
        # if errors:
        #     raise ValidationError(errors)


    def save(self, *args, **kwargs):
        """ذخیره فاکتور با مدیریت تراکنش‌ها، اعلان‌ها و تاریخچه تغییرات"""
        current_user = kwargs.pop('current_user', None)

        from budgets.models import BudgetTransaction
        with transaction.atomic():
            if not self.number:
                self.number = self.generate_number()
                logger.debug(f"تولید شماره فاکتور: {self.number}")

            # فقط در صورت نیاز به اعتبارسنجی خاص مدل، clean را فراخوانی کنید
            original = None
            if self.pk:
                original = Factor.objects.get(pk=self.pk)

            # چک کردن قفل بودن تخصیص بودجه یا دوره بودجه
            if self.tankhah and self.tankhah.project_budget_allocation:
                budget_allocation = self.tankhah.project_budget_allocation
                budget_period = budget_allocation.budget_period
                if self.status != 'PAID' and (budget_allocation.is_locked or budget_period.is_locked):
                    logger.error(f"فاکتور {self.number} به دلیل قفل بودن تخصیص یا دوره بودجه نمی‌تواند ثبت شود")
                    raise ValidationError(_("نمی‌توان فاکتور جدید ثبت کرد، تخصیص یا دوره قفل شده است."))
            else:
                logger.warning(
                    f"هیچ تخصیص بودجه‌ای برای تنخواه {self.tankhah.number if self.tankhah else 'نامشخص'} یافت نشد")
            # New
            budget_allocation = None
            if self.tankhah:
                try:
                    budget_allocation = self.tankhah.project_budget_allocation
                except AttributeError:
                    logger.warning(f"تنخواه {self.tankhah.number} فاقد project_budget_allocation است")
                except Exception as e:
                    logger.warning(f"خطا در دریافت تخصیص بودجه برای تنخواه {self.tankhah.number}: {str(e)}")

            if budget_allocation:
                budget_period = budget_allocation.budget_period
                if self.status != 'PAID' and (budget_allocation.is_locked or budget_period.is_locked):
                    logger.error(f"فاکتور {self.number} به دلیل قفل بودن تخصیص یا دوره بودجه نمی‌تواند ثبت شود")
                    raise ValidationError(_("نمی‌توان فاکتور جدید ثبت کرد، تخصیص یا دوره قفل شده است."))
            else:
                logger.warning(
                    f"هیچ تخصیص بودجه‌ای برای تنخواه {self.tankhah.number if self.tankhah else 'نامشخص'} یافت نشد")

            # به‌روزرسانی بودجه و وضعیت قفل
            if original and self.status != original.status:
                if self.status == 'PAID' and not self.is_locked:
                    create_budget_transaction(
                        allocation=self.tankhah.project_budget_allocation,
                        transaction_type='CONSUMPTION',
                        amount=self.amount,
                        related_obj=self,
                        # created_by=self.created_by,
                        created_by=current_user or self.created_by,
                        description=f"مصرف بودجه توسط فاکتور {self.number}",
                        transaction_id=f"TX-FAC-{self.number}"
                    )
                    self.is_locked = True
                elif self.status == 'REJECTED' and original.status in ['APPROVED',
                                                                           'PAID'] and self.is_locked and budget_allocation:
                    BudgetTransaction.objects.create(
                        allocation=budget_allocation,
                        transaction_type='RETURN',
                        amount=self.amount,
                        related_obj=self,
                        created_by=current_user or self.created_by,
                        description=f"بازگشت بودجه به دلیل رد فاکتور {self.number}",
                        transaction_id=f"TX-FAC-RET-{self.number}"
                    )
                    self.is_locked = False

            # اجرای اعتبارسنجی کامل
            self.full_clean()
            super().save(*args, **kwargs)

            # ثبت ApprovalLog فقط در صورت تغییر وضعیت یا فیلدها
            if original and self.status != original.status and current_user:
                user_post = current_user.userpost_set.filter(end_date__isnull=True).first()
                if user_post:
                    action = 'APPROVE' if self.status in ['APPROVED', 'PAID'] else 'REJECT'
                    ApprovalLog.objects.create(
                        factor=self,
                        action=action,
                        stage=self.tankhah.current_stage if self.tankhah else None,
                        user=current_user,
                        post=user_post.post,
                        content_type=ContentType.objects.get_for_model(self),
                        object_id=self.id,
                        comment=f"تغییر وضعیت فاکتور به {self.get_status_display()} توسط {current_user.get_full_name()}",
                        changed_field='status'
                    )
                    logger.debug(f"ApprovalLog ثبت شد برای فاکتور {self.id}، اقدام: {action}")

            # if original:
            #     changed_fields = [field.name for field in self._meta.fields if
            #                       getattr(original, field.name) != getattr(self, field.name)]
            #     if changed_fields or self.status != original.status:
            #         from django.contrib.contenttypes.models import ContentType
            #         user_post = self.created_by.userpost_set.filter(is_active=True).first()
            #         if user_post:
            #             ApprovalLog.objects.create(
            #                 factor=self,
            #                 action='STAGE_CHANGE' if changed_fields else (
            #                     'APPROVE' if self.status in ['APPROVED', 'PAID'] else 'REJECT'),
            #                 stage=self.tankhah.current_stage,
            #                 user=self.created_by,
            #                 post=user_post.post,
            #                 content_type=ContentType.objects.get_for_model(self),
            #                 object_id=self.id,
            #                 comment=f"تغییر {'فیلدها' if changed_fields else 'وضعیت'} فاکتور به {self.get_status_display()}",
            #                 changed_field=', '.join(changed_fields) if changed_fields else None
            #             )

    def __str__(self):
        # اصلاح متد __str__ برای مدیریت tankhah=None
        tankhah_number = self.tankhah.number if self.tankhah else "تنخواه ندارد"
        return f"{self.number} ({tankhah_number})"
    class Meta:
        verbose_name = _("فاکتور")
        verbose_name_plural = _("فاکتورها")
        indexes = [
            models.Index(fields=['number', 'date', 'status', 'tankhah']),
        ]
        default_permissions = ()
        permissions = [
            ('factor_add', _('افزودن فاکتور')),
            ('factor_view', _('نمایش فاکتور')),
            ('factor_update', _('بروزرسانی فاکتور')),
            ('factor_delete', _('حذف فاکتور')),
            ('factor_approve', _('تأیید فاکتور')),
            ('factor_reject', _('رد فاکتور')),
            ('Factor_full_edit', _('دسترسی کامل به فاکتور')),
            ('factor_unlock', _('باز کردن فاکتور قفل‌شده')),

        ]

class FactorHistory(models.Model):
    class ChangeType(models.TextChoices):
        CREATION = 'CREATION', _('ایجاد')
        UPDATE = 'UPDATE', _('ویرایش')
        STATUS_CHANGE = 'STATUS_CHANGE', _('تغییر وضعیت')
        DELETION = 'DELETION', _('حذف')

    factor = models.ForeignKey('Factor', on_delete=models.CASCADE, related_name='history', verbose_name=_('فاکتور'))
    change_type = models.CharField(max_length=20, choices=ChangeType.choices, verbose_name=_('نوع تغییر'))
    changed_by = models.ForeignKey( CustomUser, on_delete=models.SET_NULL, null=True, verbose_name=_('تغییر توسط'))
    change_timestamp = models.DateTimeField(default=timezone.now, verbose_name=_('زمان تغییر'))
    old_data = models.JSONField(null=True, blank=True, verbose_name=_('داده‌های قبلی'))
    new_data = models.JSONField(null=True, blank=True, verbose_name=_('داده‌های جدید'))
    description = models.TextField(blank=True, verbose_name=_('توضیحات'))

    class Meta:
        verbose_name = _('تاریخچه فاکتور')
        verbose_name_plural = _('تاریخچه‌های فاکتور')
        ordering = ['-change_timestamp']

    def __str__(self):
        return f"{self.get_change_type_display()} برای فاکتور {self.factor.number} در {self.change_timestamp}"
#-----------------------------------------------
class FactorItem(models.Model):
    """  اقلام فاکتور """

    STATUS_CHOICES = (
        ('PENDING', _('در حال بررسی')),
        ('APPROVED', _('تأیید شده')),
        ('REJECTED', _('رد شده')),
        ('PAID', 'پرداخت شده'),
    )

    factor = models.ForeignKey(Factor, on_delete=models.CASCADE, related_name='items', verbose_name=_("فاکتور"))
    description = models.CharField(max_length=255, verbose_name=_("شرح ردیف"))
    amount = models.DecimalField(max_digits=25, default=0, decimal_places=2, verbose_name=_("مبلغ"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("وضعیت"))
    quantity = models.DecimalField(max_digits=25, default=1, decimal_places=2, verbose_name=_("تعداد"))
    unit_price = models.DecimalField(max_digits=25, decimal_places=2, blank=True, null=True,verbose_name=_("قیمت واحد"))
    min_stage_order = models.IntegerField(default=1, verbose_name=_("حداقل ترتیب مرحله"),help_text=_("این نوع تراکنش فقط در این مرحله یا بالاتر مجاز است")  , editable=False)
    # Optional: Timestamps for tracking
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان ایجاد"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("زمان آخرین ویرایش"))


    def clean(self):
        """
        Basic model-level validation. Avoid complex calculations here that rely
        on related models or states that might not be fully set yet.
        Focus on individual field constraints.
        """
        super().clean() # Call parent clean method first

        errors = {}

        # 1. Validate Quantity
        if self.quantity is not None and self.quantity <= Decimal('0'):
            errors['quantity'] = ValidationError(
                _('تعداد/مقدار باید بزرگ‌تر از صفر باشد.'), code='quantity_not_positive'
            )

        # 2. Validate Unit Price (if provided)
        if self.unit_price is not None and self.unit_price < Decimal('0'):
            # Allow zero unit price? Maybe. Disallow negative.
            errors['unit_price'] = ValidationError(
                _('قیمت واحد نمی‌تواند منفی باشد.'), code='unit_price_negative'
            )
            # Note: We don't raise 'unit_price must be positive' here,
            # because the final 'amount' validation in save() is more robust.

        # 3. Validate Amount (basic check for negative, final check in save)
        if self.amount is not None and self.amount < Decimal('0'):
             errors['amount'] = ValidationError(
                 _('مبلغ کل ردیف نمی‌تواند منفی باشد.'), code='amount_negative'
             )

        # Raise all collected errors at once
        if errors:
            raise ValidationError(errors)

        # Note: Comparison between amount, unit_price, and quantity is *not* done here
        # because self.amount might still hold its default value (0) before save calculates it.


    def save(self, *args, **kwargs):
        """ذخیره آیتم با محاسبه مبلغ و اعتبارسنجی ساده"""
        logger.debug(f"Starting FactorItem save for pk={self.pk}. Qty={self.quantity}, UnitPrice={self.unit_price}, Amount={self.amount}")

        # محاسبه مبلغ
        if self.unit_price is not None and self.quantity is not None:
            self.amount = self.quantity * self.unit_price
            logger.info(f"Calculated amount for FactorItem pk={self.pk}: {self.amount}")
        elif self.amount is None:
            logger.warning(f"Amount not provided and cannot be calculated for FactorItem pk={self.pk}")
            self.amount = Decimal('0')
         # اعتبارسنجی
        self.clean()

        # ذخیره
        super().save(*args, **kwargs)
        logger.info(f"FactorItem saved successfully (pk={self.pk}). Amount={self.amount}, Status={self.status}")



    def __str__(self):
        """String representation of the FactorItem."""
        # Format amount with commas for readability
        try:
            # Ensure amount is a Decimal before formatting
            amount_str = f"{self.amount:,.2f}" if isinstance(self.amount, Decimal) else str(self.amount)
        except (TypeError, ValueError):
            amount_str = str(self.amount) # Fallback if formatting fails

        return f"{self.description or _('بدون شرح')} - {amount_str}"

    class Meta:
        verbose_name = _("ردیف فاکتور")
        verbose_name_plural = _("ردیف‌های فاکتور")
        ordering = ['factor', 'pk'] # Order by parent factor, then by creation order (pk)
        indexes = [
            models.Index(fields=['factor', 'status']), # Index for common filtering
        ]
        # Using standard Django permissions unless specific needs arise
        # default_permissions = ('add', 'change', 'delete', 'view')
        default_permissions = () # Disable default if using custom perms exclusively
        permissions = [
            ('FactorItem_add', _('افزودن ردیف فاکتور')),
            ('FactorItem_update', _('ویرایش ردیف فاکتور')),
            ('FactorItem_view', _('نمایش ردیف فاکتور')),
            ('FactorItem_delete', _('حذف ردیف فاکتور')),
            # Add specific permissions for status changes if needed
            ('FactorItem_approve', _('تأیید ردیف فاکتور')),
            ('FactorItem_reject', _('رد ردیف فاکتور')),
        ]
#--------------
class ApprovalLog(models.Model):
    ACTION_CHOICES = [
        ('APPROVE', 'تأیید'),
        ('REJECT', 'رد'),
        ('STAGE_CHANGE', 'تغییر مرحله'),
        ('NONE', 'هیچکدام'),
    ]
    tankhah  = models.ForeignKey(Tankhah, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("تنخواه"))
    factor = models.ForeignKey(Factor, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("فاکتور"))
    factor_item = models.ForeignKey(FactorItem, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_logs', verbose_name=_("ردیف فاکتور"))
    action = models.CharField(max_length=25, choices=ACTION_CHOICES, verbose_name=_("اقدام"))
    stage = models.ForeignKey('core.WorkflowStage', on_delete=models.PROTECT, verbose_name=_('مرحله'))
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, verbose_name=_("کاربر"))
    comment = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("زمان"))
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("تاریخ ایجاد"))
    post = models.ForeignKey('core.Post', on_delete=models.SET_NULL, null=True, verbose_name=_("پست تأییدکننده"))
    changed_field = models.CharField(max_length=50, blank=True, null=True, verbose_name="فیلد تغییر یافته")
    seen_by_higher = models.BooleanField(default=False, verbose_name=_("دیده‌شده توسط رده بالاتر"))
    seen_at = models.DateTimeField(null=True, blank=True, verbose_name=_("زمان دیده شدن"))
    action_type = models.CharField(max_length=50, blank=True, verbose_name=_("نوع اقدام"))
    # پشتیبانی از چندین نوع موجودیت با استفاده از GenericForeignKey
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=_("نوع موجودیت"))
    object_id = models.PositiveIntegerField(verbose_name=_("شناسه موجودیت"))
    content_object = GenericForeignKey('content_type', 'object_id')#GenericForeignKey در ApprovalLog استفاده کرده‌اید که بسیار خوب است و به شما اجازه می‌دهد ApprovalLog را به هر مدلی (از جمله PaymentOrder) مرتبط کنید.

    # -- برای بودجه
    def save(self, *args, **kwargs):
        """
        اعتبارسنجی قبل از ذخیره ApprovalLog
        """
        if self.pk is None:  # فقط برای رکوردهای جدید
            # بررسی دسترسی کاربر
            user_post = UserPost.objects.filter(
                user=self.user,
                end_date__isnull=True
            ).first()

            if not user_post:
                raise ValueError(f"کاربر {self.user.username} هیچ پست فعالی ندارد")

            # معافیت کاربران HQ یا سازمان core
            if getattr(self.user, 'is_hq', False) or user_post.post.organization.is_core:
                super().save(*args, **kwargs)
                return

            # تعیین entity_type بر اساس محتوا
            if self.factor_item:
                entity_type = 'FACTORITEM'
            elif self.factor:
                entity_type = 'FACTOR'
            elif self.content_type:
                entity_type = self.content_type.model.upper()
            else:
                entity_type = 'GENERAL'

            # بررسی وجود قانون دسترسی
            access_rule = AccessRule.objects.filter(
                organization=user_post.post.organization,
                stage=self.stage,
                action_type=self.action,
                entity_type=entity_type,
                min_level__lte=user_post.post.level,
                branch=user_post.post.branch or '',
                is_active=True
            ).first()

            if not access_rule:
                # اگر قانون مستقیم نداریم، بررسی کنیم آیا قانون کلی‌تری وجود دارد
                general_rule = AccessRule.objects.filter(
                    organization=user_post.post.organization,
                    stage=self.stage,
                    action_type=self.action,
                    entity_type__in=['FACTOR', 'FACTORITEM'],  # قوانین عمومی
                    min_level__lte=user_post.post.level,
                    is_active=True
                ).first()

                if not general_rule:
                    raise ValueError(
                        f"پست {user_post.post} مجاز به {self.action} در مرحله {self.stage} "
                        f"برای {entity_type} نیست - قانون دسترسی یافت نشد"
                    )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.action} ({self.date})"


    class Meta:
        verbose_name = _("تأیید")
        verbose_name_plural = _("تأییدات👍")
        default_permissions=()
        permissions = [
                    ('Approval_add','افزودن تأیید برای ثبت اقدامات تأیید یا رد '),
                    ('Approval_update','ویرایش تأیید برای ثبت اقدامات تأیید یا رد'),
                    ('Approval_delete','حــذف تأیید برای ثبت اقدامات تأیید یا رد'),
                    ('Approval_view','نمایش تأیید برای ثبت اقدامات تأیید یا رد'),
                ]
"""مشخص کردن کاربران یا نقش‌های مجاز برای هر مرحله"""
"""
توضیح:
این مدل مشخص می‌کند کدام پست‌ها در یک مرحله خاص می‌توانند به‌عنوان تأییدکننده برای تنخواه یا بودجه عمل کنند.
فیلد entity_type مشابه PostAction اضافه شده تا نوع موجودیت مشخص شود.
"""
class StageApprover(models.Model):
    stage = models.ForeignKey('core.WorkflowStage', on_delete=models.CASCADE, verbose_name=_('مرحله'))
    post = models.ForeignKey( 'core.Post', on_delete=models.CASCADE, verbose_name=_('پست مجاز'))  # فرض بر وجود مدل Post
    is_active = models.BooleanField(default=True, verbose_name="وضعیت فعال")
    entity_type = models.CharField(
        max_length=50,
        choices=(('TANKHAH', _('تنخواه')), ('BUDGET_ALLOCATION', _('تخصیص بودجه'))),
        default='TANKHAH',
        verbose_name=_("نوع موجودیت")
    )
    def __str__(self):
        return f"{self.post} - تأییدکننده برای {self.get_entity_type_display()} در {self.stage}"
        # return f"{self.stage} - {self.post}"

    class Meta:
        verbose_name = _('تأییدکننده مرحله')
        verbose_name_plural = _('تأییدکنندگان مرحله')
        unique_together = ('stage', 'post', 'entity_type')
        default_permissions=()
        permissions = [
            ('stageapprover__view','نمایش تأییدکننده مرحله'),
            ('stageapprover__add','افزودن تأییدکننده مرحله'),
            ('stageapprover__Update','بروزرسانی تأییدکننده مرحله'),
            ('stageapprover__delete','حــذف تأییدکننده مرحله'),
        ]
class TankhahFinalApproval(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('TankhahFinalApproval_view','دسترسی تایید یا رد تنخواه گردان ')
        ]
class ItemCategory(models.Model):
    """مقداردهی بر اساس دسته‌بندی (category):"""
    name = models.CharField(max_length=100, verbose_name=_("نام دسته‌بندی"))
    min_stage_order = models.IntegerField(default=1, verbose_name=_("حداقل ترتیب مرحله"))
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    def __str__(self):
        return self.name
    class Meta:
        verbose_name= "دسته بندی نوع هزینه کرد"
        verbose_name_plural= "دسته بندی نوع هزینه کرد"
        permissions = [
            ('ItemCategory_add','افزودن دسته بندی نوع هزینه کرد'),
            ('ItemCategory_update','ویرایش دسته بندی نوع هزینه کرد'),
            ('ItemCategory_view','نمایش دسته بندی نوع هزینه کرد'),
            ('ItemCategory_delete','حــذف دسته بندی نوع هزینه کرد'),
        ]

class DashboardView(TemplateView):
    template_name = 'tankhah/calc_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # تنخواه‌های در انتظار در هر مرحله
        from core.models import WorkflowStage
        stages = WorkflowStage.objects.all()
        for stage in stages:
            context[f'tankhah_pending_{stage.name}'] = Tankhah.objects.filter(
                current_stage=stage, status='PENDING'
            ).count()

        # تنخواه‌های نزدیک به مهلت
        context['tankhah_due_soon'] = Tankhah.objects.filter(
            due_date__lte=timezone.now() + timezone.timedelta(days=7),
            status='PENDING'
        ).count()

        # مجموع مبلغ تأییدشده در ماه جاری
        current_month = timezone.now().month
        context['total_approved_this_month'] = Tankhah.objects.filter(
            status='APPROVED', date__month=current_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        print(context['total_approved_this_month'])
        # آخرین فعالیت‌ها
        context['recent_approvals'] = ApprovalLog.objects.order_by('-timestamp')[:5]

        return context
class Dashboard_Tankhah(models.Model):
    class Meta:
        default_permissions = ()
        permissions = [
            ('Dashboard_Tankhah_view','دسترسی به داشبورد تنخواه گردان ')
        ]

