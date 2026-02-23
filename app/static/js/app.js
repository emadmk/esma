/* ===== Food Cost Analysis - Frontend App ===== */
const $ = (s, p) => (p || document).querySelector(s);
const $$ = (s, p) => [...(p || document).querySelectorAll(s)];
const fmt = n => n == null ? '0' : Math.round(n).toLocaleString('fa-IR');
const fmtEn = n => n == null ? '0' : Math.round(n).toLocaleString('en-US');

let dashboardData = null;
let charts = {};

// ===== API helpers =====
async function api(url, opts) {
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...opts, body: opts?.body ? JSON.stringify(opts.body) : undefined,
    });
    return res.json();
}

function toast(msg) {
    const t = $('#toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

// ===== Sidebar & Navigation =====
const sidebar = $('#sidebar');
const overlay = $('#overlay');
const pages = {
    dashboard: { title: 'داشبورد', load: loadDashboard },
    ingredients: { title: 'مواد اولیه', load: loadIngredients },
    foods1: { title: 'ریز غذا نوع ۱', load: () => loadFoods(1) },
    foods2: { title: 'ریز غذا نوع ۲', load: () => loadFoods(2) },
    consumables: { title: 'اقلام مصرفی', load: loadConsumables },
    equipment: { title: 'تجهیزات و استهلاک', load: loadEquipment },
    labor: { title: 'نیروی انسانی و رانندگان', load: loadLabor },
    overhead_params: { title: 'پارامترهای سرباری', load: loadOverheadParams },
    overhead_calc: { title: 'محاسبات سرباری', load: loadOverheadCalc },
    side_dishes: { title: 'دورچین', load: loadSideDishes },
    appendix: { title: 'الحاقیه', load: loadAppendix },
    weekly_menu: { title: 'برنامه غذایی هفتگی', load: loadWeeklyMenu },
    analysis: { title: 'آنالیز پیوست', load: loadAnalysis },
    simulator: { title: 'شبیه‌ساز قیمت', load: loadSimulator },
};

$$('.nav-item').forEach(item => {
    item.addEventListener('click', e => {
        e.preventDefault();
        const page = item.dataset.page;
        navigateTo(page);
    });
});

$('#menuToggle').addEventListener('click', () => { sidebar.classList.add('open'); overlay.classList.add('show'); });
$('#sidebarClose').addEventListener('click', closeSidebar);
overlay.addEventListener('click', closeSidebar);
function closeSidebar() { sidebar.classList.remove('open'); overlay.classList.remove('show'); }

$('#modalClose').addEventListener('click', () => $('#modal').classList.remove('show'));
$('#modal').addEventListener('click', e => { if (e.target === $('#modal')) $('#modal').classList.remove('show'); });

function navigateTo(page) {
    $$('.nav-item').forEach(n => n.classList.remove('active'));
    $(`.nav-item[data-page="${page}"]`)?.classList.add('active');
    $('#pageTitle').textContent = pages[page]?.title || '';
    closeSidebar();
    pages[page]?.load();
}

// Selling price update
$('#updatePrices').addEventListener('click', async () => {
    const sp1 = parseFloat($('#sp1').value.replace(/,/g, '')) || 0;
    const sp2 = parseFloat($('#sp2').value.replace(/,/g, '')) || 0;
    await api('/api/settings', { method: 'PUT', body: { selling_price_type1: sp1, selling_price_type2: sp2 } });
    toast('قیمت فروش بروزرسانی شد');
    navigateTo('dashboard');
});

function showModal(title, html) {
    $('#modalTitle').textContent = title;
    $('#modalBody').innerHTML = html;
    $('#modal').classList.add('show');
}

// ===== Dashboard =====
async function loadDashboard() {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div><p>در حال بارگذاری...</p></div>';
    const data = await api('/api/dashboard');
    dashboardData = data;

    $('#sp1').value = fmtEn(data.settings.selling_price_type1);
    $('#sp2').value = fmtEn(data.settings.selling_price_type2);

    const s = data.summary;
    c.innerHTML = `
        <div class="summary-grid">
            <div class="summary-card info">
                <div class="summary-label">کل غذاها</div>
                <div class="summary-value">${s.total_foods}</div>
                <div class="summary-sub">نوع ۱ و نوع ۲</div>
            </div>
            <div class="summary-card profit">
                <div class="summary-label">غذاهای سودده</div>
                <div class="summary-value" style="color:var(--success)">${s.profit_count}</div>
                <div class="summary-sub">مجموع سود: ${fmt(s.total_profit)} ریال</div>
            </div>
            <div class="summary-card loss">
                <div class="summary-label">غذاهای زیان‌ده</div>
                <div class="summary-value" style="color:var(--danger)">${s.loss_count}</div>
                <div class="summary-sub">مجموع زیان: ${fmt(s.total_loss)} ریال</div>
            </div>
            <div class="summary-card warning">
                <div class="summary-label">میانگین سود/زیان</div>
                <div class="summary-value ${s.avg_profit_loss >= 0 ? 'num-positive' : 'num-negative'}">${fmt(s.avg_profit_loss)}</div>
                <div class="summary-sub">ریال به ازای هر پرس</div>
            </div>
        </div>
        <div class="charts-grid">
            <div class="chart-card"><h3>سود و زیان هر غذا (ریال)</h3><canvas id="barChart"></canvas></div>
            <div class="chart-card"><h3>نسبت سود به زیان</h3><canvas id="pieChart"></canvas></div>
        </div>
        <div class="card">
            <div class="card-header">جدول غذاها</div>
            <div class="card-body">
                <div class="search-bar">
                    <input type="text" class="search-input" id="dashSearch" placeholder="جستجوی نام غذا...">
                    <button class="filter-btn active" data-filter="all">همه</button>
                    <button class="filter-btn" data-filter="1">نوع ۱</button>
                    <button class="filter-btn" data-filter="2">نوع ۲</button>
                    <button class="filter-btn" data-filter="profit">سودده</button>
                    <button class="filter-btn" data-filter="loss">زیان‌ده</button>
                </div>
                <div class="table-wrapper">
                    <table class="data-table" id="dashTable">
                        <thead><tr>
                            <th>#</th><th>کد</th><th>نام غذا</th><th>نوع</th>
                            <th>هزینه خام</th><th>هزینه تمام‌شده</th><th>قیمت فروش</th>
                            <th>سود/زیان</th><th>درصد</th><th>وضعیت</th>
                        </tr></thead>
                        <tbody id="dashTableBody"></tbody>
                    </table>
                </div>
            </div>
        </div>`;

    renderDashTable(data.foods);
    renderCharts(data.foods);

    // Search and filter
    $('#dashSearch')?.addEventListener('input', () => filterDashTable(data.foods));
    $$('.filter-btn').forEach(b => b.addEventListener('click', () => {
        $$('.filter-btn').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        filterDashTable(data.foods);
    }));
}

function filterDashTable(foods) {
    const q = ($('#dashSearch')?.value || '').trim();
    const f = $('.filter-btn.active')?.dataset.filter || 'all';
    let filtered = foods;
    if (q) filtered = filtered.filter(x => x.name.includes(q));
    if (f === '1') filtered = filtered.filter(x => x.food_type === 1);
    if (f === '2') filtered = filtered.filter(x => x.food_type === 2);
    if (f === 'profit') filtered = filtered.filter(x => x.is_profit);
    if (f === 'loss') filtered = filtered.filter(x => !x.is_profit);
    renderDashTable(filtered);
}

function renderDashTable(foods) {
    const body = $('#dashTableBody');
    if (!body) return;
    body.innerHTML = foods.map((f, i) => `
        <tr style="cursor:pointer" onclick="showFoodDetail(${f.id})">
            <td class="num">${i + 1}</td>
            <td class="num">${f.code}</td>
            <td>${f.name}</td>
            <td><span class="badge ${f.food_type === 1 ? 'badge-type1' : 'badge-type2'}">نوع ${f.food_type}</span></td>
            <td class="num price">${fmt(f.raw_cost)}</td>
            <td class="num price">${fmt(f.total_cost)}</td>
            <td class="num price">${fmt(f.selling_price)}</td>
            <td class="num ${f.is_profit ? 'profit' : 'loss'}">${fmt(f.profit_loss)}</td>
            <td class="num ${f.is_profit ? 'profit' : 'loss'}">${f.profit_loss_pct}%</td>
            <td><span class="badge ${f.is_profit ? 'badge-profit' : 'badge-loss'}">${f.is_profit ? 'سود' : 'زیان'}</span></td>
        </tr>
    `).join('');
}

function renderCharts(foods) {
    Object.values(charts).forEach(c => c.destroy?.());
    charts = {};

    const barCtx = document.getElementById('barChart');
    if (barCtx) {
        charts.bar = new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: foods.map(f => f.name),
                datasets: [{
                    label: 'سود/زیان',
                    data: foods.map(f => f.profit_loss),
                    backgroundColor: foods.map(f => f.is_profit ? 'rgba(16,185,129,.7)' : 'rgba(239,68,68,.7)'),
                    borderRadius: 6, borderSkipped: false,
                }]
            },
            options: {
                indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { callback: v => (v / 1000000).toFixed(1) + 'M', font: { family: 'Vazirmatn' } }, grid: { color: '#f1f5f9' } },
                    y: { ticks: { font: { family: 'Vazirmatn', size: 11 } }, grid: { display: false } }
                }
            }
        });
    }

    const pieCtx = document.getElementById('pieChart');
    if (pieCtx) {
        const profitCount = foods.filter(f => f.is_profit).length;
        const lossCount = foods.filter(f => !f.is_profit).length;
        charts.pie = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: ['سودده', 'زیان‌ده'],
                datasets: [{ data: [profitCount, lossCount], backgroundColor: ['#10b981', '#ef4444'], borderWidth: 0 }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { font: { family: 'Vazirmatn', size: 13 } } } },
                cutout: '65%',
            }
        });
    }
}

