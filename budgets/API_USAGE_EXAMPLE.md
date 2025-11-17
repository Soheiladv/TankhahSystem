# نحوه استفاده از API محاسبات بودجه در ثبت فاکتور

## ✅ هماهنگی با SystemSettings

API های محاسباتی (`TankhahCalculationsAPI`) به طور خودکار با `SystemSettings` هماهنگ هستند:

- اگر `create_budget_commitment_on_factor_draft = True`: از **BudgetTransaction** استفاده می‌کند
- اگر `create_budget_commitment_on_factor_draft = False`: از روش **Factor-based** استفاده می‌کند

## 📍 آدرس API

```
POST /api/calculations/tankhah/
```

## 📝 مثال استفاده در JavaScript (فرم ثبت فاکتور)

```javascript
// مثال: بررسی بودجه باقی‌مانده هنگام انتخاب تنخواه
function checkTankhahBudget(tankhahId) {
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch('/api/calculations/tankhah/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            'tankhah_id': tankhahId,
            'calculation_type': 'remaining'  // یا 'all' برای همه اطلاعات
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error('خطا:', data.error);
            return;
        }
        
        const remaining = data.result.remaining_budget;
        const method = data.result.system_settings_info.method;
        
        console.log('بودجه باقی‌مانده:', remaining);
        console.log('روش محاسبه:', method);
        console.log('تنظیمات سیستم:', data.result.system_settings_info);
        
        // نمایش در UI
        document.getElementById('remaining-budget-display').textContent = 
            new Intl.NumberFormat('fa-IR').format(remaining) + ' ریال';
            
        // اگر بودجه کافی نیست، نمایش هشدار
        const factorAmount = parseFloat(document.getElementById('id_amount').value || 0);
        if (factorAmount > remaining) {
            alert('مبلغ فاکتور بیشتر از بودجه باقی‌مانده است!');
        }
    })
    .catch(error => {
        console.error('خطا در دریافت بودجه:', error);
    });
}

// فراخوانی هنگام تغییر تنخواه
document.getElementById('id_tankhah').addEventListener('change', function() {
    const tankhahId = this.value;
    if (tankhahId) {
        checkTankhahBudget(tankhahId);
    }
});
```

## 📝 مثال استفاده در Python (Django View)

```python
# در view ثبت فاکتور می‌توانید از API استفاده کنید:
import requests
from django.conf import settings

def check_budget_via_api(tankhah_id):
    """
    بررسی بودجه از طریق API
    """
    url = f'{settings.BASE_URL}/api/calculations/tankhah/'
    
    response = requests.post(
        url,
        json={
            'tankhah_id': tankhah_id,
            'calculation_type': 'remaining'
        },
        headers={
            'Authorization': f'Token {user_token}'  # اگر از Token استفاده می‌کنید
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data['result']['remaining_budget']
    else:
        return None
```

## ✅ استفاده فعلی (مستقیم از توابع)

در حال حاضر در فرم ثبت فاکتور (`form_Nfactor.py`) مستقیماً از توابع استفاده می‌شود:

```python
# در form_Nfactor.py خط 440
remaining_budget = get_tankhah_remaining_budget(tankhah)
```

این روش **درست** است چون:
1. ✅ توابع خودشان با SystemSettings هماهنگ هستند
2. ✅ سریع‌تر از فراخوانی HTTP است
3. ✅ خطای شبکه ندارد
4. ✅ کش بهینه استفاده می‌شود

## 🔄 اگر بخواهید از API استفاده کنید

برای استفاده از API در فرم ثبت فاکتور (مثلاً در JavaScript):

```javascript
// در template یا static file
$(document).ready(function() {
    $('#id_tankhah').on('change', function() {
        const tankhahId = $(this).val();
        if (!tankhahId) return;
        
        $.ajax({
            url: '/api/calculations/tankhah/',
            method: 'POST',
            headers: {
                'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()
            },
            data: JSON.stringify({
                tankhah_id: parseInt(tankhahId),
                calculation_type: 'remaining'
            }),
            contentType: 'application/json',
            success: function(data) {
                const remaining = data.result.remaining_budget;
                const remainingStr = data.result.remaining_budget_str;
                
                // نمایش بودجه باقی‌مانده
                $('#tankhah-remaining-budget').text(remainingStr);
                
                // بررسی مبلغ فاکتور
                const factorAmount = parseFloat($('#id_amount').val() || 0);
                if (factorAmount > remaining) {
                    $('#budget-warning').show().text(
                        `⚠️ مبلغ فاکتور بیشتر از بودجه باقی‌مانده است!`
                    );
                } else {
                    $('#budget-warning').hide();
                }
                
                // نمایش روش محاسبه
                const method = data.result.system_settings_info.method;
                $('#calculation-method').text(
                    method === 'transaction-based' 
                        ? 'محاسبه با BudgetTransaction' 
                        : 'محاسبه با Factor-based'
                );
            },
            error: function(xhr) {
                console.error('خطا در دریافت بودجه:', xhr.responseJSON);
            }
        });
    });
});
```

## 📊 پاسخ API

```json
{
    "tankhah_id": 123,
    "tankhah_name": "TK-1403-001",
    "calculation_type": "remaining",
    "filters": {},
    "result": {
        "remaining_budget": 5000000.0,
        "remaining_budget_str": "5,000,000.00",
        "system_settings_info": {
            "use_commitment": true,
            "method": "transaction-based",
            "description": "استفاده از BudgetTransaction برای محاسبات"
        }
    }
}
```

## ✅ خلاصه

1. **API با SystemSettings هماهنگ است** ✅
2. **توابع از SystemSettings استفاده می‌کنند** ✅
3. **در فرم ثبت فاکتور از توابع استفاده می‌شود** (روش فعلی درست است) ✅
4. **می‌توانید از API برای JavaScript/React استفاده کنید** ✅

