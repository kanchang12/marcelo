// Global state
let charts = {};
let pinnedCharts = JSON.parse(localStorage.getItem('pinnedCharts')) || [];
let currentData = {};

// Color schemes
const colorSchemes = {
    blue: ['#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe'],
    green: ['#10b981', '#34d399', '#6ee7b7', '#a7f3d0', '#d1fae5'],
    purple: ['#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe', '#ede9fe'],
    rainbow: ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6']
};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initDateFilter();
    loadMerchantInfo();
    loadDashboardData();
    initChartBuilder();
    loadPinnedCharts();
    initTransactions();
    
    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadDashboardData();
        showNotification('Data refreshed successfully', 'success');
    });
});

// Navigation
function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all buttons
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Hide all sections
            document.querySelectorAll('.content-section').forEach(section => {
                section.classList.remove('active');
            });
            
            // Show selected section
            const view = btn.dataset.view;
            document.getElementById(`${view}-section`).classList.add('active');
        });
    });
}

// Date Filter
function initDateFilter() {
    const today = new Date().toISOString().split('T')[0];
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    
    document.getElementById('end-date').value = today;
    document.getElementById('start-date').value = thirtyDaysAgo;
    
    document.getElementById('apply-filter').addEventListener('click', () => {
        loadDashboardData();
        showNotification('Filter applied', 'success');
    });
}

// Load Merchant Info
async function loadMerchantInfo() {
    try {
        const response = await fetch('/api/merchant');
        const data = await response.json();
        
        if (data.merchant_profile) {
            document.getElementById('merchant-name').textContent = 
                data.merchant_profile.doing_business_as?.business_name || 
                data.merchant_profile.merchant_code;
        }
    } catch (error) {
        console.error('Error loading merchant info:', error);
    }
}

// Load Dashboard Data
async function loadDashboardData() {
    try {
        // Load summary
        const summaryResponse = await fetch('/api/analytics/summary');
        const summary = await summaryResponse.json();
        
        document.getElementById('total-revenue').textContent = `£${summary.total_revenue.toFixed(2)}`;
        document.getElementById('total-transactions').textContent = summary.total_transactions;
        document.getElementById('avg-transaction').textContent = `£${summary.avg_transaction.toFixed(2)}`;
        document.getElementById('failed-transactions').textContent = summary.failed_transactions;
        
        // Store for chart builder
        currentData.summary = summary;
        
        // Load and create charts
        await Promise.all([
            loadDailyRevenue(),
            loadPaymentTypes(),
            loadHourlyDistribution(),
            loadCardTypes()
        ]);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showNotification('Error loading data', 'error');
    }
}

