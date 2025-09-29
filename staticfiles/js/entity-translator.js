/**
 * مترجم کدهای موجودیت به فارسی
 */
window.EntityTranslator = {
    entities: {
        'FACTOR': 'فاکتور',
        'PAYMENTORDER': 'دستور پرداخت',
        'TANKHAH': 'تنخواه',
        'BUDGET': 'بودجه',
        'REPORTS': 'گزارشات',
        'GENERAL': 'عمومی'
    },
    
    actions: {
        'SUBMIT': 'ارسال',
        'APPROVE': 'تایید',
        'REJECT': 'رد',
        'PAY': 'پرداخت',
        'CANCEL': 'لغو',
        'EDIT': 'ویرایش',
        'DELETE': 'حذف',
        'VIEW': 'مشاهده'
    },
    
    /**
     * ترجمه کد موجودیت به فارسی
     */
    translateEntity: function(code) {
        return this.entities[code] || 'عمومی';
    },
    
    /**
     * ترجمه کد اقدام به فارسی
     */
    translateAction: function(code) {
        return this.actions[code] || 'سایر';
    },
    
    /**
     * اعمال ترجمه بر روی تمام عناصر صفحه
     */
    applyTranslations: function() {
        // ترجمه نوع موجودیت
        document.querySelectorAll('.entity-type').forEach(element => {
            const originalText = element.textContent.trim();
            const translatedText = this.translateEntity(originalText);
            element.textContent = translatedText;
        });
        
        // ترجمه نام اقدام
        document.querySelectorAll('.action-name').forEach(element => {
            const originalText = element.textContent.trim();
            const translatedText = this.translateAction(originalText);
            element.textContent = translatedText;
        });
    }
};

// اجرای خودکار پس از بارگذاری صفحه
document.addEventListener('DOMContentLoaded', function() {
    EntityTranslator.applyTranslations();
});
