// انتخاب همه برای تأیید گروهی
document.addEventListener('DOMContentLoaded', function() {
    const selectAll = document.getElementById('select-all');
    if (selectAll) {
        selectAll.addEventListener('click', function() {
            const checkboxes = document.getElementsByName('factor_ids');
            checkboxes.forEach(checkbox => {
                if (!checkbox.disabled) {
                    checkbox.checked = this.checked;
                }
            });
        });
    }
});

// اعتبارسنجی فرم رد فاکتور
function validateRejectForm() {
    const reason = document.querySelector('textarea[name="rejected_reason"]');
    if (reason && reason.value.length < 10) {
        alert('دلیل رد باید حداقل 10 کاراکتر باشد.');
        return false;
    }
    return true;
}

// محاسبه مبلغ آیتم‌ها در فرم
document.addEventListener('DOMContentLoaded', function() {
    const formset = document.getElementById('item-formset');
    if (formset) {
        formset.addEventListener('input', function(e) {
            if (e.target.name.includes('quantity') || e.target.name.includes('unit_price')) {
                const row = e.target.closest('tr');
                const quantity = row.querySelector('[name$="quantity"]').value;
                const unitPrice = row.querySelector('[name$="unit_price"]').value;
                const amountField = row.querySelector('[name$="amount"]');
                if (quantity && unitPrice) {
                    amountField.value = (parseFloat(quantity) * parseFloat(unitPrice)).toFixed(2);
                }
            }
        });
    }
});

// WebSocket برای اعلان‌های Real-Time
  const ws = new WebSocket('ws://' + window.location.host + '/ws/notifications/');
    ws.onmessage = function(e) {
        const data = JSON.parse(e.data);
        const alertDiv = document.createElement('div');
        let alertClass = 'alert-info';
        if (data.priority === 'HIGH') {
            alertClass = 'alert-danger';
        } else if (data.priority === 'MEDIUM') {
            alertClass = 'alert-warning';
        }
        alertDiv.className = `alert ${alertClass} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${data.message} (${data.entity_type} - ${data.action})
            <br><small>${new Date(data.timestamp).toLocaleString('fa-IR')}</small>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container').prepend(alertDiv);
    };