// ===== Food Detail Modal =====
window.showFoodDetail = async function(foodId) {
    const data = await api(`/api/foods/${foodId}`);
    const f = data.food;
    const ings = data.ingredients;
    let html = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px">
            <div class="summary-card info"><div class="summary-label">کد</div><div class="summary-value">${f.code}</div></div>
            <div class="summary-card ${f.total_cost <= (dashboardData?.settings?.['selling_price_type' + f.food_type] || 2150000) ? 'profit' : 'loss'}">
                <div class="summary-label">هزینه تمام‌شده</div>
                <div class="summary-value">${fmt(f.total_cost)}</div>
            </div>
        </div>
        <h3 style="margin-bottom:12px">مواد اولیه (${ings.length} ماده)</h3>
        <div class="table-wrapper">
        <table class="data-table">
            <thead><tr><th>#</th><th>ماده غذایی</th><th>مقدار</th><th>واحد</th><th>هزینه (ریال)</th></tr></thead>
            <tbody>${ings.map((ing, i) => `
                <tr>
                    <td class="num">${i + 1}</td>
                    <td>${ing.ingredient_name}</td>
                    <td class="num">${ing.amount}</td>
                    <td>${ing.unit}</td>
                    <td class="num price">${fmt(ing.cost)}</td>
                </tr>
            `).join('')}</tbody>
        </table></div>
        <div style="margin-top:16px;padding:12px;background:#f8fafc;border-radius:8px;text-align:center">
            <strong>جمع هزینه مواد خام: ${fmt(f.raw_cost)} ریال</strong>
        </div>`;
    showModal(f.name, html);
};

// ===== Ingredients =====
async function loadIngredients() {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const data = await api('/api/ingredients');
    const cats = [...new Set(data.ingredients.map(i => i.category))];

    c.innerHTML = `
        <div class="search-bar">
            <input type="text" class="search-input" id="ingSearch" placeholder="جستجوی نام ماده اولیه...">
            ${cats.map(cat => `<button class="filter-btn ${cat === '' ? '' : ''}" data-cat="${cat}">${cat || 'بدون دسته'}</button>`).join('')}
        </div>
        <div class="card"><div class="card-body">
            <div class="table-wrapper">
                <table class="data-table">
                    <thead><tr><th>#</th><th>نام ماده</th><th>واحد</th><th>دسته</th><th>قیمت هر گرم</th><th>قیمت واحد</th><th>توضیحات</th><th></th></tr></thead>
                    <tbody id="ingBody"></tbody>
                </table>
            </div>
        </div></div>`;

    renderIngredients(data.ingredients);
    $('#ingSearch')?.addEventListener('input', () => {
        const q = $('#ingSearch').value.trim();
        renderIngredients(data.ingredients.filter(i => !q || i.name.includes(q)));
    });
}

function renderIngredients(items) {
    const body = $('#ingBody');
    if (!body) return;
    body.innerHTML = items.map((ing, i) => `
        <tr>
            <td class="num">${i + 1}</td>
            <td><strong>${ing.name}</strong></td>
            <td>${ing.unit}</td>
            <td><span class="badge badge-type1">${ing.category}</span></td>
            <td class="num"><span class="editable-cell" onclick="editIngredient(${ing.id}, 'price_per_gram', ${ing.price_per_gram}, this)">${fmt(ing.price_per_gram)}</span></td>
            <td class="num"><span class="editable-cell" onclick="editIngredient(${ing.id}, 'price_per_unit', ${ing.price_per_unit}, this)">${fmt(ing.price_per_unit)}</span></td>
            <td class="text-muted" style="font-size:.8rem;max-width:200px">${ing.notes}</td>
            <td></td>
        </tr>
    `).join('');
}

window.editIngredient = function(id, field, currentVal, el) {
    const input = document.createElement('input');
    input.className = 'edit-input';
    input.value = Math.round(currentVal);
    input.type = 'number';
    el.replaceWith(input);
    input.focus();
    input.select();

    const save = async () => {
        const val = parseFloat(input.value) || 0;
        const other = field === 'price_per_gram' ? 'price_per_unit' : 'price_per_gram';
        const body = { [field]: val };
        // Keep other field value
        const row = input.closest('tr');
        const cells = row.querySelectorAll('.editable-cell');
        body[other] = currentVal; // simplified
        await api(`/api/ingredients/${id}`, { method: 'PUT', body: { price_per_gram: field === 'price_per_gram' ? val : currentVal, price_per_unit: field === 'price_per_unit' ? val : currentVal } });
        toast('قیمت بروزرسانی شد');
        loadIngredients();
    };
    input.addEventListener('blur', save);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') loadIngredients(); });
};

// ===== Foods (Type 1 & 2) =====
async function loadFoods(type) {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const data = await api(`/api/foods?type=${type}`);
    const settings = (await api('/api/settings')).settings;
    const sp = parseFloat(settings[`selling_price_type${type}`]) || 2150000;

    c.innerHTML = `
        <div class="search-bar">
            <input type="text" class="search-input" id="foodSearch" placeholder="جستجوی نام غذا...">
        </div>
        <div class="food-grid" id="foodGrid"></div>`;

    renderFoodCards(data.foods, sp);
    $('#foodSearch')?.addEventListener('input', () => {
        const q = $('#foodSearch').value.trim();
        renderFoodCards(data.foods.filter(f => !q || f.name.includes(q)), sp);
    });
}

function renderFoodCards(foods, sp) {
    const grid = $('#foodGrid');
    if (!grid) return;
    grid.innerHTML = foods.map(f => {
        const diff = sp - f.total_cost;
        const isProfit = diff >= 0;
        return `
        <div class="food-card" onclick="showFoodDetail(${f.id})">
            <div class="food-card-header">
                <span class="food-card-name">${f.name}</span>
                <span class="food-card-code">کد ${f.code}</span>
            </div>
            <div class="food-card-body">
                <div class="food-card-row"><span class="label">هزینه خام:</span><span class="value">${fmt(f.raw_cost)}</span></div>
                <div class="food-card-row"><span class="label">هزینه تمام‌شده:</span><span class="value">${fmt(f.total_cost)}</span></div>
                <div class="food-card-row"><span class="label">قیمت فروش:</span><span class="value">${fmt(sp)}</span></div>
            </div>
            <div class="food-card-footer">
                <span class="badge ${isProfit ? 'badge-profit' : 'badge-loss'}" style="font-size:.9rem;padding:6px 16px">
                    ${isProfit ? 'سود' : 'زیان'}: ${fmt(Math.abs(diff))} ریال
                </span>
            </div>
        </div>`;
    }).join('');
}

// ===== Consumables =====
async function loadConsumables() {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const data = await api('/api/consumables');

    c.innerHTML = `
        <div class="summary-grid">
            <div class="summary-card info">
                <div class="summary-label">تعداد اقلام</div>
                <div class="summary-value">${data.consumables.length}</div>
            </div>
            <div class="summary-card warning">
                <div class="summary-label">جمع هزینه سرباری هر پرس</div>
                <div class="summary-value">${fmt(data.total)}</div>
                <div class="summary-sub">ریال</div>
            </div>
        </div>
        <div class="card"><div class="card-header">لیست اقلام مصرفی</div><div class="card-body">
            <div class="table-wrapper">
                <table class="data-table">
                    <thead><tr><th>#</th><th>نام قلم</th><th>توضیحات</th><th>هزینه هر پرس (ریال)</th></tr></thead>
                    <tbody>${data.consumables.map((item, i) => `
                        <tr>
                            <td class="num">${i + 1}</td>
                            <td><strong>${item.name}</strong></td>
                            <td style="font-size:.8rem;color:var(--text-secondary)">${item.description}</td>
                            <td class="num"><span class="editable-cell" onclick="editConsumable(${item.id}, ${item.cost_per_serving}, this)">${fmt(item.cost_per_serving)}</span></td>
                        </tr>
                    `).join('')}</tbody>
                </table>
            </div>
        </div></div>`;
}

window.editConsumable = function(id, currentVal, el) {
    const input = document.createElement('input');
    input.className = 'edit-input'; input.value = Math.round(currentVal); input.type = 'number';
    el.replaceWith(input); input.focus(); input.select();
    const save = async () => {
        await api(`/api/consumables/${id}`, { method: 'PUT', body: { cost_per_serving: parseFloat(input.value) || 0, name: input.closest('tr').children[1].textContent, description: input.closest('tr').children[2].textContent } });
        toast('بروزرسانی شد'); loadConsumables();
    };
    input.addEventListener('blur', save);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') loadConsumables(); });
};

// ===== Equipment =====
async function loadEquipment() {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const data = await api('/api/equipment');

    c.innerHTML = `
        <div class="summary-grid">
            <div class="summary-card info">
                <div class="summary-label">تعداد تجهیزات</div>
                <div class="summary-value">${data.equipment.length}</div>
            </div>
            <div class="summary-card warning">
                <div class="summary-label">جمع کل هزینه تجهیزات</div>
                <div class="summary-value">${fmt(data.total)}</div>
                <div class="summary-sub">ریال</div>
            </div>
        </div>
        <div class="card"><div class="card-body">
            <div class="search-bar"><input type="text" class="search-input" id="eqSearch" placeholder="جستجو..."></div>
            <div class="table-wrapper">
                <table class="data-table" id="eqTable">
                    <thead><tr><th>#</th><th>نام تجهیزات</th><th>تعداد</th><th>واحد</th><th>قیمت واحد</th><th>قیمت کل</th></tr></thead>
                    <tbody id="eqBody"></tbody>
                </table>
            </div>
        </div></div>`;

    renderEquipment(data.equipment);
    $('#eqSearch')?.addEventListener('input', () => {
        const q = $('#eqSearch').value.trim();
        renderEquipment(data.equipment.filter(e => !q || e.name.includes(q)));
    });
}

function renderEquipment(items) {
    const body = $('#eqBody');
    if (!body) return;
    body.innerHTML = items.map((e, i) => `
        <tr>
            <td class="num">${i + 1}</td>
            <td>${e.name}</td>
            <td class="num">${e.quantity}</td>
            <td>${e.unit}</td>
            <td class="num price">${fmt(e.unit_price)}</td>
            <td class="num price">${fmt(e.total_price)}</td>
        </tr>
    `).join('');
}

// ===== Labor & Drivers =====
async function loadLabor() {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const [laborData, driverData] = await Promise.all([api('/api/labor'), api('/api/drivers')]);

    c.innerHTML = `
        <div class="tabs">
            <div class="tab active" data-tab="labor">نیروی کار</div>
            <div class="tab" data-tab="drivers">رانندگان</div>
        </div>
        <div id="laborContent">
            <div class="card"><div class="card-header">آنالیز نیروی کار</div><div class="card-body">
                <div class="table-wrapper">
                    <table class="data-table">
                        <thead><tr><th>#</th><th>دسته</th><th>پست</th><th>شرح شغل</th><th>تعداد پست</th><th>تعداد نفر</th><th>حقوق ناخالص</th><th>حقوق ماهیانه</th></tr></thead>
                        <tbody>${laborData.positions.map((p, i) => `
                            <tr>
                                <td class="num">${i + 1}</td>
                                <td><span class="badge badge-type1">${p.category}</span></td>
                                <td>${p.position_name}</td>
                                <td style="font-size:.8rem">${p.job_title}</td>
                                <td class="num">${p.post_count}</td>
                                <td class="num">${p.person_count}</td>
                                <td class="num price">${fmt(p.gross_salary)}</td>
                                <td class="num price">${fmt(p.avg_monthly_salary)}</td>
                            </tr>
                        `).join('')}</tbody>
                    </table>
                </div>
            </div></div>
        </div>
        <div id="driversContent" style="display:none">
            <div class="card"><div class="card-header">آنالیز رانندگان داخل مجتمع</div><div class="card-body">
                <div class="table-wrapper">
                    <table class="data-table">
                        <thead><tr><th>#</th><th>دسته</th><th>شرح شغل</th><th>تعداد پست</th><th>تعداد نفر</th><th>حقوق ناخالص</th><th>حقوق ماهیانه</th></tr></thead>
                        <tbody>${driverData.positions.map((p, i) => `
                            <tr>
                                <td class="num">${i + 1}</td>
                                <td>${p.position_category}</td>
                                <td>${p.job_title}</td>
                                <td class="num">${p.post_count}</td>
                                <td class="num">${p.person_count}</td>
                                <td class="num price">${fmt(p.gross_salary)}</td>
                                <td class="num price">${fmt(p.avg_monthly_salary)}</td>
                            </tr>
                        `).join('')}</tbody>
                    </table>
                </div>
            </div></div>
        </div>`;

    $$('.tab').forEach(t => t.addEventListener('click', () => {
        $$('.tab').forEach(x => x.classList.remove('active'));
        t.classList.add('active');
        $('#laborContent').style.display = t.dataset.tab === 'labor' ? '' : 'none';
        $('#driversContent').style.display = t.dataset.tab === 'drivers' ? '' : 'none';
    }));
}

// ===== Overhead Params =====
async function loadOverheadParams() {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const data = await api('/api/overhead_params');
    const shared = data.params.filter(p => p.food_type === 0);
    const t1 = data.params.filter(p => p.food_type === 1);
    const t2 = data.params.filter(p => p.food_type === 2);

    c.innerHTML = `
        <h3 class="mb-16">پارامترهای مشترک</h3>
        <div class="param-grid mb-24">${shared.map(renderParamCard).join('')}</div>
        <h3 class="mb-16">پارامترهای نوع ۱</h3>
        <div class="param-grid mb-24">${t1.map(renderParamCard).join('')}</div>
        <h3 class="mb-16">پارامترهای نوع ۲</h3>
        <div class="param-grid">${t2.map(renderParamCard).join('')}</div>`;
}

function renderParamCard(p) {
    return `
        <div class="param-card">
            <div class="param-label">${p.label}</div>
            <div class="param-desc">${p.description}</div>
            <div class="param-source">منبع: ${p.source_sheet}</div>
            <div class="param-value-row">
                <input class="param-input" type="number" value="${Math.round(p.value * 100) / 100}" id="param_${p.id}">
                <span class="param-type ${p.param_type === 'fixed' ? 'param-type-fixed' : 'param-type-percent'}">
                    ${p.param_type === 'fixed' ? 'ریال/پرس' : 'درصد'}
                </span>
                <button class="btn btn-primary btn-sm" onclick="saveParam(${p.id})">ثبت</button>
            </div>
        </div>`;
}

window.saveParam = async function(id) {
    const val = parseFloat($(`#param_${id}`).value) || 0;
    await api(`/api/overhead_params/${id}`, { method: 'PUT', body: { value: val } });
    toast('پارامتر بروزرسانی شد');
};

