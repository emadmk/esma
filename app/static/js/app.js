/* ===== Food Cost Analysis App ===== */

let dashboardData = null;
let barChart = null;
let pieChartInst = null;

// ---------- Helpers ----------

function formatNumber(n) {
    if (n == null) return '0';
    return Math.round(n).toLocaleString('fa-IR');
}

function formatNumberLatin(n) {
    if (n == null) return '0';
    return Math.round(n).toLocaleString('en-US');
}

function showToast(msg, type = 'success') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast show ' + type;
    setTimeout(() => t.className = 'toast', 3000);
}

async function apiFetch(url, options = {}) {
    const resp = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    return resp.json();
}

// ---------- Navigation ----------

document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const page = item.dataset.page;
        switchPage(page);
    });
});

function switchPage(pageName) {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`.nav-item[data-page="${pageName}"]`).classList.add('active');

    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${pageName}`).classList.add('active');

    const titles = {
        dashboard: 'داشبورد',
        foods: 'لیست غذاها',
        ingredients: 'قیمت مواد اولیه',
        overhead: 'هزینه‌های سرباری',
        simulator: 'شبیه‌ساز قیمت',
    };
    document.getElementById('pageTitle').textContent = titles[pageName] || '';

    if (pageName === 'ingredients') loadIngredients();
    if (pageName === 'overhead') loadOverheads();
    if (pageName === 'simulator') loadSimulator();
    if (pageName === 'foods') loadFoodCards();
}

// Mobile menu
document.getElementById('menuToggle').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('open');
});

// ---------- Dashboard ----------

async function loadDashboard() {
    dashboardData = await apiFetch('/api/dashboard');
    renderSummaryCards();
    renderDashboardTable();
    renderCharts();
    renderFoodCards();

    const sp = dashboardData.settings.selling_price_type1 || 2150000;
    document.getElementById('globalSellingPrice').value = formatNumberLatin(sp);
}

function renderSummaryCards() {
    const d = dashboardData.summary;
    const sp = dashboardData.settings.selling_price_type1 || 2150000;
    const html = `
        <div class="summary-card">
            <div class="label">تعداد کل غذاها</div>
            <div class="value neutral">${d.total_foods}</div>
            <div class="sub">نوع اول + نوع دوم</div>
        </div>
        <div class="summary-card">
            <div class="label">غذاهای سودآور</div>
            <div class="value profit">${d.profit_count}</div>
            <div class="sub">از ${d.total_foods} غذا</div>
        </div>
        <div class="summary-card">
            <div class="label">غذاهای زیان‌ده</div>
            <div class="value loss">${d.loss_count}</div>
            <div class="sub">از ${d.total_foods} غذا</div>
        </div>
        <div class="summary-card">
            <div class="label">قیمت فروش قراردادی</div>
            <div class="value neutral">${formatNumber(sp)}</div>
            <div class="sub">ریال - هر پرس</div>
        </div>
        <div class="summary-card">
            <div class="label">میانگین سود/زیان هر پرس</div>
            <div class="value ${d.avg_profit_loss >= 0 ? 'profit' : 'loss'}">${formatNumber(d.avg_profit_loss)}</div>
            <div class="sub">ریال</div>
        </div>
    `;
    document.getElementById('summaryCards').innerHTML = html;
}

function renderDashboardTable() {
    const tbody = document.querySelector('#dashboardTable tbody');
    let html = '';
    dashboardData.foods.forEach((f, i) => {
        html += `
            <tr onclick="showFoodDetail(${f.id})">
                <td>${i + 1}</td>
                <td><strong>${f.name}</strong></td>
                <td>${f.food_type === 1 ? 'نوع اول' : 'نوع دوم'}</td>
                <td class="num">${formatNumber(f.raw_cost)}</td>
                <td class="num">${formatNumber(f.total_cost)}</td>
                <td class="num">${formatNumber(f.selling_price)}</td>
                <td class="num" style="color: ${f.is_profit ? 'var(--success)' : 'var(--danger)'}; font-weight: 700">
                    ${formatNumber(f.profit_loss)}
                </td>
                <td>
                    <span class="badge ${f.is_profit ? 'badge-profit' : 'badge-loss'}">
                        ${f.is_profit ? 'سود' : 'زیان'}
                    </span>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

