/* ─────────────────────────────────────
   移动端财务应用 - 核心逻辑
   数据存储：localStorage
   ───────────────────────────────────── */

// ── 数据层 ──
const DB = {
  records: 'fa_records',
  categories: 'fa_categories',
  counters: 'fa_counters',

  get(key) {
    try { return JSON.parse(localStorage.getItem(key) || '[]'); }
    catch { return []; }
  },
  set(key, val) { localStorage.setItem(key, JSON.stringify(val)); },
  nextId() {
    const c = JSON.parse(localStorage.getItem(this.counters) || '{}');
    c.id = (c.id || 0) + 1;
    localStorage.setItem(this.counters, JSON.stringify(c));
    return c.id;
  }
};

// ── 默认分类 ──
const DEFAULT_CATEGORIES = [
  { id: 'c1', name: '餐饮', icon: '🍜', type: 'expense', is_default: true },
  { id: 'c2', name: '交通', icon: '🚇', type: 'expense', is_default: true },
  { id: 'c3', name: '购物', icon: '🛍️', type: 'expense', is_default: true },
  { id: 'c4', name: '住房', icon: '🏠', type: 'expense', is_default: true },
  { id: 'c5', name: '娱乐', icon: '🎮', type: 'expense', is_default: true },
  { id: 'c6', name: '医疗', icon: '💊', type: 'expense', is_default: true },
  { id: 'c7', name: '教育', icon: '📚', type: 'expense', is_default: true },
  { id: 'c8', name: '其他', icon: '💸', type: 'expense', is_default: true },
  { id: 'c9', name: '工资', icon: '💼', type: 'income', is_default: true },
  { id: 'c10', name: '奖金', icon: '🎁', type: 'income', is_default: true },
  { id: 'c11', name: '投资', icon: '📈', type: 'income', is_default: true },
  { id: 'c12', name: '兼职', icon: '✍️', type: 'income', is_default: true },
  { id: 'c13', name: '其他', icon: '💰', type: 'income', is_default: true },
];

const EMOJI_LIST = ['🍜','🍔','🍕','🍣','🚇','🚗','✈️','🛍️','👕','🏠','💡','🎮','🎬','💊','📚','✏️','💼','🎁','📈','💰','💳','📱','🎉','☕','🚲','🛒','💊','🎵','💪','✈️','🐶','🐈'];

// ── 应用状态 ──
const state = {
  currentPage: 'dashboard',
  categories: [],
  records: [],
  editingRecord: null,
  editingCategory: null,
  currentType: 'expense',
  selectedCategoryId: null,
  selectedEmoji: '🍜',
  calYear: new Date().getFullYear(),
  calMonth: new Date().getMonth(),
  chartPeriod: 'month',
  charts: {},
};

// ── 初始化 ──
function init() {
  // 加载分类
  state.categories = DB.get(DB.categories);
  if (state.categories.length === 0) {
    state.categories = DEFAULT_CATEGORIES;
    DB.set(DB.categories, state.categories);
  }
  // 加载记录
  state.records = DB.get(DB.records);

  // 显示今日日期
  const today = new Date();
  const weekDays = ['日', '一', '二', '三', '四', '五', '六'];
  document.getElementById('todayDate').textContent =
    `${today.getFullYear()}年${today.getMonth()+1}月${today.getDate()}日 · 星期${weekDays[today.getDay()]}`;

  // 绑定导航
  document.querySelectorAll('.tab-item').forEach(btn => {
    btn.addEventListener('click', () => switchPage(btn.dataset.page));
  });

  // 绑定 FAB
  document.getElementById('fabAdd').addEventListener('click', () => openRecordModal());

  // 绑定弹窗关闭
  document.getElementById('modalClose').addEventListener('click', closeRecordModal);
  document.getElementById('catModalClose').addEventListener('click', closeCategoryModal);
  document.getElementById('recordModal').addEventListener('click', e => {
    if (e.target.id === 'recordModal') closeRecordModal();
  });
  document.getElementById('categoryModal').addEventListener('click', e => {
    if (e.target.id === 'categoryModal') closeCategoryModal();
  });

  // 绑定类型切换
  document.querySelectorAll('#recordModal .type-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#recordModal .type-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.currentType = btn.dataset.type;
      renderCategoryGrid();
    });
  });

  document.querySelectorAll('#categoryModal .type-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#categoryModal .type-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.currentType = btn.dataset.type;
    });
  });

  // 保存按钮
  document.getElementById('saveBtn').addEventListener('click', saveRecord);
  document.getElementById('deleteBtn').addEventListener('click', deleteRecord);
  document.getElementById('catSaveBtn').addEventListener('click', saveCategory);
  document.getElementById('catDeleteBtn').addEventListener('click', deleteCategory);

  // 渲染 emoji picker
  renderEmojiPicker();

  // 初始渲染
  switchPage('dashboard');
}

