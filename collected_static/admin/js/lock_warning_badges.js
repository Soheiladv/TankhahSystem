// Global utility to keep lock/warning badges in sync with form inputs
(function () {
    'use strict';

    function toLatinDigits(str) {
        return String(str ?? '').replace(/[۰-۹]/g, function (d) { return '0123456789'[d.charCodeAt(0) - 1776]; })
            .replace(/[٠-٩]/g, function (d) { return '0123456789'[d.charCodeAt(0) - 1632]; });
    }

    function updateBadges(opts) {
        var lockCondSel = opts && opts.lockConditionEl || document.getElementById('id_lock_condition');
        var lockBadge = opts && opts.lockBadgeEl || document.getElementById('badge-lock-condition');
        var lockPercInput = opts && opts.lockedPercentageEl || document.getElementById('id_locked_percentage');
        var lockPercBadge = opts && opts.lockedPercentageBadgeEl || document.getElementById('badge-locked-percentage');
        var warnThrInput = opts && opts.warningThresholdEl || document.getElementById('id_warning_threshold');
        var warnThrBadge = opts && opts.warningThresholdBadgeEl || document.getElementById('badge-warning-threshold');
        var warnActionSel = opts && opts.warningActionEl || document.getElementById('id_warning_action');
        var warnActionBadge = opts && opts.warningActionBadgeEl || document.getElementById('badge-warning-action');

        if (lockCondSel && lockBadge) {
            var v = lockCondSel.value || '';
            var t = (lockCondSel.options && lockCondSel.selectedIndex >= 0) ? (lockCondSel.options[lockCondSel.selectedIndex].text || '') : '';
            lockBadge.textContent = t || '—';
            var cls;
            if (v === 'AFTER_DATE') cls = 'bg-warning';
            else if (v === 'MANUAL') cls = 'bg-danger';
            else if (v === 'ZERO_REMAINING') cls = 'bg-info';
            else cls = 'bg-secondary';
            lockBadge.className = 'badge ' + cls;
        }

        if (lockPercInput && lockPercBadge) {
            var p = Number(toLatinDigits(lockPercInput.value)) || 0;
            lockPercBadge.textContent = p + '%';
            lockPercBadge.className = 'badge ' + (p >= 50 ? 'bg-danger' : p >= 20 ? 'bg-warning' : 'bg-success');
        }

        if (warnThrInput && warnThrBadge) {
            var w = Number(toLatinDigits(warnThrInput.value)) || 0;
            warnThrBadge.textContent = w + '%';
            warnThrBadge.className = 'badge ' + (w >= 50 ? 'bg-danger' : w >= 20 ? 'bg-warning' : 'bg-success');
        }

        if (warnActionSel && warnActionBadge) {
            var vt = (warnActionSel.options && warnActionSel.selectedIndex >= 0) ? (warnActionSel.options[warnActionSel.selectedIndex].text || '') : '';
            var vv = warnActionSel.value || '';
            warnActionBadge.textContent = vt || '—';
            warnActionBadge.className = 'badge ' + (vv === 'LOCK' ? 'bg-danger' : vv === 'RESTRICT' ? 'bg-warning' : 'bg-secondary');
        }
    }

    function attachBadgeListeners() {
        var lockCondSel = document.getElementById('id_lock_condition');
        var lockPercInput = document.getElementById('id_locked_percentage');
        var warnThrInput = document.getElementById('id_warning_threshold');
        var warnActionSel = document.getElementById('id_warning_action');

        lockCondSel && lockCondSel.addEventListener('change', function () { updateBadges(); });
        lockPercInput && lockPercInput.addEventListener('input', function () { updateBadges(); });
        warnThrInput && warnThrInput.addEventListener('input', function () { updateBadges(); });
        warnActionSel && warnActionSel.addEventListener('change', function () { updateBadges(); });
    }

    document.addEventListener('DOMContentLoaded', function () {
        // Auto-init if any badge exists on the page
        if (
            document.getElementById('badge-lock-condition') ||
            document.getElementById('badge-locked-percentage') ||
            document.getElementById('badge-warning-threshold') ||
            document.getElementById('badge-warning-action')
        ) {
            attachBadgeListeners();
            setTimeout(updateBadges, 200);
        }
    });

    // Expose for manual calls if needed
    window.updateLockWarningBadges = updateBadges;
})();


