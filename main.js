// ══════════════════════════════════════════
//  SANITIZE — escapes HTML to prevent XSS/injection
//  Always call s() on any string before inserting into innerHTML
// ══════════════════════════════════════════
function s(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}

// ══════════════════════════════════════════
//  THEME
// ══════════════════════════════════════════
function toggleTheme(el) {
  el.classList.toggle('on');
  const dark = el.classList.contains('on');
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  localStorage.setItem('labmind-theme', dark ? 'dark' : 'light');
  // sync all toggles
  document.querySelectorAll('.theme-toggle').forEach(t => {
    if (dark) t.classList.add('on'); else t.classList.remove('on');
  });
}
(function applyTheme() {
  const saved = localStorage.getItem('labmind-theme');
  if (saved === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    window.addEventListener('DOMContentLoaded', () => {
      document.querySelectorAll('.theme-toggle').forEach(t => t.classList.add('on'));
    });
  }
})();

// ══════════════════════════════════════════
//  SECTION / PAGE NAVIGATION
// ══════════════════════════════════════════
const sectionMeta = {
  // Student
  dashboard:    { title: 'Dashboard',         bc: 'Home' },
  labs:         { title: 'My Laboratories',   bc: 'Labs' },
  editor:       { title: 'Code Editor',       bc: 'Editor' },
  writeups:     { title: 'Write-Ups',         bc: 'Assessments' },
  exams:        { title: 'Examinations',      bc: 'Assessments' },
  results:      { title: 'My Results',        bc: 'Progress' },
  profile:      { title: 'My Profile',        bc: 'Account' },
  // Faculty
  'manage-labs':   { title: 'Manage Labs',          bc: 'Labs' },
  'lab-manual':    { title: 'Lab Manual Upload',     bc: 'Laboratory' },
  'create-writeup':{ title: 'Create Write-Up',       bc: 'Assessments' },
  'create-exam':   { title: 'Create Examination',    bc: 'Assessments' },
  'student-perf':  { title: 'Student Performance',   bc: 'Analytics' },
  monitoring:      { title: 'Live Monitoring',        bc: 'Analytics' },
  reports:         { title: 'Assessment Reports',     bc: 'Analytics' },
  notifications:   { title: 'Notifications',          bc: 'System' },
  // Admin
  users:     { title: 'User Management',    bc: 'Management' },
  system:    { title: 'System Settings',    bc: 'Configuration' },
  analytics: { title: 'Platform Analytics', bc: 'Reports' },
};

function showSection(name) {
  // Hide all sections
  document.querySelectorAll('[id^="sec-"]').forEach(s => s.classList.add('hidden'));
  // Show target
  const target = document.getElementById('sec-' + name);
  if (target) { target.classList.remove('hidden'); target.classList.add('animate-in'); setTimeout(() => target.classList.remove('animate-in'), 400); }
  // Update header
  const meta = sectionMeta[name] || { title: name, bc: name };
  const titleEl = document.getElementById('section-title');
  const bcEl    = document.getElementById('section-bc');
  if (titleEl) titleEl.textContent = meta.title;
  if (bcEl)    bcEl.textContent    = meta.bc;
  // Update nav
  document.querySelectorAll('.nav-link').forEach(l => {
    l.classList.remove('active');
    const oc = l.getAttribute('onclick') || '';
    if (oc.includes(`'${name}'`)) l.classList.add('active');
  });
  // Lazy-init charts/data
  setTimeout(() => initSection(name), 80);
}

