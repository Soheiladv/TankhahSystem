/**
 * Chart Utilities for Budget System
 * Provides common functions for chart initialization and error handling
 */

// Chart configuration defaults
const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: {
                font: {
                    family: 'Parastoo, sans-serif'
                },
                padding: 20,
                usePointStyle: true
            }
        },
        tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            cornerRadius: 6,
            displayColors: true,
            font: {
                family: 'Parastoo, sans-serif'
            }
        }
    },
    animation: {
        duration: 2000,
        easing: 'easeInOutQuart'
    }
};

// Color palettes for different chart types
const COLOR_PALETTES = {
    primary: ['#2563eb', '#16a34a', '#f59e0b', '#dc2626', '#7c3aed', '#0891b2', '#65a30d', '#ea580c', '#db2777', '#4f46e5'],
    pastel: ['#A5B4FC', '#93C5FD', '#86EFAC', '#FDE68A', '#FCA5A5', '#FBCFE8', '#BFDBFE', '#99F6E4', '#FECACA', '#DDD6FE'],
    neutral: ['#334155', '#475569', '#64748b', '#94a3b8', '#cbd5e1', '#e2e8f0'],
    semantic: ['#16a34a', '#dc2626', '#f59e0b', '#0891b2', '#7c3aed', '#2563eb']
};

/**
 * Check if Chart.js is loaded
 */
function isChartJsLoaded() {
    return typeof Chart !== 'undefined';
}

/**
 * Show loading state for chart container
 */
function showChartLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = '<div class="chart-loading">در حال بارگذاری نمودار...</div>';
    }
}

/**
 * Show error state for chart container
 */
function showChartError(containerId, message = 'خطا در بارگذاری نمودار') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `<div class="chart-error">${message}</div>`;
    }
}

/**
 * Show empty state for chart container
 */
function showChartEmpty(containerId, message = 'داده‌ای برای نمایش وجود ندارد') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `<div class="chart-empty">${message}</div>`;
    }
}

/**
 * Create a doughnut chart with error handling
 */
function createDoughnutChart(canvasId, data, options = {}) {
    if (!isChartJsLoaded()) {
        showChartError(canvasId, 'کتابخانه Chart.js بارگذاری نشده است');
        return null;
    }

    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas element with id '${canvasId}' not found`);
        return null;
    }

    if (!data || !data.labels || !data.datasets) {
        showChartEmpty(canvasId);
        return null;
    }

    const config = {
        type: 'doughnut',
        data: data,
        options: {
            ...CHART_DEFAULTS,
            ...options,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                ...options.plugins
            }
        }
    };

    try {
        return new Chart(canvas, config);
    } catch (error) {
        console.error(`Error creating doughnut chart for ${canvasId}:`, error);
        showChartError(canvasId, 'خطا در ایجاد نمودار');
        return null;
    }
}

/**
 * Create a line chart with error handling
 */
function createLineChart(canvasId, data, options = {}) {
    if (!isChartJsLoaded()) {
        showChartError(canvasId, 'کتابخانه Chart.js بارگذاری نشده است');
        return null;
    }

    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas element with id '${canvasId}' not found`);
        return null;
    }

    if (!data || !data.labels || !data.datasets) {
        showChartEmpty(canvasId);
        return null;
    }

    const config = {
        type: 'line',
        data: data,
        options: {
            ...CHART_DEFAULTS,
            ...options,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                ...options.plugins
            }
        }
    };

    try {
        return new Chart(canvas, config);
    } catch (error) {
        console.error(`Error creating line chart for ${canvasId}:`, error);
        showChartError(canvasId, 'خطا در ایجاد نمودار');
        return null;
    }
}

/**
 * Create a bar chart with error handling
 */
