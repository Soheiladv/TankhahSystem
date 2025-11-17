/**
 * یکپارچه‌سازی API محاسبات بودجه در فرم ثبت فاکتور
 * 
 * این فایل نشان می‌دهد چگونه می‌توان از TankhahCalculationsAPI در فرم ثبت فاکتور استفاده کرد
 */

(function() {
    'use strict';

    /**
     * بررسی بودجه تنخواه از طریق API
     */
    function checkTankhahBudgetViaAPI(tankhahId) {
        if (!tankhahId) {
            return Promise.reject('شناسه تنخواه معتبر نیست');
        }

        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (!csrftoken) {
            console.error('CSRF token یافت نشد');
            return Promise.reject('CSRF token یافت نشد');
        }

        return fetch('/api/calculations/tankhah/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({
                'tankhah_id': parseInt(tankhahId),
                'calculation_type': 'all'  // دریافت همه اطلاعات بودجه
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            return data.result;
        });
    }

    /**
     * نمایش اطلاعات بودجه در UI
     */
    function displayBudgetInfo(budgetData) {
        const {
            total_budget_str = '0',
            remaining_budget,
            remaining_budget_str = '0',
            used_budget_str = '0',
            committed_budget_str = '0',
            available_budget_str = '0',
            system_settings_info
        } = budgetData;

        // نمایش بودجه باقی‌مانده
        const remainingDisplay = document.getElementById('display-remaining-budget');
        if (remainingDisplay) {
            remainingDisplay.textContent = remaining_budget_str.replace(/,/g, '');
        }

        // نمایش بودجه اولیه
        const initialDisplay = document.getElementById('display-initial-budget');
        if (initialDisplay) {
            initialDisplay.textContent = total_budget_str.replace(/,/g, '');
        }

        // نمایش روش محاسبه
        const methodInfo = system_settings_info || {};
        if (methodInfo.method === 'transaction-based') {
            console.log('✅ استفاده از BudgetTransaction برای محاسبات');
        } else {
            console.log('✅ استفاده از Factor-based برای محاسبات');
        }

        // محاسبه درصد استفاده
        const total = parseFloat(total_budget_str.replace(/,/g, '')) || 0;
        const remaining = parseFloat(remaining_budget_str.replace(/,/g, '')) || 0;
        const used = total - remaining;
        const percentage = total > 0 ? Math.round((used / total) * 100) : 0;

        // نمایش progress bar
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = percentage + '%';
            progressBar.setAttribute('aria-valuenow', percentage);
            
            // تغییر رنگ بر اساس درصد
            if (percentage >= 90) {
                progressBar.className = 'progress-bar bg-danger';
            } else if (percentage >= 70) {
                progressBar.className = 'progress-bar bg-warning';
            } else {
                progressBar.className = 'progress-bar bg-success';
            }
        }

        // هشدار اگر بودجه کافی نیست
        const factorAmountElement = document.getElementById('id_amount');
        if (factorAmountElement) {
            const factorAmount = parseFloat(factorAmountElement.value || 0);
            const warningDiv = document.getElementById('tankhah-budget-warning');
            
            if (factorAmount > remaining && warningDiv) {
                warningDiv.classList.remove('d-none');
            } else if (warningDiv) {
                warningDiv.classList.add('d-none');
            }
        }
    }

    /**
     * بررسی مبلغ فاکتور با بودجه باقی‌مانده
     */
    function validateFactorAmount(tankhahId, factorAmount) {
        if (!tankhahId || !factorAmount || factorAmount <= 0) {
            return;
        }

        checkTankhahBudgetViaAPI(tankhahId)
            .then(budgetData => {
                const remaining = parseFloat(budgetData.remaining_budget_str.replace(/,/g, '')) || 0;
                
                if (factorAmount > remaining) {
                    // نمایش هشدار
                    const warningDiv = document.getElementById('tankhah-budget-warning');
                    if (warningDiv) {
                        warningDiv.classList.remove('d-none');
                        warningDiv.innerHTML = `
                            <i class="fas fa-exclamation-circle me-1"></i>
                            هشدار: مبلغ فاکتور (${factorAmount.toLocaleString('fa-IR')} ریال) 
                            بیشتر از بودجه باقی‌مانده (${remaining.toLocaleString('fa-IR')} ریال) است!
                        `;
                    }

                    // نمایش در کنسول
                    console.warn('⚠️ مبلغ فاکتور بیشتر از بودجه باقی‌مانده است!', {
                        factorAmount,
                        remaining,
                        difference: factorAmount - remaining
                    });
                } else {
                    const warningDiv = document.getElementById('tankhah-budget-warning');
                    if (warningDiv) {
                        warningDiv.classList.add('d-none');
                    }
                }
            })
            .catch(error => {
                console.error('خطا در بررسی بودجه:', error);
            });
    }

    /**
     * راه‌اندازی event listeners
     */
    function initializeBudgetCheck() {
        // بررسی هنگام تغییر تنخواه
        const tankhahSelect = document.getElementById('id_tankhah');
        if (tankhahSelect) {
            tankhahSelect.addEventListener('change', function() {
                const tankhahId = this.value;
                
                // مخفی کردن اطلاعات قبلی
                const infoDisplay = document.getElementById('tankhah-budget-info-display');
                const loadingDiv = document.getElementById('tankhah-budget-loading');
                const errorDiv = document.getElementById('tankhah-budget-error');
                
                if (infoDisplay) infoDisplay.style.display = 'none';
                if (errorDiv) errorDiv.classList.add('d-none');
                
                if (tankhahId) {
                    if (loadingDiv) loadingDiv.classList.remove('d-none');
                    
                    checkTankhahBudgetViaAPI(tankhahId)
                        .then(budgetData => {
                            if (loadingDiv) loadingDiv.classList.add('d-none');
                            if (infoDisplay) infoDisplay.style.display = 'block';
                            
                            displayBudgetInfo(budgetData);
                        })
                        .catch(error => {
                            if (loadingDiv) loadingDiv.classList.add('d-none');
                            if (errorDiv) {
                                errorDiv.classList.remove('d-none');
                                errorDiv.textContent = 'خطا در دریافت بودجه: ' + error.message;
                            }
                            console.error('خطا در دریافت بودجه:', error);
                        });
                }
            });
        }

        // بررسی هنگام تغییر مبلغ فاکتور
        const amountInput = document.getElementById('id_amount');
        if (amountInput) {
            amountInput.addEventListener('input', function() {
                const tankhahSelect = document.getElementById('id_tankhah');
                if (tankhahSelect && tankhahSelect.value) {
                    const factorAmount = parseFloat(this.value || 0);
                    validateFactorAmount(tankhahSelect.value, factorAmount);
                }
            });
        }

        // بررسی اولیه اگر تنخواه از قبل انتخاب شده
        if (tankhahSelect && tankhahSelect.value) {
            tankhahSelect.dispatchEvent(new Event('change'));
        }
    }

    // راه‌اندازی پس از لود شدن صفحه
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeBudgetCheck);
    } else {
        initializeBudgetCheck();
    }

    // Export functions برای استفاده در دیگر فایل‌ها
    window.BudgetAPIHelper = {
        checkTankhahBudgetViaAPI,
        displayBudgetInfo,
        validateFactorAmount
    };

})();