function initSection(name) {
  switch(name) {
    case 'dashboard':
      buildBarChart('dash-chart', 'dash-chart-labels', [6.8,7.2,7.9,8.1,8.4,7.6,8.7], ['WU1','WU2','WU3','WU4','WU5','WU6','WU7']);
      buildTopPerformers();
      buildScoreSparkline('recent-scores-chart');
      buildProgressRings();
      break;
    case 'student-perf':
      buildBarChart('perf-chart','perf-chart-labels',[7.1,7.8,8.3,8.2,8.6,7.9,9.0],['WU1','WU2','WU3','WU4','WU5','WU6','WU7']);
      buildErrorDist();
      break;
    case 'results':
      buildBarChart('results-chart','results-chart-labels',[9,8,9,null,null,null,null],['WU1','WU2','WU3','WU4','WU5','WU6','WU7']);
      break;
    case 'manage-labs': buildLabCards(); break;
    case 'labs':        buildStudentLabCards(); break;
    case 'monitoring':  buildMonitorCards(); startExamCountdown('exam-countdown', 14*60+20); break;
    case 'editor':      startExamCountdown('editor-timer', 19*60+45); break;
    case 'admin-dash':
    case 'dashboard':
      buildBarChart('admin-chart','admin-chart-labels',[120,98,145,167,134,189,152],['Mon','Tue','Wed','Thu','Fri','Sat','Sun']);
      break;
    case 'analytics':
      buildBarChart('analytics-chart','analytics-chart-labels',[120,98,145,167,134,189,152],['Mon','Tue','Wed','Thu','Fri','Sat','Sun']);
      break;
  }
}

// ══════════════════════════════════════════
//  BAR CHART (CSS)
// ══════════════════════════════════════════
const CHART_COLORS = [
  'linear-gradient(180deg,#3b82f6,#2563eb)',
  'linear-gradient(180deg,#06b6d4,#0891b2)',
  'linear-gradient(180deg,#8b5cf6,#7c3aed)',
  'linear-gradient(180deg,#10b981,#059669)',
  'linear-gradient(180deg,#f59e0b,#d97706)',
];

function buildBarChart(chartId, labelsId, values, labels) {
  const chartEl  = document.getElementById(chartId);
  const labelsEl = document.getElementById(labelsId);
  if (!chartEl || chartEl.children.length > 0) return;

  const max = Math.max(...values.filter(Boolean)) * 1.15;
  values.forEach((v, i) => {
    const bar = document.createElement('div');
    bar.className = 'bar-chart-bar';
    bar.style.cssText = `height:${v ? Math.round((v/max)*100) : 5}%;background:${CHART_COLORS[i % CHART_COLORS.length]};opacity:${v ? 1 : 0.2};transition:height 1s ease ${i*0.08}s`;
    bar.dataset.val = v ? (Number.isInteger(v) ? v : v.toFixed(1)) : '—';
    chartEl.appendChild(bar);
    // Animate
    const target = bar.style.height;
    bar.style.height = '0%';
    requestAnimationFrame(() => requestAnimationFrame(() => { bar.style.height = target; }));
  });

  if (labelsEl) {
    labels.forEach(l => {
      const span = document.createElement('span');
      span.className = 'bar-chart-label';
      span.textContent = l;
      labelsEl.appendChild(span);
    });
  }
}

function buildScoreSparkline(id) {
  const el = document.getElementById(id);
  if (!el || el.innerHTML) return;
  const scores = [8, 9, 7.5, 8, 8.5, 9, 8.7];
  el.style.cssText = 'display:flex;align-items:flex-end;gap:4px;height:50px;margin-bottom:1rem';
  scores.forEach((s, i) => {
    const b = document.createElement('div');
    b.style.cssText = `flex:1;border-radius:3px 3px 0 0;background:var(--brand);opacity:0.8;height:${(s/10)*100}%;transition:height 0.8s ease ${i*0.1}s`;
    el.appendChild(b);
    const h = b.style.height; b.style.height = '0';
    requestAnimationFrame(() => requestAnimationFrame(() => b.style.height = h));
  });
}

