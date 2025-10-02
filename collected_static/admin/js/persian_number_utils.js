// static/js/persian_number_utils.js

// --- Helper Functions ---
function toPersianDigits(numStr) {
    if (numStr === null || numStr === undefined) return '';
    const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    return String(numStr).replace(/[0-9]/g, digit => persianDigits[parseInt(digit)]);
}

function toLatinDigits(persianNumStr) {
     if (persianNumStr === null || persianNumStr === undefined) return '';
    const persianDigitsMap = { '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9' };
    return String(persianNumStr).replace(/[۰-۹]/g, digit => persianDigitsMap[digit]);
}

// --- Number to Persian Words Function (from previous example) ---
function numberToPersianWords(numStr) {
    numStr = String(numStr || '').trim(); // Handle null/undefined and trim
    numStr = toLatinDigits(numStr); // Convert potential Persian input digits
    numStr = numStr.replace(/[^0-9]/g, ''); // Remove non-numeric chars (like commas)

    if (numStr === '') return '';
    if (numStr === '0') return 'صفر';
    if (numStr.length > 15) return 'عدد بسیار بزرگ است!';

    const yekan = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه"];
    const dahgan = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"];
    const sadgan = ["", "صد", "دویست", "سیصد", "چهارصد", "پانصد", "ششصد", "هفتصد", "هشتصد", "نهصد"];
    const dahyek = ["ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده"];
    const separators = ["", "هزار", "میلیون", "میلیارد", "تریلیون"];

    function threeDigitsToWords(threeDigitNum) {
        let result = '';
        const num = parseInt(threeDigitNum, 10);
        if (num === 0) return '';
        const sad = Math.floor(num / 100);
        const dahyekRemainder = num % 100;
        const dah = Math.floor(dahyekRemainder / 10);
        const yek = dahyekRemainder % 10;

        if (sad > 0) {
            result += sadgan[sad];
            if (dahyekRemainder > 0) result += ' و ';
        }
        if (dahyekRemainder > 0) {
            if (dahyekRemainder < 10) result += yekan[yek];
            else if (dahyekRemainder < 20) result += dahyek[dahyekRemainder - 10];
            else {
                result += dahgan[dah];
                if (yek > 0) result += ' و ' + yekan[yek];
            }
        }
        return result;
    }

    let resultWords = [];
    const len = numStr.length;
    const firstChunkLen = len % 3 === 0 ? 3 : len % 3;
    let chunks = [];
    if (len > 0) { // Handle empty string case after cleaning
        chunks.push(numStr.substring(0, firstChunkLen));
        for (let i = firstChunkLen; i < len; i += 3) {
            chunks.push(numStr.substring(i, i + 3));
        }
    }

    const numChunks = chunks.length;
    for (let i = 0; i < numChunks; i++) {
        const chunkWords = threeDigitsToWords(chunks[i]);
        if (chunkWords !== '') {
            const separatorIndex = numChunks - 1 - i;
            resultWords.push(chunkWords + (separatorIndex > 0 && parseInt(chunks[i], 10) > 0 ? ' ' + separators[separatorIndex] : ''));
        }
    }
    return resultWords.join(' و ');
}


// --- Input Formatting Function (Thousand Separator + Persian Digits) ---
function formatPersianNumberInput(inputElement) {
    if (!inputElement) return;

    // 1. Save cursor position
    let cursorStart = inputElement.selectionStart;
    let cursorEnd = inputElement.selectionEnd;
    const originalLength = inputElement.value.length;

    // 2. Get Latin numeric value
    let value = toLatinDigits(inputElement.value);
    value = value.replace(/[^0-9]/g, ''); // Keep only digits

    // Store unformatted value for word conversion later if needed
    const unformattedValue = value;

    // 3. Format with thousand separators
    const formattedValue = value.replace(/\B(?=(\d{3})+(?!\d))/g, ",");

    // 4. Convert back to Persian digits
    const persianFormattedValue = toPersianDigits(formattedValue);

    // 5. Update input value
    inputElement.value = persianFormattedValue;

    // 6. Restore cursor position (adjusting for added/removed commas)
    // This part is tricky and might need refinement based on behavior
    const newLength = inputElement.value.length;
    const lengthDiff = newLength - originalLength;

    // Basic adjustment (might not be perfect in all edge cases like deleting commas)
    // A more robust solution would track comma positions before/after
    let newCursorPos = cursorStart + lengthDiff;
    // Ensure cursor position is not negative or beyond the new length
    newCursorPos = Math.max(0, Math.min(newLength, newCursorPos));

     // Use requestAnimationFrame to prevent issues with rapid input events
     requestAnimationFrame(() => {
        try {
             // Check if the element is still focused before setting selection
            if (document.activeElement === inputElement) {
                inputElement.setSelectionRange(newCursorPos, newCursorPos);
            }
        } catch (e) {
            console.warn("Could not set cursor position:", e);
        }
    });


    return unformattedValue; // Return the clean Latin digit string
}

// --- Global Initializer ---
document.addEventListener('DOMContentLoaded', function() {
    // Find all inputs that should use this functionality
    const numberInputs = document.querySelectorAll('input.persian-number-input');

    numberInputs.forEach(inputEl => {
        const outputTargetSelector = inputEl.dataset.outputTarget; // Get selector from data attribute
        let outputEl = null;

        if (outputTargetSelector) {
            try {
                 outputEl = document.querySelector(outputTargetSelector);
                 if (!outputEl) {
                     console.warn(`Output target element not found for selector: ${outputTargetSelector}`);
                 }
            } catch(e) {
                 console.error(`Invalid selector for output target: ${outputTargetSelector}`, e);
            }
        } else {
             console.warn('Input element is missing data-output-target attribute:', inputEl);
        }


        // Add the input event listener
        inputEl.addEventListener('input', function() {
            // Format the input field itself and get the unformatted value
            const unformattedValue = formatPersianNumberInput(inputEl);

            // Update the output element with Persian words if it exists
            if (outputEl) {
                const persianWords = numberToPersianWords(unformattedValue);
                outputEl.textContent = persianWords;
            }
        });

         // --- Initial formatting on page load ---
         // Format the initial value (if any) when the page loads
         const initialUnformattedValue = formatPersianNumberInput(inputEl);
         if (outputEl) {
             const initialPersianWords = numberToPersianWords(initialUnformattedValue);
             outputEl.textContent = initialPersianWords;
         }
    });
});