// ── 页面切换 ──
function switchPage(page) {
  state.currentPage = page;
  document.querySelectorAll('.tab-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.page === page);
  });
  const main = document.getElementById('mainContent');
  main.scrollTop = 0;
  if (page === 'dashboard') renderDashboard();
  else if (page === 'records') renderRecords();
  else if (page === 'calendar') renderCalendar();
  else if (page === 'categories') renderCategories();
}

// ── 概览页 ──
function renderDashboard() {
  const now = new Date();
  const ym = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;

  const monthRecords = state.records.filter(r => r.date.startsWith(ym));
  const income = monthRecords.filter(r => r.type === 'income').reduce((s, r) => s + r.amount, 0);
  const expense = monthRecords.filter(r => r.type === 'expense').reduce((s, r) => s + r.amount, 0);
  const balance = income - expense;

  let html = `
    <div class="overview-cards">
      <div class="overview-card income">
        <div class="label">本月收入</div>
        <div class="amount">¥${fmtMoney(income)}</div>
      </div>
      <div class="overview-card expense">
        <div class="label">本月支出</div>
        <div class="amount">¥${fmtMoney(expense)}</div>
      </div>
      <div class="overview-card balance">
        <div class="label">结余</div>
        <div class="amount">¥${fmtMoney(balance)}</div>
      </div>
    </div>

    <div class="card chart-card">
      <div class="chart-title">
        <span>📊 收支趋势</span>
        <div class="period-tabs">
          <button class="period-tab ${state.chartPeriod==='week'?'active':''}" onclick="setPeriod('week')">周</button>
          <button class="period-tab ${state.chartPeriod==='month'?'active':''}" onclick="setPeriod('month')">月</button>
          <button class="period-tab ${state.chartPeriod==='year'?'active':''}" onclick="setPeriod('year')">年</button>
        </div>
      </div>
      <div class="chart-wrap"><canvas id="trendChart"></canvas></div>
    </div>

    <div class="card chart-card">
      <div class="chart-title"><span>🍔 支出分类占比</span></div>
      <div class="chart-wrap"><canvas id="pieChart"></canvas></div>
    </div>
  `;

  document.getElementById('mainContent').innerHTML = html;

  // 绘制图表
  setTimeout(() => {
    drawTrendChart();
    drawPieChart();
  }, 50);
}

function setPeriod(p) {
  state.chartPeriod = p;
  renderDashboard();
}

function drawTrendChart() {
  const ctx = document.getElementById('trendChart');
  if (!ctx) return;
  if (state.charts.trend) state.charts.trend.destroy();

  const now = new Date();
  let labels = [], incomeData = [], expenseData = [];

  if (state.chartPeriod === 'week') {
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const ds = formatDate(d);
      labels.push(`${d.getMonth()+1}/${d.getDate()}`);
      incomeData.push(sumByDate(ds, 'income'));
      expenseData.push(sumByDate(ds, 'expense'));
    }
  } else if (state.chartPeriod === 'month') {
    const daysInMonth = new Date(now.getFullYear(), now.getMonth()+1, 0).getDate();
    for (let i = 1; i <= daysInMonth; i++) {
      const ds = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
      labels.push(i);
      incomeData.push(sumByDate(ds, 'income'));
      expenseData.push(sumByDate(ds, 'expense'));
    }
  } else {
    for (let i = 1; i <= 12; i++) {
      const ym = `${now.getFullYear()}-${String(i).padStart(2,'0')}`;
      labels.push(`${i}月`);
      incomeData.push(sumByMonth(ym, 'income'));
      expenseData.push(sumByMonth(ym, 'expense'));
    }
  }

  state.charts.trend = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: '收入',
          data: incomeData,
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34,197,94,0.1)',
          fill: true,
          tension: 0.4,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
        },
        {
          label: '支出',
          data: expenseData,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239,68,68,0.1)',
          fill: true,
          tension: 0.4,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 }, maxTicksLimit: 7 } },
        y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 10 }, callback: v => '¥' + v } }
      }
    }
  });
}