// ══════════════════════════════════════════
//  PROGRESS RINGS (Student Dashboard)
// ══════════════════════════════════════════
const ringData = [
  { name: 'C Programming Lab',   done: 8, total: 10, pct: 80, color: 'var(--brand)' },
  { name: 'Data Structures Lab', done: 7, total: 12, pct: 58, color: 'var(--success)' },
  { name: 'ML Lab',              done: 2, total: 8,  pct: 25, color: 'var(--warning)' },
  { name: 'Full Stack Dev Lab',  done: 7, total: 15, pct: 47, color: '#7c3aed' },
];
function buildProgressRings() {
  const cont = document.getElementById('progress-rings-container');
  if (!cont || cont.innerHTML) return;
  ringData.forEach((r, i) => {
    const radius = 38;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (r.pct / 100) * circumference;
    cont.innerHTML += `<div class="progress-ring-item" style="animation-delay:${i*0.1}s">
      <div class="progress-ring">
        <svg width="90" height="90" viewBox="0 0 90 90">
          <circle class="progress-ring-track" cx="45" cy="45" r="${radius}" />
          <circle class="progress-ring-fill" cx="45" cy="45" r="${radius}"
            stroke="${s(r.color)}"
            stroke-dasharray="${circumference}"
            stroke-dashoffset="${circumference}"
            data-offset="${offset}"
          />
        </svg>
        <div class="progress-ring-val">${s(r.pct)}<small>%</small></div>
      </div>
      <div class="progress-ring-info">
        <div class="progress-ring-title">${s(r.name)}</div>
        <div class="progress-ring-meta">${s(r.done)} / ${s(r.total)} tasks</div>
      </div>
    </div>`;
  });
  setTimeout(() => cont.querySelectorAll('.progress-ring-fill').forEach(c => c.style.strokeDashoffset = c.dataset.offset), 100);
}
// ══════════════════════════════════════════
//  TOP PERFORMERS (Faculty Dashboard)
// ══════════════════════════════════════════
const performers = [
  { name: 'Ravi Kumar',   init: 'RK', pct: 93, grad: 'var(--brand),var(--accent)' },
  { name: 'Priya Sharma', init: 'PS', pct: 89, grad: '#7c3aed,#a78bfa' },
  { name: 'Anjali Joshi', init: 'AJ', pct: 85, grad: '#0891b2,#22d3ee' },
  { name: 'Meena R',      init: 'MR', pct: 74, grad: '#16a34a,#4ade80' },
];
function buildTopPerformers() {
  const el = document.getElementById('top-performers-list');
  if (!el || el.innerHTML) return;

  performers.forEach(p => {
    const scoreClass = p.pct >= 85 ? 'text-success' : '';
    const fillClass  = p.pct >= 85 ? 'green' : p.pct >= 70 ? '' : 'yellow';

    // Create elements programmatically to avoid innerHTML injection
    const item = document.createElement('div');
    item.style.marginBottom = '0.875rem';

    const flexBetween = document.createElement('div');
    flexBetween.className = 'flex-between mb-1';

    const flexCenter = document.createElement('div');
    flexCenter.className = 'flex-center gap-2';

    const avatar = document.createElement('div');
    avatar.className = 'header-avatar';
    avatar.style.cssText = `width:28px;height:28px;font-size:0.65rem;background:linear-gradient(135deg,${p.grad})`;
    avatar.textContent = p.init;

    const name = document.createElement('span');
    name.className = 'fw-600 text-sm';
    name.textContent = p.name;

    const score = document.createElement('span');
    score.className = `fw-700 text-sm ${scoreClass}`;
    score.textContent = `${p.pct}%`;

    const progress = document.createElement('div');
    progress.className = 'progress-bar';
    progress.innerHTML = `<div class="progress-fill ${fillClass}" style="width:0%;transition:width 1s ease" data-w="${p.pct}%"></div>`;

    flexCenter.append(avatar, name);
    flexBetween.append(flexCenter, score);
    item.append(flexBetween, progress);
    el.appendChild(item);
  });

  setTimeout(() => el.querySelectorAll('.progress-fill').forEach(b => b.style.width = b.dataset.w), 100);
}

// ══════════════════════════════════════════
//  ERROR DISTRIBUTION (Faculty Analytics)
// ══════════════════════════════════════════
const errorTypes = [
  { name: 'Missing Semicolon',      count: 34, color: 'var(--danger)',  pct: 35 },
  { name: 'Undeclared Variable',    count: 21, color: 'var(--warning)', pct: 22 },
  { name: 'Missing Header (#include)', count: 15, color: 'var(--brand)', pct: 15 },
  { name: 'Type Mismatch',          count: 9,  color: 'var(--info)',    pct: 9  },
  { name: 'Wrong Return Type',      count: 8,  color: '#7c3aed',        pct: 8  },
  { name: 'Infinite Loop (Logic)',  count: 5,  color: '#f97316',        pct: 5  },
];
function buildErrorDist() {
  const el = document.getElementById('error-dist-list');
  if (!el || el.innerHTML) return;
  errorTypes.forEach(e => {
    el.innerHTML += `<div style="display:flex;align-items:center;gap:0.875rem;padding:0.7rem 1rem;border-bottom:1px solid var(--border)">
      <div style="width:10px;height:10px;border-radius:50%;background:${s(e.color)};flex-shrink:0"></div>
      <span style="flex:1;font-size:0.82rem;font-weight:500">${s(e.name)}</span>
      <div style="width:80px"><div class="progress-bar"><div class="progress-fill" style="width:${s(e.pct)}%;background:${s(e.color)}"></div></div></div>
      <span style="font-size:0.78rem;font-weight:700;color:${s(e.color)};min-width:28px;text-align:right">${s(e.count)}</span>
    </div>`;
  });
}