// ===== Overhead Calculations =====
async function loadOverheadCalc() {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    c.innerHTML = `
        <div class="tabs">
            <div class="tab active" data-tab="t1">سرباری نوع ۱</div>
            <div class="tab" data-tab="t2">سرباری نوع ۲</div>
        </div>
        <div id="calcContent"></div>`;

    loadOverheadCalcType('1');

    $$('.tab').forEach(t => t.addEventListener('click', () => {
        $$('.tab').forEach(x => x.classList.remove('active'));
        t.classList.add('active');
        loadOverheadCalcType(t.dataset.tab === 't1' ? '1' : '2');
    }));
}

async function loadOverheadCalcType(type) {
    const cont = $('#calcContent');
    cont.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const data = await api(`/api/overhead_calc?type=${type}`);
    const items = data.data.filter(d => d.food_code > 0);
    const avg = data.data.find(d => d.food_code === 0);

    if (type === '1') {
        cont.innerHTML = `<div class="card"><div class="card-body"><div class="table-wrapper">
            <table class="data-table">
                <thead><tr><th>کد</th><th>غذا</th><th>خام</th><th>سرباری</th><th>بیمه تکمیلی</th><th>رانندگان</th><th>ماشین</th><th>نیرو</th><th>استهلاک</th><th>میوه</th><th>آب</th><th>دلستر</th><th>دورچین</th><th>تورم</th><th>بیمه قرارداد</th><th>مالیات</th><th>سود</th></tr></thead>
                <tbody>${items.map(d => `
                    <tr>
                        <td class="num">${d.food_code}</td><td>${d.food_name}</td>
                        <td class="num price">${fmt(d.raw_cost)}</td>
                        <td class="num">${fmt(d.consumables)}</td>
                        <td class="num">${fmt(d.supplementary_insurance)}</td>
                        <td class="num">${fmt(d.driver_salary)}</td>
                        <td class="num">${fmt(d.vehicle_rental)}</td>
                        <td class="num">${fmt(d.labor_cost)}</td>
                        <td class="num">${fmt(d.equipment_depreciation)}</td>
                        <td class="num">${fmt(d.fruit)}</td>
                        <td class="num">${fmt(d.mineral_water)}</td>
                        <td class="num">${fmt(d.delster)}</td>
                        <td class="num">${fmt(d.dessert_garnish)}</td>
                        <td class="num">${fmt(d.inflation)}</td>
                        <td class="num">${fmt(d.contract_insurance)}</td>
                        <td class="num">${fmt(d.tax)}</td>
                        <td class="num">${fmt(d.profit_margin)}</td>
                    </tr>
                `).join('')}
                ${avg ? `<tr style="font-weight:700;background:#f8fafc"><td></td><td>میانگین</td>
                    <td class="num">${fmt(avg.raw_cost)}</td><td class="num">${fmt(avg.consumables)}</td>
                    <td class="num">${fmt(avg.supplementary_insurance)}</td><td class="num">${fmt(avg.driver_salary)}</td>
                    <td class="num">${fmt(avg.vehicle_rental)}</td><td class="num">${fmt(avg.labor_cost)}</td>
                    <td class="num">${fmt(avg.equipment_depreciation)}</td><td class="num">${fmt(avg.fruit)}</td>
                    <td class="num">${fmt(avg.mineral_water)}</td><td class="num">${fmt(avg.delster)}</td>
                    <td class="num">${fmt(avg.dessert_garnish)}</td><td class="num">${fmt(avg.inflation)}</td>
                    <td class="num">${fmt(avg.contract_insurance)}</td><td class="num">${fmt(avg.tax)}</td>
                    <td class="num">${fmt(avg.profit_margin)}</td></tr>` : ''}
                </tbody>
            </table></div></div></div>`;
    } else {
        cont.innerHTML = `<div class="card"><div class="card-body"><div class="table-wrapper">
            <table class="data-table">
                <thead><tr><th>کد</th><th>غذا</th><th>خام</th><th>سرباری</th><th>بیمه</th><th>رانندگان</th><th>ماشین</th><th>نیرو</th><th>استهلاک</th><th>نوشیدنی</th><th>دورچین</th><th>تورم</th><th>بیمه قرارداد</th><th>مالیات</th><th>سود</th><th>تمام‌شده</th></tr></thead>
                <tbody>${items.map(d => `
                    <tr>
                        <td class="num">${d.food_code}</td><td>${d.food_name}</td>
                        <td class="num price">${fmt(d.raw_cost)}</td>
                        <td class="num">${fmt(d.consumables)}</td>
                        <td class="num">${fmt(d.supplementary_insurance)}</td>
                        <td class="num">${fmt(d.driver_salary)}</td>
                        <td class="num">${fmt(d.vehicle_rental)}</td>
                        <td class="num">${fmt(d.labor_cost)}</td>
                        <td class="num">${fmt(d.equipment_depreciation)}</td>
                        <td class="num">${fmt(d.drink)}</td>
                        <td class="num">${fmt(d.dessert_garnish)}</td>
                        <td class="num">${fmt(d.inflation)}</td>
                        <td class="num">${fmt(d.contract_insurance)}</td>
                        <td class="num">${fmt(d.tax)}</td>
                        <td class="num">${fmt(d.profit_margin)}</td>
                        <td class="num price fw-bold">${fmt(d.total_cost)}</td>
                    </tr>
                `).join('')}
                ${avg ? `<tr style="font-weight:700;background:#f8fafc"><td></td><td>میانگین</td>
                    <td class="num">${fmt(avg.raw_cost)}</td><td class="num">${fmt(avg.consumables)}</td>
                    <td class="num">${fmt(avg.supplementary_insurance)}</td><td class="num">${fmt(avg.driver_salary)}</td>
                    <td class="num">${fmt(avg.vehicle_rental)}</td><td class="num">${fmt(avg.labor_cost)}</td>
                    <td class="num">${fmt(avg.equipment_depreciation)}</td><td class="num">${fmt(avg.drink)}</td>
                    <td class="num">${fmt(avg.dessert_garnish)}</td><td class="num">${fmt(avg.inflation)}</td>
                    <td class="num">${fmt(avg.contract_insurance)}</td><td class="num">${fmt(avg.tax)}</td>
                    <td class="num">${fmt(avg.profit_margin)}</td><td class="num fw-bold">${fmt(avg.total_cost)}</td></tr>` : ''}
                </tbody>
            </table></div></div></div>`;
    }
}