// Daily Revenue Chart
async function loadDailyRevenue() {
    try {
        const response = await fetch('/api/analytics/daily?days=30');
        const data = await response.json();
        
        currentData.daily = data;
        
        const ctx = document.getElementById('daily-revenue-chart');
        
        if (charts.dailyRevenue) {
            charts.dailyRevenue.destroy();
        }
        
        charts.dailyRevenue = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.date),
                datasets: [{
                    label: 'Revenue (£)',
                    data: data.map(d => d.revenue),
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading daily revenue:', error);
    }
}

// Payment Types Chart
async function loadPaymentTypes() {
    try {
        const response = await fetch('/api/analytics/summary');
        const data = await response.json();
        
        const paymentTypes = data.payment_types;
        const ctx = document.getElementById('payment-types-chart');
        
        if (charts.paymentTypes) {
            charts.paymentTypes.destroy();
        }
        
        charts.paymentTypes = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(paymentTypes),
                datasets: [{
                    data: Object.values(paymentTypes),
                    backgroundColor: colorSchemes.rainbow
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading payment types:', error);
    }
}

// Hourly Distribution Chart
async function loadHourlyDistribution() {
    try {
        const response = await fetch('/api/analytics/hourly?days=7');
        const data = await response.json();
        
        currentData.hourly = data;
        
        const ctx = document.getElementById('hourly-chart');
        
        if (charts.hourly) {
            charts.hourly.destroy();
        }
        
        charts.hourly = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => `${d.hour}:00`),
                datasets: [{
                    label: 'Transactions',
                    data: data.map(d => d.count),
                    backgroundColor: '#10b981'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading hourly distribution:', error);
    }
}

// Card Types Chart
async function loadCardTypes() {
    try {
        const response = await fetch('/api/analytics/card-types?days=30');
        const data = await response.json();
        
        currentData.cardTypes = data;
        
        const ctx = document.getElementById('card-types-chart');
        
        if (charts.cardTypes) {
            charts.cardTypes.destroy();
        }
        
        charts.cardTypes = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: Object.keys(data),
                datasets: [{
                    data: Object.keys(data).map(key => data[key].count),
                    backgroundColor: colorSchemes.blue
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading card types:', error);
    }
}

// Chart Builder
function initChartBuilder() {
    const previewBtn = document.getElementById('preview-chart-btn');
    const saveBtn = document.getElementById('save-chart-btn');
    
    previewBtn.addEventListener('click', previewCustomChart);
    saveBtn.addEventListener('click', saveCustomChart);
}

async function previewCustomChart() {
    const title = document.getElementById('chart-title').value || 'Custom Chart';
    const type = document.getElementById('chart-type').value;
    const dataSource = document.getElementById('data-source').value;
    const period = document.getElementById('time-period').value;
    const colorScheme = document.getElementById('color-scheme').value;
    
    const chartData = await getChartData(dataSource, period);
    
    const ctx = document.getElementById('preview-chart');
    
    if (charts.preview) {
        charts.preview.destroy();
    }
    
    charts.preview = createCustomChart(ctx, type, title, chartData, colorScheme);
}

async function saveCustomChart() {
    const title = document.getElementById('chart-title').value;
    
    if (!title) {
        showNotification('Please enter a chart title', 'error');
        return;
    }
    
    const chartConfig = {
        id: Date.now().toString(),
        title: title,
        type: document.getElementById('chart-type').value,
        dataSource: document.getElementById('data-source').value,
        period: document.getElementById('time-period').value,
        colorScheme: document.getElementById('color-scheme').value,
        timestamp: new Date().toISOString()
    };
    
    pinnedCharts.push(chartConfig);
    localStorage.setItem('pinnedCharts', JSON.stringify(pinnedCharts));
    
    loadPinnedCharts();
    showNotification('Chart saved and pinned successfully', 'success');
    
    // Switch to My Charts view
    document.querySelector('[data-view="charts"]').click();
}

async function getChartData(dataSource, period) {
    let response;
    
    switch (dataSource) {
        case 'daily':
            response = await fetch(`/api/analytics/daily?days=${period}`);
            const dailyData = await response.json();
            return {
                labels: dailyData.map(d => d.date),
                datasets: [{
                    label: 'Revenue',
                    data: dailyData.map(d => d.revenue)
                }]
            };
            
        case 'hourly':
            response = await fetch(`/api/analytics/hourly?days=${period}`);
            const hourlyData = await response.json();
            return {
                labels: hourlyData.map(d => `${d.hour}:00`),
                datasets: [{
                    label: 'Transactions',
                    data: hourlyData.map(d => d.count)
                }]
            };
            
        case 'payment-types':
            response = await fetch('/api/analytics/summary');
            const summaryData = await response.json();
            return {
                labels: Object.keys(summaryData.payment_types),
                datasets: [{
                    data: Object.values(summaryData.payment_types)
                }]
            };
            
        case 'card-types':
            response = await fetch(`/api/analytics/card-types?days=${period}`);
            const cardData = await response.json();
            return {
                labels: Object.keys(cardData),
                datasets: [{
                    data: Object.keys(cardData).map(key => cardData[key].count)
                }]
            };
            
        case 'transaction-count':
            response = await fetch(`/api/analytics/daily?days=${period}`);
            const countData = await response.json();
            return {
                labels: countData.map(d => d.date),
                datasets: [{
                    label: 'Transactions',
                    data: countData.map(d => d.count)
                }]
            };
    }
}

function createCustomChart(ctx, type, title, data, colorScheme) {
    const colors = colorSchemes[colorScheme];
    
    return new Chart(ctx, {
        type: type === 'area' ? 'line' : type,
        data: {
            labels: data.labels,
            datasets: data.datasets.map(dataset => ({
                ...dataset,
                backgroundColor: type === 'area' ? 
                    `rgba(${hexToRgb(colors[0])}, 0.2)` : 
                    colors,
                borderColor: colors[0],
                fill: type === 'area',
                tension: 0.4
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom'
                },
                title: {
                    display: true,
                    text: title
                }
            },
            scales: type !== 'pie' && type !== 'doughnut' ? {
                y: {
                    beginAtZero: true
                }
            } : {}
        }
    });
}

// Pinned Charts
async function loadPinnedCharts() {
    const container = document.getElementById('pinned-charts-container');
    
    if (pinnedCharts.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>📌 No pinned charts yet</p>
                <p>Pin charts from Overview or create custom ones in Chart Builder</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = '';
    
    for (const chartConfig of pinnedCharts) {
        const chartDiv = document.createElement('div');
        chartDiv.className = 'chart-container';
        chartDiv.innerHTML = `
            <div class="chart-header">
                <h3>${chartConfig.title}</h3>
                <button class="btn-pin pinned" data-id="${chartConfig.id}">🗑️ Remove</button>
            </div>
            <canvas id="pinned-${chartConfig.id}"></canvas>
        `;
        
        container.appendChild(chartDiv);
        
        // Load and render chart
        const chartData = await getChartData(chartConfig.dataSource, chartConfig.period);
        const ctx = document.getElementById(`pinned-${chartConfig.id}`);
        createCustomChart(ctx, chartConfig.type, '', chartData, chartConfig.colorScheme);
        
        // Remove button
        chartDiv.querySelector('.btn-pin').addEventListener('click', () => {
            removePinnedChart(chartConfig.id);
        });
    }
    
    // Clear all button
    document.getElementById('clear-pins-btn').addEventListener('click', () => {
        if (confirm('Remove all pinned charts?')) {
            pinnedCharts = [];
            localStorage.setItem('pinnedCharts', JSON.stringify(pinnedCharts));
            loadPinnedCharts();
            showNotification('All charts removed', 'success');
        }
    });
}

function removePinnedChart(id) {
    pinnedCharts = pinnedCharts.filter(chart => chart.id !== id);
    localStorage.setItem('pinnedCharts', JSON.stringify(pinnedCharts));
    loadPinnedCharts();
    showNotification('Chart removed', 'success');
}

// Transactions
async function initTransactions() {
    try {
        const response = await fetch('/api/transactions?limit=100');
        const data = await response.json();
        
        const tbody = document.getElementById('transactions-body');
        tbody.innerHTML = '';
        
        if (!data.items || data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="loading">No transactions found</td></tr>';
            return;
        }
        
        data.items.forEach(txn => {
            const date = new Date(txn.timestamp);
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${date.toLocaleDateString()}</td>
                <td>${date.toLocaleTimeString()}</td>
                <td>£${txn.amount.toFixed(2)}</td>
                <td><span class="status-badge status-${txn.status.toLowerCase()}">${txn.status}</span></td>
                <td>${txn.payment_type || 'N/A'}</td>
                <td>${txn.card_type || 'N/A'}</td>
                <td>${txn.transaction_code || txn.id}</td>
            `;
            tbody.appendChild(row);
        });
        
        // Export CSV
        document.getElementById('export-csv-btn').addEventListener('click', () => {
            exportToCSV(data.items);
        });
        
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

function exportToCSV(transactions) {
    const headers = ['Date', 'Time', 'Amount', 'Status', 'Payment Type', 'Card Type', 'Transaction ID'];
    const rows = transactions.map(txn => {
        const date = new Date(txn.timestamp);
        return [
            date.toLocaleDateString(),
            date.toLocaleTimeString(),
            txn.amount,
            txn.status,
            txn.payment_type || 'N/A',
            txn.card_type || 'N/A',
            txn.transaction_code || txn.id
        ];
    });
    
    let csvContent = headers.join(',') + '\n';
    rows.forEach(row => {
        csvContent += row.join(',') + '\n';
    });
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transactions-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    
    showNotification('CSV exported successfully', 'success');
}

// Utilities
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? 
        `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : 
        '0, 0, 0';
}

function showNotification(message, type) {
    // Simple notification - you can enhance this with a proper notification system
    alert(message);
                                                            }
  