// ══════════════════════════════════════════
//  LAB CARDS (Faculty)
// ══════════════════════════════════════════
const labsData = [
  { icon:'⚙️', name:'C Programming Lab',    sub:'3rd Semester · Section A', students:42, writeups:4, pct:75, color:'#2563eb', status:'Active' },
  { icon:'🌳', name:'Data Structures Lab',  sub:'4th Semester · Section A', students:38, writeups:3, pct:58, color:'#16a34a', status:'Active' },
  { icon:'🤖', name:'Machine Learning Lab', sub:'6th Semester · Section B', students:35, writeups:2, pct:25, color:'#d97706', status:'Upcoming' },
  { icon:'🌐', name:'Full Stack Dev Lab',   sub:'5th Semester · Section C', students:40, writeups:5, pct:47, color:'#7c3aed', status:'Active' },
  { icon:'🗄️', name:'DBMS Lab',            sub:'4th Semester · Section B', students:36, writeups:3, pct:60, color:'#0891b2', status:'Active' },
];
function buildLabCards() {
  const grid = document.getElementById('labs-grid');
  if (!grid || grid.innerHTML) return;
  labsData.forEach(l => {
    const badge = l.status === 'Active'
      ? '<span class="badge badge-success">● Active</span>'
      : '<span class="badge badge-warning">● Upcoming</span>';
    grid.innerHTML += `<div class="lab-card-item">
      <div class="lab-card-top" style="background:${s(l.color)}"></div>
      <div class="lab-card-body">
        <div class="lab-card-icon">${s(l.icon)}</div>
        <div class="lab-card-title">${s(l.name)}</div>
        <div class="lab-card-meta">${s(l.sub)}</div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.875rem">
          ${badge}
          <span class="badge badge-brand">${s(l.writeups)} Write-Ups</span>
        </div>
        <div class="flex-between mb-1">
          <span class="text-xs text-muted">Progress</span>
          <span class="text-xs fw-600">${s(l.pct)}%</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${s(l.pct)}%;background:${s(l.color)}"></div></div>
      </div>
      <div class="lab-card-footer">
        <span class="text-sm text-muted">👥 ${s(l.students)} students</span>
        <button class="btn btn-primary btn-sm" onclick="showToast('Opening lab...','info')">Open Lab →</button>
      </div>
    </div>`;
  });
}

// ══════════════════════════════════════════
//  LAB CARDS (Student)
// ══════════════════════════════════════════
const studentLabsData = [
  { icon:'⚙️', name:'C Programming Lab',   faculty:'Dr. Ramesh Kumar',  sem:'3rd Sem', done:8,  total:10, pct:80, color:'#2563eb', status:'Active' },
  { icon:'🌳', name:'Data Structures Lab', faculty:'Prof. Sujatha',     sem:'4th Sem', done:7,  total:12, pct:58, color:'#16a34a', status:'Active' },
  { icon:'🤖', name:'Machine Learning Lab',faculty:'Dr. Meera',         sem:'6th Sem', done:2,  total:8,  pct:25, color:'#d97706', status:'Upcoming' },
  { icon:'🌐', name:'Full Stack Dev Lab',  faculty:'Prof. Arun',        sem:'5th Sem', done:7,  total:15, pct:47, color:'#7c3aed', status:'Active' },
];
function buildStudentLabCards() {
  const grid = document.getElementById('student-labs-grid');
  if (!grid || grid.innerHTML) return;
  studentLabsData.forEach(l => {
    const badge = l.status === 'Active'
      ? '<span class="badge badge-success">Active</span>'
      : '<span class="badge badge-warning">Upcoming</span>';
    grid.innerHTML += `<div class="lab-card-item" style="cursor:pointer" onclick="showSection('editor')">
      <div class="lab-card-top" style="background:${s(l.color)}"></div>
      <div class="lab-card-body">
        <div class="lab-card-icon">${s(l.icon)}</div>
        <div class="lab-card-title">${s(l.name)}</div>
        <div class="lab-card-meta">${s(l.faculty)} · ${s(l.sem)}</div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.875rem">
          ${badge}
          <span class="badge badge-brand">${s(l.total)} Programs</span>
        </div>
        <div class="flex-between mb-1">
          <span class="text-xs text-muted">${s(l.done)}/${s(l.total)} completed</span>
          <span class="text-xs fw-600">${s(l.pct)}%</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${s(l.pct)}%;background:${s(l.color)}"></div></div>
      </div>
      <div class="lab-card-footer">
        <span class="text-sm text-muted">Practice Mode</span>
        <button class="btn btn-primary btn-sm" onclick="event.stopPropagation();showSection('editor')">Code Now →</button>
      </div>
    </div>`;
  });
}