// ===== Side Dishes =====
async function loadSideDishes() {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const data = await api('/api/side_dishes');
    const g1 = data.side_dishes.filter(d => d.col_group === 1);
    const g2 = data.side_dishes.filter(d => d.col_group === 2);
    const g3 = data.side_dishes.filter(d => d.col_group === 3);

    c.innerHTML = `
        <h3 class="mb-16">دورچین - گروه ۱</h3>
        <div class="dish-grid mb-24">${g1.map(d => `
            <div class="dish-card">
                <div><div class="dish-name">${d.name}</div>${d.notes ? `<div class="dish-notes">${d.notes}</div>` : ''}</div>
                <span class="editable-cell dish-price" onclick="editSideDish(${d.id}, ${d.price}, this)">${fmt(d.price)}</span>
            </div>
        `).join('')}</div>
        <h3 class="mb-16">دورچین - گروه ۲</h3>
        <div class="dish-grid mb-24">${g2.map(d => `
            <div class="dish-card">
                <div><div class="dish-name">${d.name}</div>${d.notes ? `<div class="dish-notes">${d.notes}</div>` : ''}</div>
                <span class="editable-cell dish-price" onclick="editSideDish(${d.id}, ${d.price}, this)">${fmt(d.price)}</span>
            </div>
        `).join('')}</div>
        <h3 class="mb-16">ظروف و لوازم</h3>
        <div class="dish-grid">${g3.map(d => `
            <div class="dish-card">
                <div><div class="dish-name">${d.name}</div></div>
                <span class="editable-cell dish-price" onclick="editSideDish(${d.id}, ${d.price}, this)">${fmt(d.price)}</span>
            </div>
        `).join('')}</div>`;
}

