// Dashboard Custom JavaScript
/*
// کامنت شده برای تست - استفاده از JavaScript اصلی
/*

// Global variables
var charts = {};
var animationTimeout = null;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    startAnimations();
});

// Initialize dashboard components
function initializeDashboard() {
    console.log('Initializing Dashboard...');
    
    // Initialize AOS animations
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            easing: 'ease-in-out',
            once: true,
            offset: 100
        });
    }
    
    // Initialize charts
    initializeCharts();
    
    // Load filter options
    loadFilterOptions();
    
    // Animate counters
    animateCounters();
    
    // Setup real-time updates
    setupRealTimeUpdates();
    
    console.log('Dashboard initialized successfully');
}

// Setup event listeners
function setupEventListeners() {
    // Filter form submission
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', handleFilterSubmit);
    }
    
    // Export buttons
    const exportButtons = document.querySelectorAll('[data-export]');
    exportButtons.forEach(button => {
        button.addEventListener('click', handleExport);
    });
    
    // Refresh button
    const refreshButton = document.querySelector('[data-refresh]');
    if (refreshButton) {
        refreshButton.addEventListener('click', refreshDashboard);
    }
    
    // Chart hover effects
    setupChartHoverEffects();
}

// Initialize all charts
function initializeCharts() {
    console.log('Initializing charts...');
    
    // Budget Distribution Chart
    initBudgetDistributionChart();
    
    // Monthly Consumption Chart
    initMonthlyConsumptionChart();
    
    // Tankhah Status Chart
    initTankhahStatusChart();
    
    // Factor Category Chart
    initFactorCategoryChart();
    
    // Progress Ring
    initProgressRing();
    
    console.log('Charts initialized successfully');
}

// Initialize Budget Distribution Chart
function initBudgetDistributionChart() {
    const ctx = document.getElementById('budgetDistributionChart');
    if (!ctx) return;
    
    const chartData = window.chartData || {};
    const orgBudget = chartData.org_budget || [];
    
    charts.budgetDistribution = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: orgBudget.map(item => item.organization__name || 'نامشخص'),
            datasets: [{
                data: orgBudget.map(item => item.total || 0),
                backgroundColor: generateColors(orgBudget.length),
                borderWidth: 2,
                borderColor: '#fff',
                hoverBorderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value.toLocaleString()} ریال (${percentage}%)`;
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                duration: 2000,
                easing: 'easeInOutQuart'
            },
            interaction: {
                intersect: false
            }
        }
    });
}

// Initialize Monthly Consumption Chart
function initMonthlyConsumptionChart() {
    const ctx = document.getElementById('monthlyConsumptionChart');
    if (!ctx) return;
    
    const chartData = window.chartData || {};
    const monthlyData = chartData.monthly_consumption || [];
    
    charts.monthlyConsumption = new Chart(ctx, {
        type: 'line',
        data: {
            labels: monthlyData.map(item => {
                const date = new Date(item.month);
                return date.toLocaleDateString('fa-IR');
            }),
            datasets: [{
                label: 'مصرف بودجه',
                data: monthlyData.map(item => item.total || 0),
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#28a745',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `مصرف: ${context.parsed.y.toLocaleString()} ریال`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString() + ' ریال';
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                }
            },
            animation: {
                duration: 2000,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// Initialize Tankhah Status Chart
function initTankhahStatusChart() {
    const ctx = document.getElementById('tankhahStatusChart');
    if (!ctx) return;
    
    const chartData = window.chartData || {};
    const statusData = chartData.tankhah_status || [];
    
    charts.tankhahStatus = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: statusData.map(item => item.status__name || 'نامشخص'),
            datasets: [{
                label: 'تعداد تنخواه‌ها',
                data: statusData.map(item => item.count || 0),
                backgroundColor: '#007bff',
                borderColor: '#0056b3',
                borderWidth: 1,
                borderRadius: 5,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `تعداد: ${context.parsed.y}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 2000,
                easing: 'easeInOutBounce'
            }
        }
    });
}

// Initialize Factor Category Chart
function initFactorCategoryChart() {
    const ctx = document.getElementById('factorCategoryChart');
    if (!ctx) return;
    
    const chartData = window.chartData || {};
    const categoryData = chartData.factor_category || [];
    
    charts.factorCategory = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: categoryData.map(item => item.category__name || 'نامشخص'),
            datasets: [{
                data: categoryData.map(item => item.total || 0),
                backgroundColor: generateColors(categoryData.length),
                borderWidth: 2,
                borderColor: '#fff',
                hoverBorderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value.toLocaleString()} ریال (${percentage}%)`;
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                duration: 2000
            }
        }
    });
}

// Initialize Progress Ring
function initProgressRing() {
    const circle = document.querySelector('.progress-ring-circle');
    if (!circle) return;
    
    const percentage = parseFloat(circle.getAttribute('data-percentage')) || 0;
    const circumference = 2 * Math.PI * 40;
    const offset = circumference - (percentage / 100) * circumference;
    
    circle.style.strokeDashoffset = offset;
    
    // Animate progress ring
    setTimeout(() => {
        circle.style.transition = 'stroke-dashoffset 2s ease-in-out';
        circle.style.strokeDashoffset = offset;
    }, 1000);
}

// Generate colors for charts
function generateColors(count) {
    const colors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
        '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384',
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
        '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
    ];
    
    return colors.slice(0, count);
}

// Load filter options via AJAX
function loadFilterOptions() {
    console.log('Loading filter options...');
    
    // Load organizations
    fetch('/api/organizations/')
        .then(response => response.json())
        .then(data => {
            const orgSelect = document.getElementById('organization');
            if (orgSelect) {
                data.forEach(org => {
                    const option = document.createElement('option');
                    option.value = org.id;
                    option.textContent = org.name;
                    orgSelect.appendChild(option);
                });
            }
        })
        .catch(error => console.error('Error loading organizations:', error));
    
    // Load projects
    fetch('/api/projects/')
        .then(response => response.json())
        .then(data => {
            const projectSelect = document.getElementById('project');
            if (projectSelect) {
                data.forEach(project => {
                    const option = document.createElement('option');
                    option.value = project.id;
                    option.textContent = project.name;
                    projectSelect.appendChild(option);
                });
            }
        })
        .catch(error => console.error('Error loading projects:', error));
}

// Animate counters
function animateCounters() {
    const counters = document.querySelectorAll('.stat-number');
    
    counters.forEach(counter => {
        const target = parseInt(counter.textContent.replace(/,/g, ''));
        const duration = 2000;
        const increment = target / (duration / 16);
        let current = 0;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            counter.textContent = Math.floor(current).toLocaleString();
        }, 16);
    });
}

// Setup chart hover effects
function setupChartHoverEffects() {
    Object.values(charts).forEach(chart => {
        if (chart && chart.canvas) {
            chart.canvas.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.02)';
                this.style.transition = 'transform 0.3s ease';
            });
            
            chart.canvas.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
            });
        }
    });
}

// Handle filter form submission
function handleFilterSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const params = new URLSearchParams(formData);
    
    // Show loading state
    showLoadingState();
    
    // Reload page with new filters
    setTimeout(() => {
        window.location.href = window.location.pathname + '?' + params.toString();
    }, 500);
}

// Handle export functionality
function handleExport(event) {
    const exportType = event.target.getAttribute('data-export');
    
    switch(exportType) {
        case 'pdf':
            exportToPDF();
            break;
        case 'excel':
            exportToExcel();
            break;
        case 'csv':
            exportToCSV();
            break;
        default:
            console.warn('Unknown export type:', exportType);
    }
}

// Export to PDF
function exportToPDF() {
    showExportProgress('PDF');
    
    // Simulate PDF export
    setTimeout(() => {
        hideExportProgress();
        showSuccessMessage('گزارش PDF با موفقیت صادر شد');
    }, 3000);
}

// Export to Excel
function exportToExcel() {
    showExportProgress('Excel');
    
    // Simulate Excel export
    setTimeout(() => {
        hideExportProgress();
        showSuccessMessage('گزارش Excel با موفقیت صادر شد');
    }, 2500);
}

// Export to CSV
function exportToCSV() {
    showExportProgress('CSV');
    
    // Simulate CSV export
    setTimeout(() => {
        hideExportProgress();
        showSuccessMessage('گزارش CSV با موفقیت صادر شد');
    }, 2000);
}

// Show export progress
function showExportProgress(format) {
    const progressContainer = document.getElementById('exportProgress');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    if (progressContainer) {
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
        progressText.textContent = 'آماده‌سازی داده‌ها...';
        
        // Simulate progress
        simulateProgress(progressBar, progressText, format);
    }
}

// Hide export progress
function hideExportProgress() {
    const progressContainer = document.getElementById('exportProgress');
    if (progressContainer) {
        progressContainer.style.display = 'none';
    }
}

// Simulate progress
function simulateProgress(progressBar, progressText, format) {
    let progress = 0;
    
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 100) progress = 100;
        
        progressBar.style.width = progress + '%';
        
        if (progress < 30) {
            progressText.textContent = 'آماده‌سازی داده‌ها...';
        } else if (progress < 60) {
            progressText.textContent = `تولید فایل ${format}...`;
        } else if (progress < 90) {
            progressText.textContent = 'اعمال قالب‌بندی...';
        } else {
            progressText.textContent = 'تکمیل صادرات...';
        }
        
        if (progress >= 100) {
            clearInterval(interval);
        }
    }, 200);
}

// Show success message
function showSuccessMessage(message) {
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show position-fixed';
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alert.innerHTML = `
        <i class="fas fa-check-circle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alert);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    }, 5000);
}

// Show loading state
function showLoadingState() {
    const cards = document.querySelectorAll('.dashboard-card, .stat-card, .chart-container');
    cards.forEach(card => {
        card.classList.add('loading');
    });
}

// Hide loading state
function hideLoadingState() {
    const cards = document.querySelectorAll('.dashboard-card, .stat-card, .chart-container');
    cards.forEach(card => {
        card.classList.remove('loading');
    });
}

// Setup real-time updates
function setupRealTimeUpdates() {
    // Update data every 5 minutes
    setInterval(() => {
        updateDashboardData();
    }, 300000);
}

// Update dashboard data
function updateDashboardData() {
    console.log('Updating dashboard data...');
    
    // Show loading state
    showLoadingState();
    
    // Fetch new data
    fetch(window.location.href)
        .then(response => response.text())
        .then(html => {
            // Parse new data and update charts
            // This would typically involve more sophisticated data parsing
            hideLoadingState();
            console.log('Dashboard data updated');
        })
        .catch(error => {
            console.error('Error updating dashboard data:', error);
            hideLoadingState();
        });
}

// Refresh dashboard
function refreshDashboard() {
    console.log('Refreshing dashboard...');
    location.reload();
}

// Reset filters
function resetFilters() {
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.reset();
        window.location.href = window.location.pathname;
    }
}

// Start animations
function startAnimations() {
    // Animate cards on scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, { threshold: 0.1 });
    
    const cards = document.querySelectorAll('.stat-card, .chart-container');
    cards.forEach(card => {
        observer.observe(card);
    });
}

// Utility functions
function formatNumber(number) {
    return new Intl.NumberFormat('fa-IR').format(number);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('fa-IR', {
        style: 'currency',
        currency: 'IRR'
    }).format(amount);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for global access
window.dashboard = {
    refresh: refreshDashboard,
    resetFilters: resetFilters,
    exportToPDF: exportToPDF,
    exportToExcel: exportToExcel,
    exportToCSV: exportToCSV
};
*/

console.log('Dashboard JavaScript loaded successfully');