// ══════════════════════════════════════════
//  MONITORING CARDS
// ══════════════════════════════════════════
const monitorStudents = [
  { name:'Ravi Kumar',    roll:'CS001', init:'RK', status:'green',  label:'Coding',    tabs:0, warns:0,  prog:65 },
  { name:'Priya Sharma',  roll:'CS002', init:'PS', status:'green',  label:'Submitted', tabs:0, warns:0,  prog:100 },
  { name:'Arjun Das',     roll:'CS003', init:'AD', status:'red',    label:'⚠ Flagged', tabs:3, warns:2,  prog:40 },
  { name:'Meena R',       roll:'CS004', init:'MR', status:'yellow', label:'Coding',    tabs:1, warns:1,  prog:55 },
  { name:'Anjali Joshi',  roll:'CS005', init:'AJ', status:'green',  label:'Coding',    tabs:0, warns:0,  prog:72 },
  { name:'Kiran B',       roll:'CS006', init:'KB', status:'green',  label:'Coding',    tabs:0, warns:0,  prog:30 },
  { name:'Suresh M',      roll:'CS007', init:'SM', status:'yellow', label:'Idle',      tabs:0, warns:1,  prog:20 },
  { name:'Deepa R',       roll:'CS008', init:'DR', status:'green',  label:'Submitted', tabs:0, warns:0,  prog:100 },
];
function buildMonitorCards() {
  const grid = document.getElementById('monitor-grid');
  if (!grid || grid.innerHTML) return;
  monitorStudents.forEach(st => {
    const dotClass  = `msd-${s(st.status)}`;
    const cardClass = s(st.status);
    const progColor = st.status === 'red' ? 'var(--danger)' : st.status === 'yellow' ? 'var(--warning)' : 'var(--success)';
    const tabColor  = st.tabs  > 0 ? 'var(--danger)'  : 'var(--text)';
    const warnColor = st.warns > 0 ? 'var(--warning)' : 'var(--text)';
    const warnBtn   = st.tabs > 0
      ? `<button class="btn btn-danger btn-sm" onclick="showToast('Warning sent to ${s(st.name)}','info');this.disabled=true;this.textContent='Sent'">⚠ Warn</button>`
      : '';
    grid.innerHTML += `<div class="monitor-card ${cardClass}">
      <div class="monitor-card-top">
        <div style="display:flex;align-items:center;gap:0.6rem">
          <div class="monitor-avatar">${s(st.init)}</div>
          <div>
            <div class="monitor-name">${s(st.name)}</div>
            <div class="monitor-roll">${s(st.roll)}</div>
          </div>
        </div>
        <div class="monitor-status-dot ${dotClass}"></div>
      </div>
      <div style="font-size:0.78rem;font-weight:600;margin-bottom:0.6rem;color:${progColor}">${s(st.label)}</div>
      <div class="progress-bar" style="margin-bottom:0.75rem"><div class="progress-fill" style="width:${s(st.prog)}%;background:${progColor}"></div></div>
      <div class="monitor-stats">
        <div class="monitor-stat-item">
          <div class="monitor-stat-val" style="color:${tabColor}">${s(st.tabs)}</div>
          <div class="monitor-stat-label">Tab Switches</div>
        </div>
        <div class="monitor-stat-item">
          <div class="monitor-stat-val" style="color:${warnColor}">${s(st.warns)}</div>
          <div class="monitor-stat-label">Warnings</div>
        </div>
      </div>
      ${warnBtn ? `<div style="margin-top:0.75rem">${warnBtn}</div>` : ''}
    </div>`;
  });
}