window.editSideDish = function(id, currentVal, el) {
    const input = document.createElement('input');
    input.className = 'edit-input'; input.value = Math.round(currentVal); input.type = 'number';
    input.style.width = '120px';
    el.replaceWith(input); input.focus(); input.select();
    const save = async () => {
        await api(`/api/side_dishes/${id}`, { method: 'PUT', body: { price: parseFloat(input.value) || 0, name: input.closest('.dish-card').querySelector('.dish-name').textContent, notes: '' } });
        toast('بروزرسانی شد'); loadSideDishes();
    };
    input.addEventListener('blur', save);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') loadSideDishes(); });
};

// ===== Appendix =====
async function loadAppendix() {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const data = await api('/api/appendix');
    const items = data.items.filter(i => i.food_code > 0);
    const avg = data.items.find(i => i.food_name === 'میانگین');

    c.innerHTML = `
        <div class="card"><div class="card-header">الحاقیه - قیمت‌های بروز</div><div class="card-body">
            <div class="table-wrapper">
                <table class="data-table">
                    <thead><tr><th>ردیف</th><th>کد</th><th>نام غذا</th><th>قیمت الحاقیه</th><th>قیمت تمام‌شده</th><th>تفاوت</th></tr></thead>
                    <tbody>
                        ${items.map((item, i) => {
                            const diff = item.appendix_price - item.calculated_price;
                            return `<tr>
                                <td class="num">${i + 1}</td>
                                <td class="num">${item.food_code}</td>
                                <td>${item.food_name}</td>
                                <td class="num price"><span class="editable-cell" onclick="editAppendix(${item.id}, ${item.appendix_price}, this)">${fmt(item.appendix_price)}</span></td>
                                <td class="num price">${fmt(item.calculated_price)}</td>
                                <td class="num ${diff >= 0 ? 'loss' : 'profit'}">${fmt(diff)}</td>
                            </tr>`;
                        }).join('')}
                        ${avg ? `<tr style="font-weight:700;background:#f8fafc"><td></td><td></td><td>میانگین</td><td class="num price">${fmt(avg.appendix_price)}</td><td></td><td></td></tr>` : ''}
                    </tbody>
                </table>
            </div>
        </div></div>`;
}

