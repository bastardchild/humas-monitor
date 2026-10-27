// UNMER Monitor - Dashboard JavaScript & Chart.js Controllers

let sentimentPieChart = null;
let trendLineChart = null;
let platformBarChart = null;
let engBarChart = null;

function renderCharts(chartData) {
    if (!chartData) return;

    // 1. Sentiment Pie Chart
    const pieCtx = document.getElementById('sentimentPieChart');
    if (pieCtx) {
        if (sentimentPieChart) sentimentPieChart.destroy();
        sentimentPieChart = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: chartData.pie.labels,
                datasets: [{
                    data: chartData.pie.data,
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                    borderColor: '#0a0f14',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, position: 'bottom', labels: { color: '#e6f0e8', font: { family: 'JetBrains Mono' } } }
                },
                cutout: '60%'
            }
        });
    }

    // 2. Trend Line Chart
    const lineCtx = document.getElementById('trendLineChart');
    if (lineCtx) {
        if (trendLineChart) trendLineChart.destroy();
        trendLineChart = new Chart(lineCtx, {
            type: 'line',
            data: {
                labels: chartData.trend.dates,
                datasets: [
                    { label: 'Positive', data: chartData.trend.positive, borderColor: '#10b981', backgroundColor: '#10b981', tension: 0.3 },
                    { label: 'Neutral', data: chartData.trend.neutral, borderColor: '#f59e0b', backgroundColor: '#f59e0b', tension: 0.3 },
                    { label: 'Negative', data: chartData.trend.negative, borderColor: '#ef4444', backgroundColor: '#ef4444', tension: 0.3 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: '#a8c0b0' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#a8c0b0' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                },
                plugins: {
                    legend: { display: true, position: 'top', labels: { color: '#e6f0e8', font: { family: 'JetBrains Mono' } } }
                }
            }
        });
    }

    // 3. Platform Comparison Chart
    const platCtx = document.getElementById('platformBarChart');
    if (platCtx) {
        if (platformBarChart) platformBarChart.destroy();
        platformBarChart = new Chart(platCtx, {
            type: 'bar',
            data: {
                labels: chartData.platform.labels,
                datasets: [
                    { label: 'Positive', data: chartData.platform.positive, backgroundColor: '#10b981' },
                    { label: 'Neutral', data: chartData.platform.neutral, backgroundColor: '#f59e0b' },
                    { label: 'Negative', data: chartData.platform.negative, backgroundColor: '#ef4444' }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: '#a8c0b0' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#a8c0b0' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                },
                plugins: {
                    legend: { display: true, position: 'top', labels: { color: '#e6f0e8', font: { family: 'JetBrains Mono' } } }
                }
            }
        });
    }

    // 4. Engagement Chart
    const engCtx = document.getElementById('engBarChart');
    if (engCtx) {
        if (engBarChart) engBarChart.destroy();
        engBarChart = new Chart(engCtx, {
            type: 'bar',
            data: {
                labels: chartData.engagement.labels,
                datasets: [
                    { label: 'Likes (Avg)', data: chartData.engagement.likes, backgroundColor: '#3b82f6' },
                    { label: 'Comments (Avg)', data: chartData.engagement.comments, backgroundColor: '#ec4899' }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: '#a8c0b0' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#a8c0b0' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                },
                plugins: {
                    legend: { display: true, position: 'top', labels: { color: '#e6f0e8', font: { family: 'JetBrains Mono' } } }
                }
            }
        });
    }
}

// Re-render charts after HTMX swaps
document.addEventListener('htmx:afterSwap', function (evt) {
    if (evt.detail.target.id === 'dashboard-content') {
        const chartDataEl = document.getElementById('chart-data-json');
        if (chartDataEl) {
            try {
                const chartData = JSON.parse(chartDataEl.textContent);
                renderCharts(chartData);
            } catch (e) {
                console.error("Error parsing chart JSON:", e);
            }
        }
    }
});