// ══════════════════════════════════════════
//  TIMERS
// ══════════════════════════════════════════
const runningTimers = {};
function startExamCountdown(id, seconds) {
  if (runningTimers[id]) { clearInterval(runningTimers[id]); }
  const el = document.getElementById(id);
  if (!el) return;
  let rem = seconds;
  const tick = () => {
    if (rem <= 0) { el.textContent = "Time's up!"; clearInterval(runningTimers[id]); return; }
    const m = String(Math.floor(rem/60)).padStart(2,'0');
    const s = String(rem%60).padStart(2,'0');
    el.textContent = `${m}:${s}`;
    if (rem < 120) el.style.color = 'var(--danger)';
    rem--;
  };
  tick();
  runningTimers[id] = setInterval(tick, 1000);
}

// ══════════════════════════════════════════
//  CODE EDITOR
// ══════════════════════════════════════════
const DEFAULT_CODE = `#include <stdio.h>

int main() {
    int n, i, j, temp;
    int a[100];

    printf("Enter number of elements: ");
    scanf("%d", &n);

    printf("Enter elements: ");
    for(i = 0; i < n; i++)
        scanf("%d", &a[i]);

    // Bubble Sort
    for(i = 0; i < n-1; i++) {
        for(j = 0; j < n-i-1; j++) {
            if(a[j] > a[j+1]) {
                temp = a[j];
                a[j] = a[j+1];
                a[j+1] = temp
            }
        }
    }

    printf("Sorted: ");
    for(i = 0; i < n; i++)
        printf("%d ", a[i]);

    return 0;
}`;

const AI_ERRORS = [
  {
    raw: "main.c:20:13: error: expected ';' before '}'",
    title: "Missing Semicolon — Line 20",
    explain: `<strong>What happened:</strong> The statement on line 20 (<code style="background:var(--bg-2);padding:0.1em 0.3em;border-radius:3px">a[j+1] = temp</code>) is missing a semicolon at the end.<br><br>
    <strong>How to fix it:</strong> Add a semicolon after <code style="background:var(--bg-2);padding:0.1em 0.3em;border-radius:3px">temp</code>:<br>
    <code style="color:var(--success);font-family:'JetBrains Mono',monospace">a[j+1] = temp;</code>`,
    tip: "💡 Every C statement must end with a semicolon (;). Think of it like a full stop at the end of a sentence.",
  }
];

async function compileCode() {
  const console_el = document.getElementById('console-body');
  const aiPanel = document.getElementById('ai-panel-body');
  const code = document.getElementById('code-textarea')?.value;
  const programId = document.getElementById('editor-program-id')?.value; // Assume an input holds the current program ID

  if (!console_el) return;
  if (!code) {
    showToast('Code editor is empty.', 'warning');
    return;
  }

  console_el.innerHTML = `<div class="console-output cout-info">⟳ Compiling with GCC...</div>`;
  if (aiPanel) aiPanel.innerHTML = `<div style="text-align:center;padding:1.5rem;color:var(--text-4);font-size:0.85rem">⟳ Analyzing...</div>`;

  try {
    const token = localStorage.getItem('jwt_token'); // Assuming you store the JWT token
    const response = await fetch('/api/compiler/compile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ code: code, language: 'c', program_id: programId })
    });

    if (!response.ok) throw new Error(`Server error: ${response.statusText}`);

    const result = await response.json();

    if (result.compilation_success) {
      console_el.innerHTML = `<div class="console-output cout-success">✅ Compilation successful</div>`;
      if (result.compiler_output) {
        console_el.innerHTML += `<div class="console-output cout-warn" style="margin-top:0.5rem">${s(result.compiler_output)}</div>`;
      } else {
        console_el.innerHTML += `<div class="console-output" style="color:#585b70;margin-top:0.35rem">No errors. No warnings.</div>`;
      }
      if (aiPanel) aiPanel.innerHTML = `<div style="text-align:center;padding:1.5rem"><div style="font-size:2rem;margin-bottom:0.75rem">✅</div><div class="fw-700" style="color:var(--success)">Compilation Successful!</div><div class="text-sm text-muted" style="margin-top:0.35rem">Your code compiled without errors. Click Run to execute.</div></div>`;
      showToast('Code compiled successfully!', 'success');
    } else {
      console_el.innerHTML = `<div class="console-output cout-error">Compilation Failed</div><div class="console-output cout-error" style="margin-top:0.35rem">${s(result.compiler_output)}</div>`;
      if (result.ai_analysis && aiPanel) {
        const ai = result.ai_analysis;
        aiPanel.innerHTML = `
          <div class="error-card"><div class="error-card-title">🚫 ${s(ai.title || 'AI Analysis')}</div><div class="error-code">${s(result.compiler_output)}</div></div>
          <div class="ai-explanation"><div class="ai-explanation-title">🤖 AI Explanation</div><div class="ai-explanation-text">${ai.explanation}</div></div>
          <div class="ai-tip">💡 <div>${ai.tip}</div></div>`;
      }
      showToast('Compilation Failed — AI explanation ready', 'error');
    }
  } catch (error) {
    console.error('Compile error:', error);
    console_el.innerHTML = `<div class="console-output cout-error">Error: ${s(error.message)}</div>`;
    showToast('Could not connect to the compiler service.', 'error');
  }
}

