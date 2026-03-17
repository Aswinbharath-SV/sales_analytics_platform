document.addEventListener('DOMContentLoaded', () => {
    // ==== Upload Logic ====
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('csvFile');
    const uploadStatus = document.getElementById('uploadStatus');

    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.remove('dragover'), false);
        });

        dropArea.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFile(files[0]);
        }, false);

        fileInput.addEventListener('change', (e) => {
            handleFile(e.target.files[0]);
        });
    }

    function handleFile(file) {
        if (!file) return;
        if (!file.name.endsWith('.csv')) {
            uploadStatus.innerHTML = '<span class="text-danger">Please upload a valid CSV file.</span>';
            return;
        }

        const formData = new FormData();
        formData.append("file", file);
        uploadStatus.innerHTML = '<span class="text-primary"><i class="fa-solid fa-spinner fa-spin"></i> Uploading...</span>';

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    uploadStatus.innerHTML = `<span class="text-danger">${data.error}</span>`;
                } else {
                    uploadStatus.innerHTML = `<span class="text-success"><i class="fa-solid fa-check-circle"></i> ${data.filename} loaded. (${data.rows} rows)</span>`;
                    loadAnalyticsData(); // Refresh dashboard
                    addChatMessage('ai-message', `I see you just uploaded <strong>${data.filename}</strong>. What would you like to know about it?`, '<i class="fa-solid fa-robot"></i>');
                }
            })
            .catch(error => {
                uploadStatus.innerHTML = `<span class="text-danger">Upload failed.</span>`;
                console.error(error);
            });
    }

    const btnLoadSample = document.getElementById('btnLoadSample');
    if (btnLoadSample) {
        btnLoadSample.addEventListener('click', () => {
            uploadStatus.innerHTML = '<span class="text-primary"><i class="fa-solid fa-spinner fa-spin"></i> Loading Sample Database...</span>';

            fetch('/load-sample', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        uploadStatus.innerHTML = `<span class="text-danger">${data.error}</span>`;
                    } else {
                        uploadStatus.innerHTML = `<span class="text-success"><i class="fa-solid fa-bolt"></i> Sample ${data.filename} loaded. (${data.rows} rows)</span>`;
                        loadAnalyticsData(); // Refresh dashboard
                        addChatMessage('ai-message', `I've loaded the sample Kaggle dataset containing <strong>${data.rows}</strong> sales records. How can I help?`, '<i class="fa-solid fa-robot"></i>');
                    }
                })
                .catch(error => {
                    uploadStatus.innerHTML = `<span class="text-danger">Failed to load sample data.</span>`;
                    console.error(error);
                });
        });
    }

    // ==== Dashboard Analytics Logic ====
    let mainChartInstance = null;
    let secondaryChartInstance = null;
    let fallbackCharts = {};

    function loadAnalyticsData() {
        const kpiContainer = document.getElementById('kpiContainer');
        const analyticsChartsContainer = document.getElementById('analyticsChartsContainer');

        // Show loading skeletons if KPIs are found
        if (kpiContainer) {
            kpiContainer.innerHTML = `
                <div class="kpi-card glass-card skeleton-loading"></div>
                <div class="kpi-card glass-card skeleton-loading"></div>
                <div class="kpi-card glass-card skeleton-loading"></div>
                <div class="kpi-card glass-card skeleton-loading"></div>
            `;
        }

        fetch('/analytics-data')
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    console.log(data.error);
                    if (kpiContainer) {
                        kpiContainer.innerHTML = `
                        <div class="kpi-card glass-card fade-in" style="grid-column: 1 / -1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding: 40px;">
                            <i class="fa-solid fa-folder-open text-primary" style="font-size: 3rem; margin-bottom: 15px;"></i>
                            <h3 style="margin-bottom: 5px;">No Data Loaded</h3>
                            <p class="text-secondary" style="margin-bottom: 15px;">Please upload a CSV file or use the "Load Sample Data" button located in the sidebar to visualize metrics.</p>
                        </div>`;
                    }
                    if (analyticsChartsContainer) {
                        analyticsChartsContainer.innerHTML = '<p class="text-center" style="width: 100%;">No charts to display. Please load a dataset first.</p>';
                    }
                    return;
                }

                // Render KPIs on Dashboard
                if (kpiContainer) {
                    let kpisHtml = '';
                    const metrics = data.metrics;

                    // Format number helper
                    const fmt = (num) => new Intl.NumberFormat('en-US', { notation: "compact", compactDisplay: "short" }).format(num);

                    // Always show rows
                    kpisHtml += `
                        <div class="kpi-card glass-card fade-in-up">
                            <div class="kpi-title">Total Records</div>
                            <div class="kpi-value text-primary">${fmt(metrics.total_rows || 0)}</div>
                        </div>
                    `;

                    // Display up to 3 more numeric totals
                    let count = 0;
                    for (const [key, val] of Object.entries(metrics)) {
                        if (key.startsWith('total_') && key !== 'total_rows' && key !== 'total_columns' && count < 3) {
                            const cleanKey = key.replace('total_', '').replace('_', ' ');
                            kpisHtml += `
                                <div class="kpi-card glass-card fade-in-up delay-1">
                                    <div class="kpi-title">Total ${cleanKey}</div>
                                    <div class="kpi-value gradient-text">${fmt(val || 0)}</div>
                                </div>
                            `;
                            count++;
                        }
                    }
                    kpiContainer.innerHTML = kpisHtml;
                }

                // AI Summary for Analytics page
                const aiSummary = document.getElementById('aiSummaryText');
                if (aiSummary) {
                    const rowCount = data.metrics.total_rows || 0;
                    const colCount = data.metrics.total_columns || 0;
                    let summaryText = `Analyzed dataset with ${rowCount} records and ${colCount} properties. `;
                    for (const [key, val] of Object.entries(data.metrics)) {
                        if (key.startsWith('total_') && key !== 'total_rows' && key !== 'total_columns') {
                            summaryText += `Total ${key.replace('total_', '')} sums up to ${new Intl.NumberFormat().format(val)}. `;
                            break;
                        }
                    }
                    aiSummary.innerHTML = summaryText + "All systems operational.";
                }

                // Render Dashboard Charts
                const mainCanvas = document.getElementById('mainChart');
                const secCanvas = document.getElementById('secondaryChart');

                if (data.charts && data.charts.length > 0) {
                    if (mainCanvas) {
                        renderChart(mainCanvas, data.charts[0], 'mainChartInstance');
                    }
                    if (secCanvas && data.charts.length > 1) {
                        renderChart(secCanvas, data.charts[1], 'secondaryChartInstance');
                    }
                }

                // Render Analytics View Charts (if on analytics page)
                if (analyticsChartsContainer && data.charts && data.charts.length > 0) {
                    for (let i = 0; i < 3; i++) {
                        const can = document.getElementById(`analyticsChart${i + 1}`);
                        if (can && data.charts[i]) {
                            renderChart(can, data.charts[i], null, true);
                        }
                    }
                }
            })
            .catch(err => {
                console.warn("Failed to load analytics: ", err);
            });
    }

    const chartColors = {
        primary: 'rgb(59, 130, 246)',
        primaryBg: 'rgba(59, 130, 246, 0.2)',
        secondary: 'rgb(139, 92, 246)',
        secondaryBg: 'rgba(139, 92, 246, 0.2)',
        tertiary: 'rgb(16, 185, 129)',
        text: '#94A3B8',
        grid: 'rgba(255,255,255,0.05)'
    };

    const multiColors = [
        'rgba(59, 130, 246, 0.7)',
        'rgba(139, 92, 246, 0.7)',
        'rgba(16, 185, 129, 0.7)',
        'rgba(245, 158, 11, 0.7)',
        'rgba(239, 68, 68, 0.7)',
        'rgba(6, 182, 212, 0.7)'
    ];

    function renderChart(canvasElement, chartData, instanceKey, isDarkBg = false) {
        if (!canvasElement) return;
        const ctx = canvasElement.getContext('2d');

        // Destroy existing if re-rendering dashboard globals
        if (instanceKey === 'mainChartInstance' && mainChartInstance) mainChartInstance.destroy();
        if (instanceKey === 'secondaryChartInstance' && secondaryChartInstance) secondaryChartInstance.destroy();

        // Also destroy previous canvas specific chart if it exists
        if (canvasElement.id && fallbackCharts[canvasElement.id]) {
            fallbackCharts[canvasElement.id].destroy();
        }

        let bgColor = chartData.type === 'pie' ? multiColors : chartColors.primaryBg;
        let borderColor = chartData.type === 'pie' ? '#0F172A' : chartColors.primary;

        if (chartData.type === 'line') {
            bgColor = chartColors.secondaryBg;
            borderColor = chartColors.secondary;
        }

        const config = {
            type: chartData.type, // 'bar', 'line', 'pie'
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: chartData.title,
                    data: chartData.values,
                    backgroundColor: bgColor,
                    borderColor: borderColor,
                    borderWidth: 2,
                    tension: 0.4, // smooth curves for line
                    fill: chartData.type === 'line' // fill below line
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: chartData.type === 'pie',
                        labels: { color: chartColors.text }
                    }
                },
                scales: chartData.type !== 'pie' ? {
                    x: {
                        grid: { color: chartColors.grid, drawBorder: false },
                        ticks: { color: chartColors.text }
                    },
                    y: {
                        grid: { color: chartColors.grid, drawBorder: false },
                        ticks: { color: chartColors.text }
                    }
                } : {}
            }
        };

        const newChart = new Chart(ctx, config);

        if (instanceKey === 'mainChartInstance') mainChartInstance = newChart;
        else if (instanceKey === 'secondaryChartInstance') secondaryChartInstance = newChart;

        if (canvasElement.id) {
            fallbackCharts[canvasElement.id] = newChart;
        }
    }

    // Call initially if we are on dashboard or analytics
    if (document.getElementById('kpiContainer') || document.getElementById('analyticsChartsContainer')) {
        loadAnalyticsData();
    }

    // ==== Chatbot Logic ====
    const chatWidget = document.querySelector('.ai-chat-widget');
    const minimizeBtn = document.getElementById('minimizeChat');
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const chatMessages = document.getElementById('chatMessages');

    if (minimizeBtn && chatWidget) {
        minimizeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            chatWidget.classList.toggle('minimized');
            const icon = minimizeBtn.querySelector('i');
            if (chatWidget.classList.contains('minimized')) {
                icon.classList.remove('fa-chevron-down');
                icon.classList.add('fa-chevron-up');
            } else {
                icon.classList.remove('fa-chevron-up');
                icon.classList.add('fa-chevron-down');
                setTimeout(() => chatInput.focus(), 300);
            }
        });

        // Click on minimized widget to open
        chatWidget.addEventListener('click', () => {
            if (chatWidget.classList.contains('minimized')) {
                minimizeBtn.click();
            }
        });
    }

    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const question = chatInput.value.trim();
            if (!question) return;

            // user message
            addChatMessage('user-message', question, 'U');
            chatInput.value = '';

            // typing indicator
            const typingId = 'typing-' + Date.now();
            addChatMessage('ai-message', '<i class="fa-solid fa-ellipsis fa-beat"></i>', '<i class="fa-solid fa-robot"></i>', typingId);

            const formData = new FormData();
            formData.append('question', question);

            fetch('/ask', {
                method: 'POST',
                body: formData
            })
                .then(res => res.json())
                .then(data => {
                    document.getElementById(typingId).remove();
                    addChatMessage('ai-message', data.answer, '<i class="fa-solid fa-robot"></i>');
                })
                .catch(err => {
                    document.getElementById(typingId).remove();
                    addChatMessage('ai-message', 'Sorry, I lost connection to the server.', '<i class="fa-solid fa-robot"></i>');
                    console.error(err);
                });
        });
    }

    function addChatMessage(typeClass, htmlContent, avatarHtml, id = '') {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${typeClass} fade-in-up`;
        if (id) msgDiv.id = id;

        msgDiv.innerHTML = `
            <div class="avatar">${avatarHtml}</div>
            <div class="text">${htmlContent}</div>
        `;

        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