function createBarChart(canvasId, data, options = {}) {
    if (!isChartJsLoaded()) {
        showChartError(canvasId, 'کتابخانه Chart.js بارگذاری نشده است');
        return null;
    }

    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas element with id '${canvasId}' not found`);
        return null;
    }

    if (!data || !data.labels || !data.datasets) {
        showChartEmpty(canvasId);
        return null;
    }

    const config = {
        type: 'bar',
        data: data,
        options: {
            ...CHART_DEFAULTS,
            ...options,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                ...options.plugins
            }
        }
    };

    try {
        return new Chart(canvas, config);
    } catch (error) {
        console.error(`Error creating bar chart for ${canvasId}:`, error);
        showChartError(canvasId, 'خطا در ایجاد نمودار');
        return null;
    }
}

/**
 * Create a pie chart with error handling
 */
function createPieChart(canvasId, data, options = {}) {
    if (!isChartJsLoaded()) {
        showChartError(canvasId, 'کتابخانه Chart.js بارگذاری نشده است');
        return null;
    }

    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas element with id '${canvasId}' not found`);
        return null;
    }

    if (!data || !data.labels || !data.datasets) {
        showChartEmpty(canvasId);
        return null;
    }

    const config = {
        type: 'pie',
        data: data,
        options: {
            ...CHART_DEFAULTS,
            ...options,
            plugins: {
                ...CHART_DEFAULTS.plugins,
                ...options.plugins
            }
        }
    };

    try {
        return new Chart(canvas, config);
    } catch (error) {
        console.error(`Error creating pie chart for ${canvasId}:`, error);
        showChartError(canvasId, 'خطا در ایجاد نمودار');
        return null;
    }
}

/**
 * Format number for display in charts
 */
function formatNumber(value, locale = 'fa-IR') {
    if (typeof value !== 'number') {
        value = parseFloat(value) || 0;
    }
    return value.toLocaleString(locale);
}

/**
 * Format currency for display in charts
 */
function formatCurrency(value, currency = 'ریال', locale = 'fa-IR') {
    return formatNumber(value, locale) + ' ' + currency;
}

/**
 * Get color from palette
 */
function getColorFromPalette(index, palette = 'primary') {
    const colors = COLOR_PALETTES[palette] || COLOR_PALETTES.primary;
    return colors[index % colors.length];
}

/**
 * Create gradient background for datasets
 */
function createGradient(ctx, color1, color2, direction = 'vertical') {
    const gradient = ctx.createLinearGradient(
        direction === 'vertical' ? 0 : 0,
        direction === 'vertical' ? 0 : 0,
        direction === 'vertical' ? 0 : ctx.canvas.width,
        direction === 'vertical' ? ctx.canvas.height : 0
    );
    gradient.addColorStop(0, color1);
    gradient.addColorStop(1, color2);
    return gradient;
}

/**
 * Destroy chart if it exists
 */
function destroyChart(chart) {
    if (chart && typeof chart.destroy === 'function') {
        chart.destroy();
    }
}

/**
 * Resize chart if it exists
 */
function resizeChart(chart) {
    if (chart && typeof chart.resize === 'function') {
        chart.resize();
    }
}

// Export functions for global use
window.ChartUtils = {
    isChartJsLoaded,
    showChartLoading,
    showChartError,
    showChartEmpty,
    createDoughnutChart,
    createLineChart,
    createBarChart,
    createPieChart,
    // removed adaptive chart and 3d controls
    formatNumber,
    formatCurrency,
    getColorFromPalette,
    createGradient,
    destroyChart,
    resizeChart,
    CHART_DEFAULTS,
    COLOR_PALETTES
};

/**
 * Determine current chart mode from global selector
 */
// removed adaptive chart implementation

/**
 * Lightweight 3D-like shadow effect for Chart.js datasets
 * Usage: pass enable3D=true to options.plugins.fake3d.enable
 */