async function runCode() {
  const console_el = document.getElementById('console-body');
  const code = document.getElementById('code-textarea')?.value;
  const stdin = document.getElementById('stdin-input');
  const programId = document.getElementById('editor-program-id')?.value; // Assume an input holds the current program ID

  if (!console_el || !code) return;

  console_el.innerHTML = `<div class="console-output cout-info">⟳ Executing...</div>`;

  try {
    const token = localStorage.getItem('jwt_token');
    const response = await fetch('/api/compiler/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ code: code, language: 'c', stdin: stdin?.value || '', program_id: programId })
    });

    if (!response.ok) throw new Error(`Server error: ${response.statusText}`);

    const result = await response.json();

    if (!result.compilation_success) {
      console_el.innerHTML = `<div class="console-output cout-error">Compilation Failed</div><div class="console-output cout-error" style="margin-top:0.35rem">${s(result.compiler_output)}</div>`;
      showToast('Fix compilation errors before running.', 'error');
      return;
    }

    if (result.status === "Execution Successful") {
      console_el.innerHTML = `<div class="console-output">${s(result.run_output)}</div>
                              <div class="console-output" style="color:#585b70;margin-top:0.5rem">Process exited · Time: ${result.execution_time_ms}ms</div>`;
      showToast('Program executed successfully!', 'success');
    } else { // Handles Runtime Errors
      console_el.innerHTML = `<div class="console-output cout-error">${s(result.status)}</div>`;
      if (result.error) {
        console_el.innerHTML += `<div class="console-output cout-error" style="margin-top:0.35rem">${s(result.error)}</div>`;
      }
      showToast(result.status || 'Execution failed.', 'error');
    }
  } catch (error) {
    console.error('Run error:', error);
    console_el.innerHTML = `<div class="console-output cout-error">Error: ${s(error.message)}</div>`;
    showToast('Could not connect to the execution service.', 'error');
  }
}

function resetCode() {
  const ta = document.getElementById('code-textarea');
  if (ta) ta.value = DEFAULT_CODE;
  clearConsole();
  const aiPanel = document.getElementById('ai-panel-body');
  if (aiPanel) {
    aiPanel.innerHTML = `<div style="text-align:center;padding:2rem 1rem;color:var(--text-4)"><div style="font-size:2rem;margin-bottom:0.75rem">🤖</div><div class="text-sm fw-600" style="color:var(--text-3)">AI Assistant Ready</div><div class="text-xs" style="margin-top:0.35rem">Compile your code to get instant error explanations</div></div>`;
  }
  showToast('Editor reset', 'info');
}

function clearConsole() {
  const el = document.getElementById('console-body');
  if (el) el.innerHTML = '<div class="console-output cout-info">Console cleared.</div>';
}

