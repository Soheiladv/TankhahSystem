// Tanbakhsystem/static/js/number_to_words_connect.js
function initializeNumberToWordsInputs() {
    document.querySelectorAll(".persian-number-input").forEach(input => {
        // فقط اگه هنوز بهش گوش‌کننده اضافه نشده باشه
        if (!input.dataset.listenerAdded) {
            const output = document.querySelector(input.getAttribute("data-output-target") + " span");
            if (output) {
                // فرمت اولیه اگه مقدار وجود داره
                if (input.value) {
                    input.value = NumberFormatter.separate(input.value);
                }

                input.addEventListener("input", function() {
                    let value = NumberFormatter.getRawNumber(this.value);
                    let words = NumberFormatter.toPersianWords(value);
                    output.textContent = words || "";
                    this.value = NumberFormatter.separate(value);
                });

                // علامت‌گذاری که گوش‌کننده اضافه شده
                input.dataset.listenerAdded = "true";
            }
        }
    });
}

// اجرا در بارگذاری اولیه
document.addEventListener("DOMContentLoaded", initializeNumberToWordsInputs);

// تابع برای فراخوانی بعد از اضافه کردن ردیف جدید
window.initializeNumberToWordsInputs = initializeNumberToWordsInputs;