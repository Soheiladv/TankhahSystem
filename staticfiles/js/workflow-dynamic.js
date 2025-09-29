/**
 * تنظیمات پویا برای گردش کار
 * بدون هاردکد - کاملاً قابل تنظیم
 */

// تنظیمات مرکزی برای رنگ‌بندی و آیکون‌ها
window.WorkflowConfig = {
    // تنظیمات اقدامات
    actions: {
        'SUBMIT': { 
            rowClass: 'table-primary', 
            icon: 'fas fa-paper-plane', 
            color: 'text-primary',
            label: 'ارسال'
        },
        'APPROVE': { 
            rowClass: 'table-success', 
            icon: 'fas fa-check-circle', 
            color: 'text-success',
            label: 'تایید'
        },
        'REJECT': { 
            rowClass: 'table-danger', 
            icon: 'fas fa-times-circle', 
            color: 'text-danger',
            label: 'رد'
        },
        'PAY': { 
            rowClass: 'table-warning', 
            icon: 'fas fa-money-bill-wave', 
            color: 'text-warning',
            label: 'پرداخت'
        },
        'CANCEL': { 
            rowClass: 'table-secondary', 
            icon: 'fas fa-ban', 
            color: 'text-secondary',
            label: 'لغو'
        },
        'EDIT': { 
            rowClass: 'table-info', 
            icon: 'fas fa-edit', 
            color: 'text-info',
            label: 'ویرایش'
        },
        'DELETE': { 
            rowClass: 'table-dark', 
            icon: 'fas fa-trash', 
            color: 'text-dark',
            label: 'حذف'
        }
    },
    
    // تنظیمات انواع موجودیت
    entities: {
        'FACTOR': { 
            badge: 'bg-info', 
            icon: 'fas fa-file-invoice',
            label: 'فاکتور'
        },
        'PAYMENTORDER': { 
            badge: 'bg-primary', 
            icon: 'fas fa-credit-card',
            label: 'دستور پرداخت'
        },
        'TANKHAH': { 
            badge: 'bg-warning', 
            icon: 'fas fa-wallet',
            label: 'تنخواه'
        },
        'BUDGET': { 
            badge: 'bg-success', 
            icon: 'fas fa-chart-pie',
            label: 'بودجه'
        },
        'REPORTS': { 
            badge: 'bg-secondary', 
            icon: 'fas fa-chart-bar',
            label: 'گزارشات'
        },
        'GENERAL': { 
            badge: 'bg-light text-dark', 
            icon: 'fas fa-file',
            label: 'عمومی'
        }
    },
    
    // تنظیمات پیش‌فرض برای موارد نامشخص
    defaults: {
        action: {
            rowClass: 'table-light',
            icon: 'fas fa-cog',
            color: 'text-muted',
            label: 'سایر'
        },
        entity: {
            badge: 'bg-secondary',
            icon: 'fas fa-file',
            label: 'نامشخص'
        }
    }
};

/**
 * اعمال تنظیمات پویا بر روی ردیف‌های جدول
 */
function applyDynamicStyling() {
    document.querySelectorAll('.workflow-row').forEach(row => {
        const actionCode = row.dataset.actionCode;
        const entityType = row.dataset.entityType;
        
        // تنظیم کلاس ردیف بر اساس نوع اقدام
        const actionConfig = WorkflowConfig.actions[actionCode] || WorkflowConfig.defaults.action;
        row.className = `workflow-row ${actionConfig.rowClass}`;
        
        // تنظیم آیکون و رنگ اقدام
        const actionIcon = row.querySelector('.action-icon');
        const actionColor = row.querySelector('.action-color');
        
        if (actionIcon) {
            actionIcon.className = `action-icon me-2 ${actionConfig.color}`;
            actionIcon.classList.add(...actionConfig.icon.split(' '));
        }
        
        if (actionColor) {
            actionColor.className = `action-color ${actionConfig.color}`;
        }
        
        // تنظیم badge موجودیت
        const entityConfig = WorkflowConfig.entities[entityType] || WorkflowConfig.defaults.entity;
        const entityBadge = row.querySelector('.entity-badge');
        const entityIcon = row.querySelector('.entity-icon');
        
        if (entityBadge) {
            entityBadge.className = `badge ${entityConfig.badge} me-2`;
        }
        
        if (entityIcon) {
            entityIcon.className = `entity-icon me-1`;
            entityIcon.classList.add(...entityConfig.icon.split(' '));
        }
    });
}