function renderCharts() {
    // Bar chart
    const ctx1 = document.getElementById('profitLossChart').getContext('2d');
    if (barChart) barChart.destroy();

    const labels = dashboardData.foods.map(f => f.name);
    const values = dashboardData.foods.map(f => f.profit_loss);
    const colors = values.map(v => v >= 0 ? 'rgba(34, 197, 94, 0.7)' : 'rgba(239, 68, 68, 0.7)');
    const borders = values.map(v => v >= 0 ? '#22c55e' : '#ef4444');

    barChart = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'سود/زیان (ریال)',
                data: values,
                backgroundColor: colors,
                borderColor: borders,
                borderWidth: 1,
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => formatNumberLatin(ctx.parsed.y) + ' ریال',
                    },
                },
            },
            scales: {
                x: {
                    ticks: {
                        color: '#8b8fa3',
                        font: { family: 'Vazirmatn', size: 10 },
                        maxRotation: 45,
                    },
                    grid: { color: 'rgba(42, 46, 61, 0.5)' },
                },
                y: {
                    ticks: {
                        color: '#8b8fa3',
                        callback: (v) => (v / 1000000).toFixed(1) + 'M',
                    },
                    grid: { color: 'rgba(42, 46, 61, 0.5)' },
                },
            },
        },
    });

    // Pie chart
    const ctx2 = document.getElementById('pieChart').getContext('2d');
    if (pieChartInst) pieChartInst.destroy();

    pieChartInst = new Chart(ctx2, {
        type: 'doughnut',
        data: {
            labels: ['سودآور', 'زیان‌ده'],
            datasets: [{
                data: [dashboardData.summary.profit_count, dashboardData.summary.loss_count],
                backgroundColor: ['rgba(34, 197, 94, 0.7)', 'rgba(239, 68, 68, 0.7)'],
                borderColor: ['#22c55e', '#ef4444'],
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#8b8fa3',
                        font: { family: 'Vazirmatn', size: 12 },
                        padding: 16,
                    },
                },
            },
            cutout: '65%',
        },
    });
}

// ---------- Food Cards & Detail ----------