window.editAppendix = function(id, currentVal, el) {
    const input = document.createElement('input');
    input.className = 'edit-input'; input.value = Math.round(currentVal); input.type = 'number';
    el.replaceWith(input); input.focus(); input.select();
    const save = async () => {
        await api(`/api/appendix/${id}`, { method: 'PUT', body: { appendix_price: parseFloat(input.value) || 0 } });
        toast('بروزرسانی شد'); loadAppendix();
    };
    input.addEventListener('blur', save);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') loadAppendix(); });
};

// ===== Weekly Menu =====
async function loadWeeklyMenu() {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const data = await api('/api/weekly_menu');

    c.innerHTML = `<div class="menu-grid">${data.menu.map(day => `
        <div class="menu-card">
            <div class="menu-card-header">
                <span class="menu-card-day">${day.day_name}</span>
                <span class="menu-card-date">${day.date_str}</span>
            </div>
            <div class="menu-card-body">
                <div class="menu-card-item"><span class="menu-card-label">غذا نوع ۱:</span><span>${day.food_type1}</span></div>
                ${day.food_type1_special ? `<div class="menu-card-item"><span class="menu-card-label">اختصاصی:</span><span>${day.food_type1_special}</span></div>` : ''}
                <div class="menu-card-item"><span class="menu-card-label">غذا نوع ۲:</span><span>${day.food_type2}</span></div>
                ${day.dessert_desc ? `<div class="menu-card-item"><span class="menu-card-label">دسر:</span><span style="font-size:.8rem">${day.dessert_desc}</span></div>` : ''}
                ${day.drink ? `<div class="menu-card-item"><span class="menu-card-label">نوشیدنی:</span><span>${day.drink}</span></div>` : ''}
                ${day.salad ? `<div class="menu-card-item"><span class="menu-card-label">سالاد:</span><span>${day.salad} (${fmt(day.salad_price)} ریال)</span></div>` : ''}
                ${day.special_item ? `<div class="menu-card-item"><span class="menu-card-label">ویژه:</span><span>${day.special_item} (${fmt(day.special_price)} ریال)</span></div>` : ''}
            </div>
        </div>
    `).join('')}</div>`;
}