/**
 * تولید راهنمای رنگ‌بندی پویا
 */
function generateColorGuide() {
    const colorGuide = document.getElementById('colorGuide');
    if (!colorGuide) return;
    
    let guideHTML = '';
    
    // تولید راهنمای اقدامات
    Object.keys(WorkflowConfig.actions).forEach(actionCode => {
        const config = WorkflowConfig.actions[actionCode];
        guideHTML += `
            <div class="col-md-2 col-sm-4 col-6 mb-2">
                <div class="d-flex align-items-center">
                    <div class="color-indicator ${config.rowClass} me-2"></div>
                    <small><strong>${config.label}</strong></small>
                </div>
            </div>
        `;
    });
    
    // اضافه کردن "سایر"
    const defaultConfig = WorkflowConfig.defaults.action;
    guideHTML += `
        <div class="col-md-2 col-sm-4 col-6 mb-2">
            <div class="d-flex align-items-center">
                <div class="color-indicator ${defaultConfig.rowClass} me-2"></div>
                <small><strong>${defaultConfig.label}</strong></small>
            </div>
        </div>
    `;
    
    colorGuide.innerHTML = guideHTML;
}

/**
 * اضافه کردن اقدام جدید به تنظیمات
 */
function addActionConfig(actionCode, config) {
    WorkflowConfig.actions[actionCode] = {
        rowClass: config.rowClass || 'table-light',
        icon: config.icon || 'fas fa-cog',
        color: config.color || 'text-muted',
        label: config.label || actionCode
    };
}

/**
 * اضافه کردن نوع موجودیت جدید به تنظیمات
 */
function addEntityConfig(entityType, config) {
    WorkflowConfig.entities[entityType] = {
        badge: config.badge || 'bg-secondary',
        icon: config.icon || 'fas fa-file',
        label: config.label || entityType
    };
}

/**
 * دریافت تنظیمات یک اقدام
 */
function getActionConfig(actionCode) {
    return WorkflowConfig.actions[actionCode] || WorkflowConfig.defaults.action;
}

/**
 * دریافت تنظیمات یک نوع موجودیت
 */
function getEntityConfig(entityType) {
    return WorkflowConfig.entities[entityType] || WorkflowConfig.defaults.entity;
}

/**
 * به‌روزرسانی تنظیمات و اعمال مجدد
 */
function updateConfig() {
    applyDynamicStyling();
    generateColorGuide();
}

/**
 * بارگذاری تنظیمات از فایل JSON
 */
async function loadConfigFromJSON() {
    try {
        const response = await fetch('/static/config/workflow-config.json');
        const config = await response.json();
        
        // به‌روزرسانی تنظیمات
        Object.assign(WorkflowConfig, config);
        
        // اعمال تنظیمات جدید
        updateConfig();
    } catch (error) {
        console.warn('خطا در بارگذاری تنظیمات JSON، از تنظیمات پیش‌فرض استفاده می‌شود:', error);
        // استفاده از تنظیمات پیش‌فرض
        generateColorGuide();
        applyDynamicStyling();
    }
}

// اجرای خودکار پس از بارگذاری صفحه
document.addEventListener('DOMContentLoaded', function() {
    // تلاش برای بارگذاری تنظیمات از JSON
    loadConfigFromJSON();
});
