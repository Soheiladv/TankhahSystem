// Persian Datepicker Initialization Script
$(document).ready(function() {
    // Function to initialize Persian datepickers
    function initializePersianDatepickers() {
        $('[data-jdp]').each(function() {
            if (!$(this).hasClass('pdatepicker-applied')) {
                $(this).pDatepicker({
                    format: 'YYYY/MM/DD',
                    autoClose: true,
                    initialValue: false,
                    persianDigit: true,
                    calendar: {
                        persian: {
                            locale: 'fa',
                            showHint: true,
                            leapYearMode: 'algorithmic'
                        }
                    }
                });
                $(this).addClass('pdatepicker-applied');
            }
        });
    }
    
    // Initialize immediately
    initializePersianDatepickers();
    
    // Re-initialize after any dynamic content is added
    $(document).on('DOMNodeInserted', function() {
        setTimeout(initializePersianDatepickers, 100);
    });
    
    // Also initialize on window load
    $(window).on('load', function() {
        setTimeout(initializePersianDatepickers, 200);
    });
});