// ===== Analysis Attachment =====
async function loadAnalysis() {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const data = await api('/api/analysis_attachment');

    c.innerHTML = `
        <p class="text-muted mb-16" style="font-size:.9rem">این بخش آنالیز پیوست اکسل را نشان می‌دهد. مقادیر ممکن است با شیت ریز غذا تفاوت داشته باشد.</p>
        <div class="food-grid">${data.foods.map(f => `
            <div class="food-card" onclick="showAnalysisDetail(${f.id}, '${f.food_name}', ${JSON.stringify(f.ingredients).replace(/"/g, '&quot;')})">
                <div class="food-card-header">
                    <span class="food-card-name">${f.food_name}</span>
                    <span class="food-card-code">کد ${f.food_code}</span>
                </div>
                <div class="food-card-body">
                    <div class="food-card-row"><span class="label">هزینه خام:</span><span class="value">${fmt(f.raw_cost)}</span></div>
                    <div class="food-card-row"><span class="label">تعداد مواد:</span><span class="value">${f.ingredients.length}</span></div>
                </div>
            </div>
        `).join('')}</div>`;
}

window.showAnalysisDetail = function(id, name, ingredients) {
    let html = `<div class="table-wrapper"><table class="data-table">
        <thead><tr><th>#</th><th>ماده</th><th>مقدار</th><th>واحد</th><th>قیمت</th></tr></thead>
        <tbody>${ingredients.map((ing, i) => `
            <tr><td class="num">${i + 1}</td><td>${ing.ingredient_name}</td><td class="num">${ing.amount}</td><td>${ing.unit}</td><td class="num price">${fmt(ing.unit_price)}</td></tr>
        `).join('')}</tbody></table></div>`;
    showModal(`آنالیز پیوست: ${name}`, html);
};