function drawPieChart() {
  const ctx = document.getElementById('pieChart');
  if (!ctx) return;
  if (state.charts.pie) state.charts.pie.destroy();

  const now = new Date();
  const ym = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
  const expenseRecords = state.records.filter(r => r.type === 'expense' && r.date.startsWith(ym));

  const catMap = {};
  expenseRecords.forEach(r => {
    catMap[r.categoryId] = (catMap[r.categoryId] || 0) + r.amount;
  });

  const cats = Object.entries(catMap)
    .map(([cid, amount]) => {
      const cat = state.categories.find(c => c.id === cid);
      return { name: cat ? cat.name : '其他', icon: cat ? cat.icon : '💸', amount };
    })
    .sort((a, b) => b.amount - a.amount);

  if (cats.length === 0) {
    ctx.parentElement.innerHTML = '<div style="text-align:center;padding:40px;color:#94a3b8;font-size:13px;">暂无支出数据</div>';
    return;
  }

  const colors = ['#3b82f6','#22c55e','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316','#6366f1','#10b981'];

  state.charts.pie = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: cats.map(c => `${c.icon} ${c.name}`),
      datasets: [{
        data: cats.map(c => c.amount),
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#fff',
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '60%',
      plugins: {
        legend: { display: true, position: 'right', labels: { font: { size: 11 }, boxWidth: 12, padding: 8 } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const total = ctx.dataset.data.reduce((a,b) => a+b, 0);
              const pct = ((ctx.parsed / total) * 100).toFixed(1);
              return ` ${ctx.label}: ¥${fmtMoney(ctx.parsed)} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

// ── 记录列表页 ──
function renderRecords() {
  const sorted = [...state.records].sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id);

  if (sorted.length === 0) {
    document.getElementById('mainContent').innerHTML = `
      <div class="empty-state">
        <div class="emoji">📋</div>
        <div class="text">还没有记账记录<br>点击下方 + 开始记账</div>
      </div>`;
    return;
  }

  // 按日期分组
  const groups = {};
  sorted.forEach(r => {
    if (!groups[r.date]) groups[r.date] = [];
    groups[r.date].push(r);
  });

  let html = '';
  Object.entries(groups).forEach(([date, records]) => {
    const income = records.filter(r => r.type === 'income').reduce((s,r) => s+r.amount, 0);
    const expense = records.filter(r => r.type === 'expense').reduce((s,r) => s+r.amount, 0);
    const d = new Date(date);
    const weekDays = ['日','一','二','三','四','五','六'];

    html += `<div class="card" style="padding:12px 16px;margin-bottom:10px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="font-size:13px;font-weight:600;">${d.getMonth()+1}月${d.getDate()}日 · 周${weekDays[d.getDay()]}</div>
        <div style="font-size:11px;color:#94a3b8;">
          ${income > 0 ? `<span style="color:#22c55e;">+¥${fmtMoney(income)}</span>` : ''}
          ${income > 0 && expense > 0 ? ' · ' : ''}
          ${expense > 0 ? `<span style="color:#ef4444;">-¥${fmtMoney(expense)}</span>` : ''}
        </div>
      </div>`;

    records.forEach(r => {
      const cat = state.categories.find(c => c.id === r.categoryId);
      const icon = cat ? cat.icon : '💸';
      const name = cat ? cat.name : '其他';
      html += `
        <div class="record-item" style="margin-bottom:6px;box-shadow:none;background:#f8fafc;" onclick="openRecordModal(${r.id})">
          <div class="record-icon" style="background:${r.type==='income'?'#dcfce7':'#dbeafe'}">${icon}</div>
          <div class="record-info">
            <div class="cat-name">${name}</div>
            ${r.note ? `<div class="note">${escapeHtml(r.note)}</div>` : ''}
          </div>
          <div class="record-amount ${r.type}">${r.type==='income'?'+':'-'}¥${fmtMoney(r.amount)}</div>
        </div>`;
    });
    html += `</div>`;
  });

  document.getElementById('mainContent').innerHTML = html;
}

// ── 日历页 ──
function renderCalendar() {
  const y = state.calYear, m = state.calMonth;
  const firstDay = new Date(y, m, 1).getDay();
  const offset = firstDay === 0 ? 6 : firstDay - 1; // 周一为本周第一天
  const daysInMonth = new Date(y, m+1, 0).getDate();
  const today = new Date();
  const isCurrentMonth = today.getFullYear() === y && today.getMonth() === m;

  const ym = `${y}-${String(m+1).padStart(2,'0')}`;
  const monthRecords = state.records.filter(r => r.date.startsWith(ym));

  // 每日收支汇总
  const dayMap = {};
  monthRecords.forEach(r => {
    const day = parseInt(r.date.split('-')[2]);
    if (!dayMap[day]) dayMap[day] = { income: 0, expense: 0 };
    if (r.type === 'income') dayMap[day].income += r.amount;
    else dayMap[day].expense += r.amount;
  });

  let html = `
    <div class="card">
      <div class="calendar-header">
        <button class="cal-nav-btn" onclick="calPrev()">‹</button>
        <div class="month-text">${y}年${m+1}月</div>
        <button class="cal-nav-btn" onclick="calNext()">›</button>
      </div>
      <div class="cal-weekdays">
        <div>一</div><div>二</div><div>三</div><div>四</div><div>五</div><div>六</div><div>日</div>
      </div>
      <div class="cal-grid">
  `;

  for (let i = 0; i < offset; i++) html += `<div class="cal-cell empty"></div>`;

  for (let day = 1; day <= daysInMonth; day++) {
    const ds = `${ym}-${String(day).padStart(2,'0')}`;
    const d = dayMap[day];
    const isToday = isCurrentMonth && day === today.getDate();
    let cls = 'cal-cell';
    if (isToday) cls += ' today';
    else if (d) {
      if (d.income > 0) cls += ' has-income';
      if (d.expense > 0) cls += ' has-expense';
    }
    let amountText = '';
    if (d) {
      if (d.expense > 0) amountText = `-${Math.round(d.expense)}`;
      else if (d.income > 0) amountText = `+${Math.round(d.income)}`;
    }
    html += `<div class="${cls}" onclick="selectCalDay('${ds}')">
      <div>${day}</div>
      ${amountText ? `<div class="cal-amount">${amountText}</div>` : ''}
    </div>`;
  }

  html += `</div></div>`;

  // 当日明细
  const todayStr = formatDate(today);
  html += `<div class="cal-day-detail" id="calDayDetail"></div>`;

  document.getElementById('mainContent').innerHTML = html;

  // 默认显示今日
  selectCalDay(todayStr);
}

function calPrev() {
  state.calMonth--;
  if (state.calMonth < 0) { state.calMonth = 11; state.calYear--; }
  renderCalendar();
}

function calNext() {
  state.calMonth++;
  if (state.calMonth > 11) { state.calMonth = 0; state.calYear++; }
  renderCalendar();
}

function selectCalDay(ds) {
  const records = state.records.filter(r => r.date === ds).sort((a,b) => b.id - a.id);
  const d = new Date(ds);
  const weekDays = ['日','一','二','三','四','五','六'];
  const detail = document.getElementById('calDayDetail');
  if (!detail) return;

  if (records.length === 0) {
    detail.innerHTML = `
      <div class="card" style="text-align:center;padding:30px;color:#94a3b8;">
        <div style="font-size:32px;margin-bottom:8px;">🌙</div>
        <div style="font-size:13px;">${d.getMonth()+1}月${d.getDate()}日 · 周${weekDays[d.getDay()]}<br>暂无记录</div>
      </div>`;
    return;
  }

  const income = records.filter(r => r.type === 'income').reduce((s,r) => s+r.amount, 0);
  const expense = records.filter(r => r.type === 'expense').reduce((s,r) => s+r.amount, 0);

  let html = `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div style="font-size:14px;font-weight:700;">${d.getMonth()+1}月${d.getDate()}日 · 周${weekDays[d.getDay()]}</div>
        <div style="font-size:12px;">
          ${income > 0 ? `<span style="color:#22c55e;">+¥${fmtMoney(income)}</span>` : ''}
          ${income > 0 && expense > 0 ? ' · ' : ''}
          ${expense > 0 ? `<span style="color:#ef4444;">-¥${fmtMoney(expense)}</span>` : ''}
        </div>
      </div>
  `;
  records.forEach(r => {
    const cat = state.categories.find(c => c.id === r.categoryId);
    const icon = cat ? cat.icon : '💸';
    const name = cat ? cat.name : '其他';
    html += `
      <div class="record-item" style="margin-bottom:6px;box-shadow:none;background:#f8fafc;" onclick="openRecordModal(${r.id})">
        <div class="record-icon" style="background:${r.type==='income'?'#dcfce7':'#dbeafe'}">${icon}</div>
        <div class="record-info">
          <div class="cat-name">${name}</div>
          ${r.note ? `<div class="note">${escapeHtml(r.note)}</div>` : ''}
        </div>
        <div class="record-amount ${r.type}">${r.type==='income'?'+':'-'}¥${fmtMoney(r.amount)}</div>
      </div>`;
  });
  html += `</div>`;
  detail.innerHTML = html;
}

// ── 分类管理页 ──
function renderCategories() {
  const expense = state.categories.filter(c => c.type === 'expense');
  const income = state.categories.filter(c => c.type === 'income');

  let html = `
    <div class="stats-summary">
      <div class="stats-card expense">
        <div class="stats-label">支出分类</div>
        <div class="stats-value">${expense.length} 个</div>
      </div>
      <div class="stats-card income">
        <div class="stats-label">收入分类</div>
        <div class="stats-value">${income.length} 个</div>
      </div>
    </div>

    <div style="font-size:13px;font-weight:700;color:#475569;margin:10px 4px 8px;">🍔 支出分类</div>
  `;

  expense.forEach(c => {
    const count = state.records.filter(r => r.categoryId === c.id).length;
    html += `
      <div class="cat-item" onclick="openCategoryModal('${c.id}')">
        <div class="cat-icon">${c.icon}</div>
        <div class="cat-info">
          <div class="name">${escapeHtml(c.name)}</div>
          <div class="meta">${count} 笔记录${c.is_default ? ' · 默认' : ''}</div>
        </div>
        <div class="cat-type-badge expense">支出</div>
      </div>`;
  });

  html += `<div style="font-size:13px;font-weight:700;color:#475569;margin:20px 4px 8px;">💰 收入分类</div>`;

  income.forEach(c => {
    const count = state.records.filter(r => r.categoryId === c.id).length;
    html += `
      <div class="cat-item" onclick="openCategoryModal('${c.id}')">
        <div class="cat-icon" style="background:#dcfce7">${c.icon}</div>
        <div class="cat-info">
          <div class="name">${escapeHtml(c.name)}</div>
          <div class="meta">${count} 笔记录${c.is_default ? ' · 默认' : ''}</div>
        </div>
        <div class="cat-type-badge income">收入</div>
      </div>`;
  });

  html += `<button class="add-cat-btn" onclick="openCategoryModal()">➕ 新增分类</button>`;

  document.getElementById('mainContent').innerHTML = html;
}

// ── 记账弹窗 ──
function openRecordModal(id) {
  state.editingRecord = id || null;

  if (id) {
    const r = state.records.find(x => x.id === id);
    if (!r) return;
    state.currentType = r.type;
    state.selectedCategoryId = r.categoryId;
    document.getElementById('amountInput').value = r.amount;
    document.getElementById('dateInput').value = r.date;
    document.getElementById('noteInput').value = r.note || '';
    document.getElementById('modalTitle').textContent = '编辑记录';
    document.getElementById('deleteBtn').style.display = 'block';
  } else {
    state.currentType = 'expense';
    state.selectedCategoryId = null;
    document.getElementById('amountInput').value = '';
    document.getElementById('dateInput').value = formatDate(new Date());
    document.getElementById('noteInput').value = '';
    document.getElementById('modalTitle').textContent = '新增记账';
    document.getElementById('deleteBtn').style.display = 'none';
  }

  // 类型按钮
  document.querySelectorAll('#recordModal .type-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.type === state.currentType);
  });

  renderCategoryGrid();
  document.getElementById('recordModal').classList.add('show');
  setTimeout(() => document.getElementById('amountInput').focus(), 300);
}

function closeRecordModal() {
  document.getElementById('recordModal').classList.remove('show');
}

function renderCategoryGrid() {
  const cats = state.categories.filter(c => c.type === state.currentType);
  const grid = document.getElementById('categoryGrid');
  grid.innerHTML = cats.map(c => `
    <div class="cat-option ${state.selectedCategoryId === c.id ? 'selected' : ''}" onclick="selectCategory('${c.id}')">
      <div class="icon">${c.icon}</div>
      <div class="name">${escapeHtml(c.name)}</div>
    </div>
  `).join('');
}

function selectCategory(id) {
  state.selectedCategoryId = id;
  renderCategoryGrid();
}

function saveRecord() {
  const amount = parseFloat(document.getElementById('amountInput').value);
  if (!amount || amount <= 0) {
    showToast('请输入金额');
    return;
  }
  if (!state.selectedCategoryId) {
    showToast('请选择分类');
    return;
  }
  const date = document.getElementById('dateInput').value;
  if (!date) {
    showToast('请选择日期');
    return;
  }
  const note = document.getElementById('noteInput').value.trim();

  if (state.editingRecord) {
    const r = state.records.find(x => x.id === state.editingRecord);
    r.amount = amount;
    r.categoryId = state.selectedCategoryId;
    r.date = date;
    r.note = note;
    showToast('已更新');
  } else {
    state.records.push({
      id: DB.nextId(),
      type: state.currentType,
      amount,
      categoryId: state.selectedCategoryId,
      date,
      note,
      createdAt: Date.now(),
    });
    showToast('记账成功 ✅');
  }
  DB.set(DB.records, state.records);
  closeRecordModal();
  switchPage(state.currentPage);
}

function deleteRecord() {
  if (!state.editingRecord) return;
  if (!confirm('确定删除这条记录？')) return;
  state.records = state.records.filter(r => r.id !== state.editingRecord);
  DB.set(DB.records, state.records);
  closeRecordModal();
  switchPage(state.currentPage);
  showToast('已删除');
}

// ── 分类弹窗 ──
function openCategoryModal(id) {
  state.editingCategory = id || null;

  if (id) {
    const c = state.categories.find(x => x.id === id);
    if (!c) return;
    state.currentType = c.type;
    state.selectedEmoji = c.icon;
    document.getElementById('catNameInput').value = c.name;
    document.getElementById('catModalTitle').textContent = '编辑分类';
    document.getElementById('catDeleteBtn').style.display = c.is_default ? 'none' : 'block';
  } else {
    state.currentType = 'expense';
    state.selectedEmoji = '🍜';
    document.getElementById('catNameInput').value = '';
    document.getElementById('catModalTitle').textContent = '新增分类';
    document.getElementById('catDeleteBtn').style.display = 'none';
  }

  document.querySelectorAll('#categoryModal .type-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.type === state.currentType);
  });

  renderEmojiPicker();
  document.getElementById('categoryModal').classList.add('show');
}

function closeCategoryModal() {
  document.getElementById('categoryModal').classList.remove('show');
}

function renderEmojiPicker() {
  const picker = document.getElementById('emojiPicker');
  picker.innerHTML = EMOJI_LIST.map(e => `
    <div class="emoji-option ${state.selectedEmoji === e ? 'selected' : ''}" onclick="selectEmoji('${e}')">${e}</div>
  `).join('');
}

function selectEmoji(e) {
  state.selectedEmoji = e;
  renderEmojiPicker();
}

function saveCategory() {
  const name = document.getElementById('catNameInput').value.trim();
  if (!name) {
    showToast('请输入分类名称');
    return;
  }

  if (state.editingCategory) {
    const c = state.categories.find(x => x.id === state.editingCategory);
    c.name = name;
    c.icon = state.selectedEmoji;
    c.type = state.currentType;
    showToast('已更新');
  } else {
    const id = 'c' + Date.now();
    state.categories.push({
      id,
      name,
      icon: state.selectedEmoji,
      type: state.currentType,
      is_default: false,
    });
    showToast('分类已添加 ✅');
  }
  DB.set(DB.categories, state.categories);
  closeCategoryModal();
  renderCategories();
}

function deleteCategory() {
  if (!state.editingCategory) return;
  const c = state.categories.find(x => x.id === state.editingCategory);
  if (c && c.is_default) {
    showToast('默认分类不可删除');
    return;
  }
  const count = state.records.filter(r => r.categoryId === state.editingCategory).length;
  if (count > 0) {
    showToast(`该分类下有 ${count} 笔记录，无法删除`);
    return;
  }
  if (!confirm('确定删除这个分类？')) return;
  state.categories = state.categories.filter(c => c.id !== state.editingCategory);
  DB.set(DB.categories, state.categories);
  closeCategoryModal();
  renderCategories();
  showToast('已删除');
}

// ── 工具函数 ──
function fmtMoney(n) {
  if (n === 0) return '0';
  return n.toFixed(2).replace(/\.?0+$/, '').replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function formatDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

function sumByDate(ds, type) {
  return state.records.filter(r => r.date === ds && r.type === type).reduce((s, r) => s + r.amount, 0);
}

function sumByMonth(ym, type) {
  return state.records.filter(r => r.date.startsWith(ym) && r.type === type).reduce((s, r) => s + r.amount, 0);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 2000);
}

// ── 启动 ──
init();
