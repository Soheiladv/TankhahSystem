// numberFormatter.js
const NumberFormatter = (function () {
    function toPersianDigits(number) {
        const persianDigits = '۰۱۲۳۴۵۶۷۸۹';
        const englishDigits = '0123456789';
        let result = number + '';
        for (let i = 0; i < 10; i++) {
            result = result.replace(new RegExp(englishDigits[i], 'g'), persianDigits[i]);
        }
        return result;
    }

    function toEnglishDigits(number) {
        return number.replace(/[۰-۹]/g, function(d) {
            return '۰۱۲۳۴۵۶۷۸۹'.indexOf(d);
        });
    }

    function separate(number) {
        number = toEnglishDigits(number + '').replace(/[^0-9.]/g, ''); // نگه داشتن نقطه اعشار
        if (!number) return '';
        let parts = number.split('.');
        let y = parts[0];
        let z = parts.length > 1 ? '.' + parts[1] : '';
        let rgx = /(\d+)(\d{3})/;
        while (rgx.test(y)) {
            y = y.replace(rgx, '$1,$2');
        }
        return toPersianDigits(y + z).replace(/,/g, '،');
    }

    function getRawNumber(formattedNumber) {
        return toEnglishDigits(formattedNumber.replace(/،/g, ''));
    }

    function toPersianWords(number) {
        number = getRawNumber(number + '');
        if (!number || isNaN(number)) return '';

        const units = ['', 'یک', 'دو', 'سه', 'چهار', 'پنج', 'شش', 'هفت', 'هشت', 'نه'];
        const teens = ['ده', 'یازده', 'دوازده', 'سیزده', 'چهارده', 'پانزده', 'شانزده', 'هفده', 'هجده', 'نوزده'];
        const tens = ['', 'ده', 'بیست', 'سی', 'چهل', 'پنجاه', 'شصت', 'هفتاد', 'هشتاد', 'نود'];
        const hundreds = ['', 'صد', 'دویست', 'سیصد', 'چهارصد', 'پانصد', 'ششصد', 'هفتصد', 'هشتصد', 'نهصد'];
        const thousands = ['هزار', 'میلیون', 'میلیارد', 'تریلیون'];

        let num = parseInt(number);
        if (num === 0) return 'صفر';

        let parts = [];
        let thousandIndex = 0;

        while (num > 0) {
            let segment = num % 1000;
            if (segment > 0) {
                let segmentText = '';
                let hundred = Math.floor(segment / 100);
                let ten = Math.floor((segment % 100) / 10);
                let unit = segment % 10;

                if (hundred > 0) {
                    segmentText += hundreds[hundred];
                }

                if (segment % 100 > 0) {
                    if (segmentText) segmentText += ' و ';
                    if (segment % 100 < 20 && segment % 100 >= 10) {
                        segmentText += teens[(segment % 100) - 10];
                    } else {
                        if (ten > 0) {
                            segmentText += tens[ten];
                            if (unit > 0) segmentText += ' و ';
                        }
                        if (unit > 0) segmentText += units[unit];
                    }
                }

                if (thousandIndex > 0) {
                    segmentText += ' ' + thousands[thousandIndex - 1];
                }
                parts.unshift(segmentText);
            }
            num = Math.floor(num / 1000);
            thousandIndex++;
        }

        return parts.join(' و ');
    }

    return {
        separate: separate,
        getRawNumber: getRawNumber,
        toPersianWords: toPersianWords
    };
})();