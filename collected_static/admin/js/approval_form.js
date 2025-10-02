document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('approvalForm');
    const buttons = form.querySelectorAll('button[type="submit"]');
    const statusSelect = document.querySelector('#{{ approval_form.status.id_for_label }}');

    if (!form || !statusSelect) {
        console.error('Form or status select element not found');
        return;
    }

    buttons.forEach(button => {
        button.addEventListener('click', (e) => {
            try {
                form.classList.add('loading');
                buttons.forEach(btn => btn.disabled = true);

                const action = button.getAttribute('data-action');
                if (action) {
                    const option = Array.from(statusSelect.options).find(opt => opt.value === action);
                    if (option) {
                        statusSelect.value = option.value;
                    } else {
                        console.warn(`No option found for status: ${action}`);
                    }
                }
            } catch (error) {
                console.error(`Error handling button click: ${error.message}`);
                form.classList.remove('loading');
                buttons.forEach(btn => btn.disabled = false);
            }
        });
    });

    // انیمیشن ورود
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.fade-in').forEach(card => {
        observer.observe(card);
    });

    // بازگرداندن دکمه‌ها در صورت خطا
    form.addEventListener('submit', (e) => {
        setTimeout(() => {
            if (form.classList.contains('loading')) {
                form.classList.remove('loading');
                buttons.forEach(btn => btn.disabled = false);
            }
        }, 5000);
    });
});