function apply3DEffect(chart, intensity = 6, alpha = 0.12) {
    if (!chart || !chart.ctx) return;
    const ctx = chart.ctx;
    const originalStroke = ctx.stroke;
    const originalFill = ctx.fill;
    ctx.stroke = function() {
        ctx.save();
        ctx.shadowColor = 'rgba(0,0,0,' + alpha + ')';
        ctx.shadowBlur = intensity;
        ctx.shadowOffsetX = Math.max(1, Math.floor(intensity/2));
        ctx.shadowOffsetY = Math.max(2, Math.floor(intensity/1.5));
        originalStroke.apply(this, arguments);
        ctx.restore();
    };
    ctx.fill = function() {
        ctx.save();
        ctx.shadowColor = 'rgba(0,0,0,' + alpha + ')';
        ctx.shadowBlur = intensity;
        ctx.shadowOffsetX = Math.max(1, Math.floor(intensity/2));
        ctx.shadowOffsetY = Math.max(2, Math.floor(intensity/1.5));
        originalFill.apply(this, arguments);
        ctx.restore();
    };
}

/**
 * Create adaptive chart by type string with optional 3D-like effect
 */
function createAdaptiveChart(canvasId, type, data, options = {}, enable3D = false) {
    if (!isChartJsLoaded()) { showChartError(canvasId, 'Chart.js بارگذاری نشده'); return null; }
    const canvas = document.getElementById(canvasId);
    if (!canvas) { console.error('Canvas not found', canvasId); return null; }
    if (!data || !data.labels || !data.datasets) { showChartEmpty(canvasId); return null; }
    const config = { type, data, options: { ...CHART_DEFAULTS, ...options, plugins: { ...CHART_DEFAULTS.plugins, ...(options.plugins||{}) } } };
    try {
        const chart = new Chart(canvas, config);
        if (enable3D) {
            apply3DEffect(chart);
            chart.update();
        }
        return chart;
    } catch (e) {
        console.error('Adaptive chart error', e);
        showChartError(canvasId, 'خطا در ساخت نمودار');
        return null;
    }
}

// expose helpers
window.ChartUtils.createAdaptiveChart = createAdaptiveChart;
window.ChartUtils.apply3DEffect = apply3DEffect;
// Backward-safe: if some callers still reference ChartUtils.createAdaptiveChart
if (!window.ChartUtils.createAdaptiveChart) {
    window.ChartUtils.createAdaptiveChart = function(canvasId, type, data, options, enable3D){
        const canvas = document.getElementById(canvasId);
        if (!canvas || typeof Chart === 'undefined') return null;
        const cfg = { type, data, options: { ...CHART_DEFAULTS, ...(options||{}) } };
        const chart = new Chart(canvas, cfg);
        if (enable3D) try { apply3DEffect(chart); chart.update(); } catch(e){}
        return chart;
    };
}

/**
 * Export helpers: PNG and CSV from an existing chart canvas
 */
function exportChartAsPNG(canvasId, filename = 'chart.png') {
    try {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const link = document.createElement('a');
        link.href = canvas.toDataURL('image/png');
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } catch (e) { console.warn('PNG export error', e); }
}

