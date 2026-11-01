function renderDoughnutChart(canvasId, data, colors, labels) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(centerX, centerY) - 20;
    const innerRadius = radius * 0.55;

    const total = data.reduce((acc, val) => acc + val, 0);
    if (total === 0) {
        ctx.fillStyle = '#94a3b8';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('No data available', centerX, centerY);
        return;
    }

    let startAngle = -Math.PI / 2;
    for (let i = 0; i < data.length; i++) {
        const sliceAngle = (data[i] / total) * 2 * Math.PI;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
        ctx.arc(centerX, centerY, innerRadius, startAngle + sliceAngle, startAngle, true);
        ctx.closePath();
        ctx.fillStyle = colors[i];
        ctx.fill();
        startAngle += sliceAngle;
    }
}

function renderBarChart(canvasId, data, labels, barColor) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const pad = 30;

    const maxVal = Math.max(...data, 5);
    const barWidth = (w - pad * 2) / (data.length * 1.8);
    const spacing = barWidth * 0.8;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#e2e8f0';
    ctx.fillRect(pad, h - pad, w - pad * 2, 1);

    for (let i = 0; i < data.length; i++) {
        const barHeight = (data[i] / maxVal) * (h - pad * 2);
        const x = pad + i * (barWidth + spacing) + spacing / 2;
        const y = h - pad - barHeight;

        ctx.fillStyle = barColor;
        ctx.fillRect(x, y, barWidth, barHeight);

        ctx.fillStyle = '#64748b';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(labels[i], x + barWidth / 2, h - pad + 14);
        ctx.fillText(data[i], x + barWidth / 2, y - 5);
    }
}
