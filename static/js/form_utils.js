// Generic form utilities shared across templates
window.FormUtils = (function(){
  function toLatinDigits(str){
    return String(str ?? '')
      .replace(/[۰-۹]/g, d => '0123456789'[d.charCodeAt(0)-1776])
      .replace(/[٠-٩]/g, d => '0123456789'[d.charCodeAt(0)-1632]);
  }
  function toPersianDigits(str){
    return String(str ?? '').replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
  }
  function formatFaNumber(n){
    const num = Number(toLatinDigits(String(n)).replace(/,/g,'')) || 0;
    return toPersianDigits(num.toLocaleString('en-US'));
  }
  function debounce(fn, wait){
    let t; return function(...args){ clearTimeout(t); t=setTimeout(()=>fn.apply(this,args), wait); };
  }
  function numberToWordsFa(num){
    num = Math.floor(Number(num) || 0);
    if (num === 0) return 'صفر';
    const ones = ['','یک','دو','سه','چهار','پنج','شش','هفت','هشت','نه'];
    const teens = ['ده','یازده','دوازده','سیزده','چهارده','پانزده','شانزده','هفده','هجده','نوزده'];
    const tens = ['','','بیست','سی','چهل','پنجاه','شصت','هفتاد','هشتاد','نود'];
    const hundreds = ['','صد','دویست','سیصد','چهارصد','پانصد','ششصد','هفتصد','هشتصد','نهصد'];
    const scales = ['','هزار','میلیون','میلیارد','هزار میلیارد'];
    function underThousand(n){
      let parts=[];
      const h=Math.floor(n/100), lastTwo=n%100, t=Math.floor(lastTwo/10), o=lastTwo%10;
      if (h) parts.push(hundreds[h]);
      if (lastTwo>=10 && lastTwo<20) parts.push(teens[lastTwo-10]);
      else { if (t) parts.push(tens[t]); if (o) parts.push(ones[o]); }
      return parts.join(' و ');
    }
    let parts=[], scale=0;
    while(num>0 && scale<scales.length){
      const chunk = num%1000;
      if (chunk){
        const w = underThousand(chunk);
        parts.unshift((w + (scales[scale] ? ' ' + scales[scale] : '')).trim());
      }
      num = Math.floor(num/1000); scale++;
    }
    return parts.join(' و ');
  }
  function getEl(){ for(let i=0;i<arguments.length;i++){ const el=document.getElementById(arguments[i]); if(el) return el; } return null; }
  return { toLatinDigits, toPersianDigits, formatFaNumber, debounce, numberToWordsFa, getEl };
})();