// ===== Simulator =====
async function loadSimulator() {
    const c = $('#pageContainer');
    c.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    const [ingData, paramData, settingsData] = await Promise.all([
        api('/api/ingredients'), api('/api/overhead_params'), api('/api/settings')
    ]);

    const keyIngs = ingData.ingredients.filter(i => i.price_per_gram > 1000).slice(0, 15);
    const params = paramData.params;
    const settings = settingsData.settings;

    c.innerHTML = `
        <div class="sim-layout">
            <div>
                <div class="card mb-16"><div class="card-header">قیمت فروش شبیه‌سازی</div><div class="card-body">
                    <div class="sim-row"><label>نوع ۱:</label><input type="number" id="simSP1" value="${settings.selling_price_type1 || 2150000}"><span class="rial">ریال</span></div>
                    <div class="sim-row"><label>نوع ۲:</label><input type="number" id="simSP2" value="${settings.selling_price_type2 || 2150000}"><span class="rial">ریال</span></div>
                </div></div>
                <div class="card mb-16"><div class="card-header">تغییر قیمت مواد کلیدی</div><div class="card-body">
                    ${keyIngs.map(i => `
                        <div class="sim-row"><label>${i.name}</label><input type="number" class="sim-ing" data-name="${i.name}" value="${Math.round(i.price_per_gram)}"><span class="rial">ر/گ</span></div>
                    `).join('')}
                </div></div>
                <div class="card mb-16"><div class="card-header">تغییر پارامترهای سرباری</div><div class="card-body">
                    ${params.filter(p => p.param_type === 'fixed' && p.food_type === 0).map(p => `
                        <div class="sim-row"><label>${p.label}</label><input type="number" class="sim-param" data-name="${p.name}" value="${Math.round(p.value)}"><span class="rial">ریال</span></div>
                    `).join('')}
                    ${params.filter(p => p.param_type === 'percent').map(p => `
                        <div class="sim-row"><label>${p.label}</label><input type="number" class="sim-param" data-name="${p.name}" value="${p.value}" step="0.1"><span>%</span></div>
                    `).join('')}
                </div></div>
                <button class="btn btn-primary" id="runSim" style="width:100%;padding:14px;font-size:1rem">اجرای شبیه‌سازی</button>
            </div>
            <div>
                <div class="card"><div class="card-header">نتیجه شبیه‌سازی</div><div class="card-body" id="simResults">
                    <div class="empty"><p>ابتدا شبیه‌سازی را اجرا کنید</p></div>
                </div></div>
            </div>
        </div>`;

    $('#runSim')?.addEventListener('click', runSimulation);
}

async function runSimulation() {
    const ingChanges = {};
    $$('.sim-ing').forEach(inp => { ingChanges[inp.dataset.name] = parseFloat(inp.value) || 0; });
    const paramChanges = {};
    $$('.sim-param').forEach(inp => { paramChanges[inp.dataset.name] = parseFloat(inp.value) || 0; });

    const body = {
        ingredient_changes: ingChanges,
        overhead_changes: paramChanges,
        selling_price_t1: parseFloat($('#simSP1')?.value) || null,
        selling_price_t2: parseFloat($('#simSP2')?.value) || null,
    };

    const data = await api('/api/simulate', { method: 'POST', body });
    const results = $('#simResults');

    const totalProfit = data.foods.filter(f => f.is_profit).reduce((s, f) => s + f.profit_loss, 0);
    const totalLoss = data.foods.filter(f => !f.is_profit).reduce((s, f) => s + Math.abs(f.profit_loss), 0);

    results.innerHTML = `
        <div class="summary-grid mb-16" style="grid-template-columns:1fr 1fr">
            <div class="summary-card profit"><div class="summary-label">مجموع سود</div><div class="summary-value" style="color:var(--success)">${fmt(totalProfit)}</div></div>
            <div class="summary-card loss"><div class="summary-label">مجموع زیان</div><div class="summary-value" style="color:var(--danger)">${fmt(totalLoss)}</div></div>
        </div>
        <div class="table-wrapper"><table class="data-table">
            <thead><tr><th>غذا</th><th>نوع</th><th>خام</th><th>تمام‌شده</th><th>فروش</th><th>سود/زیان</th><th>وضعیت</th></tr></thead>
            <tbody>${data.foods.map(f => `
                <tr>
                    <td>${f.name}</td>
                    <td><span class="badge ${f.food_type === 1 ? 'badge-type1' : 'badge-type2'}">نوع ${f.food_type}</span></td>
                    <td class="num">${fmt(f.raw_cost)}</td>
                    <td class="num">${fmt(f.total_cost)}</td>
                    <td class="num">${fmt(f.selling_price)}</td>
                    <td class="num ${f.is_profit ? 'profit' : 'loss'}">${fmt(f.profit_loss)}</td>
                    <td><span class="badge ${f.is_profit ? 'badge-profit' : 'badge-loss'}">${f.is_profit ? 'سود' : 'زیان'}</span></td>
                </tr>
            `).join('')}</tbody>
        </table></div>`;
    toast('شبیه‌سازی انجام شد');
}

// ===== Init =====
navigateTo('dashboard');