function loadFoodCards() {
    if (!dashboardData) return;
    const container = document.getElementById('foodCards');
    let html = '';
    dashboardData.foods.forEach(f => {
        html += `
            <div class="food-card ${f.is_profit ? 'profit' : 'loss'}" onclick="showFoodDetail(${f.id})">
                <div class="food-name">${f.name}</div>
                <div class="food-meta">
                    <span class="label">هزینه مواد خام</span>
                    <span class="val">${formatNumber(f.raw_cost)}</span>
                </div>
                <div class="food-meta">
                    <span class="label">هزینه تمام‌شده</span>
                    <span class="val">${formatNumber(f.total_cost)}</span>
                </div>
                <div class="food-meta">
                    <span class="label">قیمت فروش</span>
                    <span class="val">${formatNumber(f.selling_price)}</span>
                </div>
                <div class="food-pl ${f.is_profit ? 'profit' : 'loss'}">
                    ${f.is_profit ? '+' : ''}${formatNumber(f.profit_loss)} ریال
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

async function showFoodDetail(foodId) {
    const data = await apiFetch(`/api/food/${foodId}`);
    const f = data.food;
    const ings = data.ingredients;
    const ohs = data.overheads;

    document.getElementById('modalFoodName').textContent = f.name;

    const isProfit = f.profit_loss >= 0;
    const fixedOH = ohs.filter(o => o.param_type === 'fixed').reduce((s, o) => s + o.value, 0);
    const base = f.raw_cost + fixedOH;

    let html = `
        <div class="cost-breakdown">
            <div class="cost-item">
                <span class="lbl">هزینه مواد خام</span>
                <span class="val">${formatNumber(f.raw_cost)} ریال</span>
            </div>
            <div class="cost-item">
                <span class="lbl">هزینه سرباری ثابت</span>
                <span class="val">${formatNumber(fixedOH)} ریال</span>
            </div>
            <div class="cost-item">
                <span class="lbl">مجموع پایه</span>
                <span class="val">${formatNumber(base)} ریال</span>
            </div>
            <div class="cost-item">
                <span class="lbl">قیمت تمام‌شده</span>
                <span class="val" style="color: var(--primary-light)">${formatNumber(f.total_cost)} ریال</span>
            </div>
            <div class="cost-item">
                <span class="lbl">قیمت فروش</span>
                <span class="val">${formatNumber(f.selling_price)} ریال</span>
            </div>
            <div class="cost-item" style="background: ${isProfit ? 'var(--success-bg)' : 'var(--danger-bg)'}">
                <span class="lbl" style="color: ${isProfit ? 'var(--success)' : 'var(--danger)'}; font-weight: 700">
                    ${isProfit ? 'سود' : 'زیان'}
                </span>
                <span class="val" style="color: ${isProfit ? 'var(--success)' : 'var(--danger)'}; font-size: 16px">
                    ${isProfit ? '+' : ''}${formatNumber(f.profit_loss)} ریال
                </span>
            </div>
        </div>

        <h3>ریز مواد اولیه (مرتب بر اساس هزینه)</h3>
        <table class="data-table ing-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>ماده</th>
                    <th>مقدار</th>
                    <th>واحد</th>
                    <th>هزینه (ریال)</th>
                    <th>سهم از کل</th>
                </tr>
            </thead>
            <tbody>
    `;

    const totalIngCost = ings.reduce((s, i) => s + (i.cost || 0), 0);
    ings.forEach((ing, idx) => {
        const pct = totalIngCost > 0 ? ((ing.cost || 0) / totalIngCost * 100).toFixed(1) : 0;
        html += `
            <tr>
                <td>${idx + 1}</td>
                <td>${ing.ingredient_name}</td>
                <td class="num">${ing.amount}</td>
                <td>${ing.unit || 'گرم'}</td>
                <td class="num">${formatNumber(ing.cost)}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <div style="width: 60px; height: 6px; background: var(--bg); border-radius: 3px; overflow: hidden;">
                            <div style="width: ${pct}%; height: 100%; background: var(--primary); border-radius: 3px;"></div>
                        </div>
                        <span style="font-size: 11px; color: var(--text-muted)">${pct}%</span>
                    </div>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    document.getElementById('modalBody').innerHTML = html;

    document.getElementById('foodModal').classList.add('active');
}

document.getElementById('modalClose').addEventListener('click', () => {
    document.getElementById('foodModal').classList.remove('active');
});

document.getElementById('foodModal').addEventListener('click', (e) => {
    if (e.target === document.getElementById('foodModal')) {
        document.getElementById('foodModal').classList.remove('active');
    }
});

// ---------- Ingredients ----------

async function loadIngredients() {
    const data = await apiFetch('/api/ingredients');
    renderIngredientsTable(data.ingredients);
}

function renderIngredientsTable(ingredients) {
    const tbody = document.querySelector('#ingredientTable tbody');
    let html = '';
    ingredients.forEach((ing, i) => {
        html += `
            <tr>
                <td>${i + 1}</td>
                <td><strong>${ing.name}</strong></td>
                <td>${ing.unit || '-'}</td>
                <td>
                    <input type="text" class="editable-input"
                        value="${formatNumberLatin(ing.price_per_gram)}"
                        data-id="${ing.id}"
                        data-field="price_per_gram"
                        data-original="${ing.price_per_gram}">
                </td>
                <td>
                    <input type="text" class="editable-input"
                        value="${formatNumberLatin(ing.price_per_unit)}"
                        data-id="${ing.id}"
                        data-field="price_per_unit"
                        data-original="${ing.price_per_unit}">
                </td>
                <td style="color: var(--text-muted); font-size: 12px; white-space: normal; max-width: 200px">
                    ${ing.notes || '-'}
                </td>
                <td>
                    <button class="btn btn-primary btn-sm save-ingredient" data-id="${ing.id}">ذخیره</button>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = html;

    // Bind save buttons
    document.querySelectorAll('.save-ingredient').forEach(btn => {
        btn.addEventListener('click', async () => {
            const id = btn.dataset.id;
            const row = btn.closest('tr');
            const ppg = parseFloat(row.querySelector('[data-field="price_per_gram"]').value.replace(/,/g, '')) || 0;
            const ppu = parseFloat(row.querySelector('[data-field="price_per_unit"]').value.replace(/,/g, '')) || 0;

            await apiFetch(`/api/ingredients/${id}`, {
                method: 'PUT',
                body: JSON.stringify({ price_per_gram: ppg, price_per_unit: ppu }),
            });

            showToast('قیمت ماده اولیه به‌روزرسانی شد');
            loadDashboard();
        });
    });
}

// Search ingredients
document.getElementById('ingredientSearch').addEventListener('input', (e) => {
    const q = e.target.value.trim();
    const rows = document.querySelectorAll('#ingredientTable tbody tr');
    rows.forEach(row => {
        const name = row.querySelector('td:nth-child(2)').textContent;
        row.style.display = name.includes(q) ? '' : 'none';
    });
});

// ---------- Overhead ----------

async function loadOverheads() {
    const data = await apiFetch('/api/dashboard');
    renderOverheadCards(data.overheads);
}

function renderOverheadCards(overheads) {
    const container = document.getElementById('overheadCards');
    let html = '';
    overheads.forEach(oh => {
        const unit = oh.param_type === 'percent' ? 'درصد' : 'ریال';
        html += `
            <div class="overhead-card">
                <div class="oh-label">${oh.label}</div>
                <div class="oh-desc">${oh.description || ''}</div>
                <div class="oh-input-row">
                    <input type="text" class="oh-input"
                        value="${oh.param_type === 'percent' ? oh.value : formatNumberLatin(oh.value)}"
                        data-id="${oh.id}"
                        data-type="${oh.param_type}">
                    <span class="oh-unit">${unit}</span>
                    <button class="btn btn-primary btn-sm save-overhead" data-id="${oh.id}">ذخیره</button>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;

    document.querySelectorAll('.save-overhead').forEach(btn => {
        btn.addEventListener('click', async () => {
            const id = btn.dataset.id;
            const card = btn.closest('.overhead-card');
            const input = card.querySelector('.oh-input');
            const val = parseFloat(input.value.replace(/,/g, '')) || 0;

            await apiFetch(`/api/overhead/${id}`, {
                method: 'PUT',
                body: JSON.stringify({ value: val }),
            });

            showToast('پارامتر سرباری به‌روزرسانی شد');
            loadDashboard();
        });
    });
}

// ---------- Selling Price ----------

document.getElementById('updateSellingPrice').addEventListener('click', async () => {
    const val = parseFloat(document.getElementById('globalSellingPrice').value.replace(/,/g, '')) || 0;
    if (val <= 0) {
        showToast('قیمت فروش معتبر نیست', 'error');
        return;
    }
    await apiFetch('/api/settings', {
        method: 'PUT',
        body: JSON.stringify({
            selling_price_type1: val,
            selling_price_type2: val,
        }),
    });
    showToast('قیمت فروش به‌روزرسانی شد');
    loadDashboard();
});

// ---------- Simulator ----------

async function loadSimulator() {
    const data = await apiFetch('/api/dashboard');

    // Key ingredients for simulation
    const keyIngredients = [
        'برنج ایرانی', 'برنج مخلوط', 'گوشت گوساله گرم', 'گوشت گوسفند گرم',
        'شنیسل مرغ گرم', 'مرغ گرم', 'ماهی قزل آلا', 'روغن مایع',
        'پیاز', 'گوجه فرنگی', 'سیب زمینی', 'رب گوجه',
    ];

    const ingData = await apiFetch('/api/ingredients');
    const allIngs = ingData.ingredients;

    let html = '';
    keyIngredients.forEach(name => {
        const ing = allIngs.find(i => i.name === name);
        if (ing) {
            html += `
                <div class="sim-row">
                    <span class="sim-label">${name}</span>
                    <input type="text" class="sim-input sim-field sim-ing-input"
                        data-name="${name}"
                        value="${formatNumberLatin(ing.price_per_gram)}"
                        placeholder="${formatNumberLatin(ing.price_per_gram)}">
                </div>
            `;
        }
    });
    document.getElementById('simIngredients').innerHTML = html;

    let ohHtml = '';
    data.overheads.forEach(oh => {
        const unit = oh.param_type === 'percent' ? '%' : 'ریال';
        ohHtml += `
            <div class="sim-row">
                <span class="sim-label">${oh.label}</span>
                <input type="text" class="sim-input sim-field sim-oh-input"
                    data-name="${oh.name}"
                    value="${oh.param_type === 'percent' ? oh.value : formatNumberLatin(oh.value)}"
                    placeholder="${oh.value}">
                <span style="color: var(--text-dim); font-size: 11px; min-width: 30px">${unit}</span>
            </div>
        `;
    });
    document.getElementById('simOverheads').innerHTML = ohHtml;

    const sp = data.settings.selling_price_type1 || 2150000;
    document.getElementById('simSellingPrice').value = formatNumberLatin(sp);
}

document.getElementById('runSimulation').addEventListener('click', async () => {
    const ingChanges = {};
    document.querySelectorAll('.sim-ing-input').forEach(input => {
        const val = parseFloat(input.value.replace(/,/g, ''));
        if (!isNaN(val)) {
            ingChanges[input.dataset.name] = val;
        }
    });

    const ohChanges = {};
    document.querySelectorAll('.sim-oh-input').forEach(input => {
        const val = parseFloat(input.value.replace(/,/g, ''));
        if (!isNaN(val)) {
            ohChanges[input.dataset.name] = val;
        }
    });

    const sp = parseFloat(document.getElementById('simSellingPrice').value.replace(/,/g, '')) || null;

    const data = await apiFetch('/api/simulate', {
        method: 'POST',
        body: JSON.stringify({
            ingredient_changes: ingChanges,
            overhead_changes: ohChanges,
            selling_price: sp,
        }),
    });

    let html = '';
    let totalPL = 0;
    data.foods.forEach(f => {
        totalPL += f.profit_loss;
        html += `
            <div class="sim-result-item ${f.is_profit ? 'profit' : 'loss'}">
                <span class="name">${f.name}</span>
                <span class="amount">${f.is_profit ? '+' : ''}${formatNumber(f.profit_loss)}</span>
            </div>
        `;
    });

    const avgPL = totalPL / data.foods.length;
    html = `
        <div style="text-align: center; margin-bottom: 16px; padding: 16px; border-radius: 8px; background: ${avgPL >= 0 ? 'var(--success-bg)' : 'var(--danger-bg)'}">
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px">میانگین سود/زیان هر پرس</div>
            <div style="font-size: 28px; font-weight: 800; color: ${avgPL >= 0 ? 'var(--success)' : 'var(--danger)'}; direction: ltr">
                ${avgPL >= 0 ? '+' : ''}${formatNumber(avgPL)} ریال
            </div>
        </div>
    ` + html;

    document.getElementById('simResults').innerHTML = html;
    showToast('شبیه‌سازی انجام شد');
});

// ---------- Init ----------

loadDashboard();
