/**
 * Debug script for chart issues
 */

console.log('Debug charts script loaded');

// Test Chart.js availability
function testChartJs() {
    console.log('Testing Chart.js availability...');
    
    if (typeof Chart === 'undefined') {
        console.error('❌ Chart.js is NOT loaded');
        return false;
    } else {
        console.log('✅ Chart.js is loaded, version:', Chart.version);
        return true;
    }
}

// Test canvas elements
function testCanvasElements() {
    console.log('Testing canvas elements...');
    
    const canvasIds = [
        'budgetDistributionChart',
        'monthlyConsumptionChart', 
        'tankhahStatusChart',
        'factorCategoryChart'
    ];
    
    canvasIds.forEach(id => {
        const canvas = document.getElementById(id);
        if (canvas) {
            console.log(`✅ Canvas found: ${id}`);
        } else {
            console.log(`❌ Canvas NOT found: ${id}`);
        }
    });
}

// Test data availability
function testDataAvailability() {
    console.log('Testing data availability...');
    
    if (typeof chartData !== 'undefined') {
        console.log('✅ chartData variable exists');
        console.log('chartData type:', typeof chartData);
        console.log('chartData content:', chartData);
        
        if (chartData && typeof chartData === 'object') {
            const keys = Object.keys(chartData);
            console.log('chartData keys:', keys);
            
            keys.forEach(key => {
                const data = chartData[key];
                console.log(`${key}:`, data, 'length:', Array.isArray(data) ? data.length : 'N/A');
            });
        }
    } else {
        console.log('❌ chartData variable does NOT exist');
    }
}

// Create a simple test chart
function createTestChart() {
    console.log('Creating test chart...');
    
    const testCanvas = document.getElementById('budgetDistributionChart');
    if (!testCanvas) {
        console.error('❌ Test canvas not found');
        return;
    }
    
    try {
        const ctx = testCanvas.getContext('2d');
        const testChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [30, 50, 20],
                    backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
        
        console.log('✅ Test chart created successfully');
        return testChart;
    } catch (error) {
        console.error('❌ Error creating test chart:', error);
        return null;
    }
}

// Run all tests
function runAllTests() {
    console.log('=== Running Chart Debug Tests ===');
    
    testChartJs();
    testCanvasElements();
    testDataAvailability();
    
    // Wait a bit then create test chart
    setTimeout(() => {
        createTestChart();
    }, 1000);
    
    console.log('=== Tests Complete ===');
}

// Auto-run tests when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runAllTests);
} else {
    runAllTests();
}

// Export functions for manual testing
window.ChartDebug = {
    testChartJs,
    testCanvasElements,
    testDataAvailability,
    createTestChart,
    runAllTests
};
