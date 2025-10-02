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
                    family: 'Vazirmatn, sans-serif'
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
                family: 'Vazirmatn, sans-serif'
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
    primary: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6366f1'],
    pastel: ['#a8d8ea', '#aa96da', '#fcbad3', '#ffffd2', '#d4a5a5', '#9fd3c7', '#fce38a', '#f38181', '#95e1d3', '#fce38a'],
    gradient: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe', '#43e97b', '#38f9d7', '#ffecd2', '#fcb69f']
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
    formatNumber,
    formatCurrency,
    getColorFromPalette,
    createGradient,
    destroyChart,
    resizeChart,
    CHART_DEFAULTS,
    COLOR_PALETTES
};