function exportChartAsCSV(canvasId, filename = 'chart.csv') {
    try {
        const canvas = document.getElementById(canvasId);
        if (!canvas || typeof Chart === 'undefined') return;
        const chart = Chart.getChart(canvas);
        if (!chart || !chart.data) return;
        const labels = chart.data.labels || [];
        const datasets = chart.data.datasets || [];
        let csv = [];
        const header = ['Label'].concat(datasets.map(ds => '"' + (ds.label || '') + '"'));
        csv.push(header.join(','));
        for (let i = 0; i < labels.length; i++) {
            const row = [ '"' + (labels[i] ?? '') + '"' ];
            for (let d = 0; d < datasets.length; d++) {
                const val = Array.isArray(datasets[d].data) ? (datasets[d].data[i] ?? '') : '';
                row.push(val);
            }
            csv.push(row.join(','));
        }
        const blob = new Blob([csv.join('\n')], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    } catch (e) { console.warn('CSV export error', e); }
}

window.ChartUtils.exportChartAsPNG = exportChartAsPNG;
window.ChartUtils.exportChartAsCSV = exportChartAsCSV;

/**
 * Fullscreen helpers for chart canvases
 */
function toggleFullscreenForCanvas(canvasId) {
    try {
        const el = document.getElementById(canvasId);
        if (!el) return;
        const container = el.closest('.chart-container') || el;
        if (!document.fullscreenElement) {
            (container.requestFullscreen || container.webkitRequestFullscreen || container.msRequestFullscreen || container.mozRequestFullScreen).call(container);
        } else {
            (document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen || document.mozCancelFullScreen).call(document);
        }
    } catch (e) { console.warn('fullscreen toggle error', e); }
}

function apply3DEffectToChartId(canvasId) {
    try {
        const canvas = document.getElementById(canvasId);
        if (!canvas || typeof Chart === 'undefined') return;
        const chart = Chart.getChart(canvas);
        if (!chart) return;
        apply3DEffect(chart);
        chart.update();
    } catch (e) { console.warn('3D effect apply error', e); }
}

window.ChartUtils.toggleFullscreenForCanvas = toggleFullscreenForCanvas;
window.ChartUtils.apply3DEffectToChartId = apply3DEffectToChartId;

/**
 * Fallback renderers using native Chart.js (no external controllers)
 */
function renderSemiGaugeFallback(canvasId, percent) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    const value = Math.max(0, Math.min(100, Number(percent||0)));
    const data = {
        labels: ['Value', 'Rest'],
        datasets: [{
            data: [value, 100 - value],
            backgroundColor: ['#22c55e', '#e5e7eb'],
            borderWidth: 0
        }]
    };
    const options = {
        ...CHART_DEFAULTS,
        rotation: -Math.PI,
        circumference: Math.PI,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: () => Math.round(value)+'%' } } }
    };
    return new Chart(canvas, { type: 'doughnut', data, options });
}

function renderBulletFallback(canvasId, units) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !Array.isArray(units) || !units.length) return null;
    const labels = units.map(u => u.name||u.unit||'');
    const values = units.map(u => Number(u.actual||u.value||0));
    const targets = units.map(u => Number(u.target||0));
    const chart = new Chart(canvas, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'عملکرد', data: values, backgroundColor: '#3b82f6' }] },
        options: { indexAxis: 'y', plugins: { legend: { display: false }, annotation: { annotations: targets.map((t, i) => ({ type: 'line', xMin: t, xMax: t, yMin: i - 0.45, yMax: i + 0.45, borderColor: '#ef4444', borderWidth: 2 })) } } }
    });
    return chart;
}

function renderFunnelFallback(canvasId, stages) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !Array.isArray(stages) || !stages.length) return null;
    const labels = stages.map(s => s.label);
    const data = stages.map(s => Number(s.value||0));
    return new Chart(canvas, {
        type: 'bar',
        data: { labels, datasets: [{ data, backgroundColor: data.map((_,i)=> getColorFromPalette(i)) }] },
        options: { indexAxis:'y', plugins:{ legend:{ display:false } }, scales:{ x:{ beginAtZero:true } } }
    });
}

function renderWaterfallFallback(canvasId, series) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !Array.isArray(series) || !series.length) return null;
    // series: [{label, value}]; compute cumulative
    let cum = 0;
    const labels = series.map(s => s.label);
    const positives = [];
    const negatives = [];
    series.forEach(s => {
        const v = Number(s.value||0);
        positives.push(Math.max(0, v));
        negatives.push(Math.min(0, v));
        cum += v;
    });
    return new Chart(canvas, {
        type: 'bar',
        data: { labels, datasets: [
            { label: 'افزایشی', data: positives, backgroundColor: '#22c55e' },
            { label: 'کاهشی', data: negatives, backgroundColor: '#ef4444' }
        ] },
        options: { plugins:{ legend:{ position:'bottom' } }, scales:{ y:{ beginAtZero:true } } }
    });
}

window.ChartUtils.renderSemiGaugeFallback = renderSemiGaugeFallback;
window.ChartUtils.renderBulletFallback = renderBulletFallback;
window.ChartUtils.renderFunnelFallback = renderFunnelFallback;
window.ChartUtils.renderWaterfallFallback = renderWaterfallFallback;