function submitCode() {
  const console_el = document.getElementById('console-body');
  if (console_el && console_el.innerHTML.includes('Compilation Failed')) {
    showToast('Fix all errors before submitting', 'error'); return;
  }
  showToast('Submitting solution...', 'info');
  setTimeout(() => {
    showToast('✅ Submitted! Auto-evaluation: 9/10 — Excellent!', 'success');
    document.getElementById('exam-lock-bar') && (document.getElementById('exam-lock-bar').style.display = 'none');
  }, 1500);
}

function startWriteUp() {
  const bar = document.getElementById('exam-lock-bar');
  if (bar) bar.style.display = 'flex';
  showSection('editor');
  startExamCountdown('exam-timer-bar', 19*60+45);
  showToast('Write-Up started! Timer is running.', 'warning');
}

// ══════════════════════════════════════════
//  CREATE LAB
// ══════════════════════════════════════════
function createLab() {
  closeModal('modal-create-lab');
  showToast('Laboratory created successfully!', 'success');
  const grid = document.getElementById('labs-grid');
  if (grid) { grid.innerHTML = ''; buildLabCards(); }
}

// ══════════════════════════════════════════
//  UPLOAD SIMULATION
// ══════════════════════════════════════════
function handleFileSelect(input) {
  if (input.files[0]) showToast(`File "${input.files[0].name}" selected`, 'info');
}
function handleDrop(e) {
  e.preventDefault();
  document.getElementById('upload-zone')?.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) showToast(`Dropped: ${f.name}`, 'info');
}
function simulateUpload() {
  showToast('Uploading and extracting programs...', 'info');
  setTimeout(() => showToast('✅ Manual uploaded! 4 programs extracted.', 'success'), 2000);
}

// ══════════════════════════════════════════
//  TABS
// ══════════════════════════════════════════
function switchTab(btn, targetId) {
  const parent = btn.closest('.card') || btn.closest('.page-content') || document;
  parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  parent.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  const target = document.getElementById(targetId);
  if (target) target.classList.add('active');
}

// ══════════════════════════════════════════
//  MODALS
// ══════════════════════════════════════════
function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add('open');
}
function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove('open');
}
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) e.target.classList.remove('open');
});

// ══════════════════════════════════════════
//  TOAST
// ══════════════════════════════════════════
function showToast(msg, type = 'info') {
  let root = document.getElementById('toast-root');
  if (!root) { root = document.createElement('div'); root.id = 'toast-root'; document.body.appendChild(root); }
  const icons = { success:'✅', error:'❌', warning:'⚠️', info:'ℹ️' };
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  // Use textContent for msg and icon to prevent XSS from any caller-supplied strings
  const icon = document.createElement('span'); icon.className = 'toast-icon'; icon.textContent = icons[type] || 'ℹ️';
  const msgEl = document.createElement('span'); msgEl.className = 'toast-msg'; msgEl.textContent = msg;
  const closeEl = document.createElement('span'); closeEl.className = 'toast-close'; closeEl.textContent = '✕';
  closeEl.onclick = () => t.remove();
  t.append(icon, msgEl, closeEl);
  root.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(100%)'; t.style.transition = '0.3s ease'; setTimeout(() => t.remove(), 300); }, 3500);
}

// ══════════════════════════════════════════
//  MOBILE SIDEBAR
// ══════════════════════════════════════════
function toggleMobileSidebar() {
  const sb = document.getElementById('sidebar');
  if (sb) sb.classList.toggle('mobile-open');
}

// ══════════════════════════════════════════
//  INIT ON LOAD
// ══════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  // Init first visible section
  const firstSec = document.querySelector('[id^="sec-"]:not(.hidden)');
  if (firstSec) {
    const name = firstSec.id.replace('sec-', '');
    setTimeout(() => initSection(name), 150);
  }
  // Admin section init
  setTimeout(() => {
    buildBarChart('admin-chart','admin-chart-labels',[120,98,145,167,134,189,152],['Mon','Tue','Wed','Thu','Fri','Sat','Sun']);
  }, 200);
  // Show mobile menu button if needed
  const menuBtn = document.getElementById('mob-menu');
  if (menuBtn && window.innerWidth <= 768) menuBtn.style.display = 'flex';
  window.addEventListener('resize', () => {
    if (menuBtn) menuBtn.style.display = window.innerWidth <= 768 ? 'flex' : 'none';
  });
});
