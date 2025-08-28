document.addEventListener("DOMContentLoaded", function () {
    const baseUrl = window.location.origin; // دامنه اصلی

    // تابع برای مخفی کردن مسیر URL در نوار آدرس
    function hideUrlPath() {
        if (window.location.pathname !== "/") {
            history.replaceState(null, document.title, baseUrl);
        }
    }

    // اجرا هنگام لود صفحه
    hideUrlPath();

    // مدیریت کلیک روی لینک‌ها
    document.addEventListener("click", function (event) {
        const link = event.target.closest("a");
        if (link && link.href.startsWith(baseUrl)) {
            event.preventDefault(); // جلوگیری از پیمایش مستقیم
            let originalHref = link.getAttribute("data-href") || link.href;

            fetch(originalHref) // دریافت محتوای صفحه جدید
                .then(response => response.text())
                .then(html => {
                    const doc = new DOMParser().parseFromString(html, "text/html");
                    document.body.innerHTML = doc.body.innerHTML; // جایگزینی محتوای صفحه
                    hideUrlPath(); // پنهان کردن مسیر
                })
                .catch(err => console.error("خطا در بارگذاری صفحه:", err));
        }
    });

    // مدیریت دکمه‌های بازگشت و جلو در مرورگر
    window.addEventListener("popstate", hideUrlPath);

    // مخفی کردن لینک‌ها در نوار وضعیت و هاور
    document.querySelectorAll("a").forEach(link => {
        link.setAttribute("data-href", link.href); // ذخیره لینک واقعی
        link.href = "javascript:void(0)"; // جلوگیری از نمایش لینک در هاور

        link.addEventListener("click", function () {
            this.href = this.getAttribute("data-href"); // بازگرداندن لینک هنگام کلیک
        });

        link.addEventListener("mouseover", function () {
            this.href = "javascript:void(0)"; // حذف نمایش لینک هنگام هاور
        });

        link.addEventListener("mouseout", function () {
            this.href = this.getAttribute("data-href"); // بازگرداندن مقدار اصلی لینک
        });
    });
});
