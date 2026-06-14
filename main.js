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
    el.innerHTML += `<div style="margin-bottom:0.875rem">
      <div class="flex-between mb-1">
        <div class="flex-center gap-2">
          <div class="header-avatar" style="width:28px;height:28px;font-size:0.65rem;background:linear-gradient(135deg,${p.grad})">${p.init}</div>
          <span class="fw-600 text-sm">${p.name}</span>
        </div>
        <span class="fw-700 text-sm ${p.pct >= 85 ? 'text-success' : ''}">${p.pct}%</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill ${p.pct>=85?'green':p.pct>=70?'':'yellow'}" style="width:0%;transition:width 1s ease" data-w="${p.pct}%"></div>
      </div>
    </div>`;
  });
  // Animate
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
      <div style="width:10px;height:10px;border-radius:50%;background:${e.color};flex-shrink:0"></div>
      <span style="flex:1;font-size:0.82rem;font-weight:500">${e.name}</span>
      <div style="width:80px"><div class="progress-bar"><div class="progress-fill" style="width:${e.pct}%;background:${e.color}"></div></div></div>
      <span style="font-size:0.78rem;font-weight:700;color:${e.color};min-width:28px;text-align:right">${e.count}</span>
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
      <div class="lab-card-top" style="background:${l.color}"></div>
      <div class="lab-card-body">
        <div class="lab-card-icon">${l.icon}</div>
        <div class="lab-card-title">${l.name}</div>
        <div class="lab-card-meta">${l.sub}</div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.875rem">
          ${badge}
          <span class="badge badge-brand">${l.writeups} Write-Ups</span>
        </div>
        <div class="flex-between mb-1">
          <span class="text-xs text-muted">Progress</span>
          <span class="text-xs fw-600">${l.pct}%</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${l.pct}%;background:${l.color}"></div></div>
      </div>
      <div class="lab-card-footer">
        <span class="text-sm text-muted">👥 ${l.students} students</span>
        <button class="btn btn-primary btn-sm" onclick="showToast('Opening ${l.name}...','info')">Open Lab →</button>
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
      <div class="lab-card-top" style="background:${l.color}"></div>
      <div class="lab-card-body">
        <div class="lab-card-icon">${l.icon}</div>
        <div class="lab-card-title">${l.name}</div>
        <div class="lab-card-meta">${l.faculty} · ${l.sem}</div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.875rem">
          ${badge}
          <span class="badge badge-brand">${l.total} Programs</span>
        </div>
        <div class="flex-between mb-1">
          <span class="text-xs text-muted">${l.done}/${l.total} completed</span>
          <span class="text-xs fw-600">${l.pct}%</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${l.pct}%;background:${l.color}"></div></div>
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
  monitorStudents.forEach(s => {
    const dotClass = `msd-${s.status}`;
    const cardClass = s.status;
    const progColor = s.status === 'red' ? 'var(--danger)' : s.status === 'yellow' ? 'var(--warning)' : 'var(--success)';
    const warnBtn = (s.tabs > 0) ? `<button class="btn btn-danger btn-sm" onclick="showToast('Warning sent to ${s.name}','info');this.disabled=true;this.textContent='Sent'">⚠ Warn</button>` : '';
    grid.innerHTML += `<div class="monitor-card ${cardClass}">
      <div class="monitor-card-top">
        <div style="display:flex;align-items:center;gap:0.6rem">
          <div class="monitor-avatar">${s.init}</div>
          <div>
            <div class="monitor-name">${s.name}</div>
            <div class="monitor-roll">${s.roll}</div>
          </div>
        </div>
        <div class="monitor-status-dot ${dotClass}"></div>
      </div>
      <div style="font-size:0.78rem;font-weight:600;margin-bottom:0.6rem;color:${progColor}">${s.label}</div>
      <div class="progress-bar" style="margin-bottom:0.75rem"><div class="progress-fill" style="width:${s.prog}%;background:${progColor}"></div></div>
      <div class="monitor-stats">
        <div class="monitor-stat-item">
          <div class="monitor-stat-val" style="color:${s.tabs>0?'var(--danger)':'var(--text)'}">${s.tabs}</div>
          <div class="monitor-stat-label">Tab Switches</div>
        </div>
        <div class="monitor-stat-item">
          <div class="monitor-stat-val" style="color:${s.warns>0?'var(--warning)':'var(--text)'}">${s.warns}</div>
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

let compileCount = 0;
function compileCode() {
  const console_el = document.getElementById('console-body');
  const aiPanel   = document.getElementById('ai-panel-body');
  if (!console_el) return;
  console_el.innerHTML = `<div class="console-output cout-info">⟳ Compiling with GCC...</div>`;
  if (aiPanel) aiPanel.innerHTML = `<div style="text-align:center;padding:1.5rem;color:var(--text-4);font-size:0.85rem">⟳ Analyzing...</div>`;

  compileCount++;
  setTimeout(() => {
    if (compileCount % 2 === 1) {
      // Error run
      const err = AI_ERRORS[0];
      console_el.innerHTML = `
        <div class="console-output cout-error">Compilation Failed</div>
        <div class="console-output cout-error" style="margin-top:0.35rem">${err.raw}</div>
        <div class="console-output" style="color:#585b70;margin-top:0.5rem">1 error generated.</div>`;
      if (aiPanel) {
        aiPanel.innerHTML = `
          <div class="error-card">
            <div class="error-card-title">🚫 ${err.title}</div>
            <div class="error-code">${err.raw}</div>
          </div>
          <div class="ai-explanation">
            <div class="ai-explanation-title">🤖 AI Explanation</div>
            <div class="ai-explanation-text">${err.explain}</div>
          </div>
          <div class="ai-tip">💡 <div>${err.tip}</div></div>`;
      }
      showToast('Compilation failed — AI explanation ready', 'error');
    } else {
      // Success
      console_el.innerHTML = `
        <div class="console-output cout-success">✅ Compilation successful</div>
        <div class="console-output" style="color:#585b70;margin-top:0.35rem">No errors. No warnings.</div>`;
      if (aiPanel) {
        aiPanel.innerHTML = `
          <div style="text-align:center;padding:1.5rem">
            <div style="font-size:2rem;margin-bottom:0.75rem">✅</div>
            <div class="fw-700" style="color:var(--success)">Compilation Successful!</div>
            <div class="text-sm text-muted" style="margin-top:0.35rem">Your code compiled without errors. Click Run to execute.</div>
          </div>`;
      }
      showToast('Code compiled successfully!', 'success');
    }
  }, 1200);
}

function runCode() {
  const console_el = document.getElementById('console-body');
  if (!console_el) return;
  if (console_el.innerHTML.includes('Compilation Failed')) { showToast('Fix compilation errors first', 'error'); return; }
  const stdin = document.getElementById('stdin-input');
  const input = stdin?.value || '5\n64 34 25 12 22';
  console_el.innerHTML = `<div class="console-output cout-info">⟳ Executing...</div>`;
  setTimeout(() => {
    console_el.innerHTML = `
      <div class="console-output cout-info">Enter number of elements: 5</div>
      <div class="console-output cout-info">Enter elements: 64 34 25 12 22</div>
      <div class="console-output cout-success">Sorted: 12 22 25 34 64</div>
      <div class="console-output" style="color:#585b70;margin-top:0.5rem">Process exited with code 0 · Time: 0.002s · Memory: 1.2 MB</div>`;
    showToast('Program executed successfully!', 'success');
  }, 900);
}

function resetCode() {
  const ta = document.getElementById('code-textarea');
  if (ta) ta.value = DEFAULT_CODE;
  clearConsole();
  const aiPanel = document.getElementById('ai-panel-body');
  if (aiPanel) aiPanel.innerHTML = `<div style="text-align:center;padding:2rem 1rem;color:var(--text-4)"><div style="font-size:2rem;margin-bottom:0.75rem">🤖</div><div class="text-sm fw-600" style="color:var(--text-3)">AI Assistant Ready</div><div class="text-xs" style="margin-top:0.35rem">Compile your code to get instant error explanations</div></div>`;
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
  t.innerHTML = `<span class="toast-icon">${icons[type]||'ℹ️'}</span><span class="toast-msg">${msg}</span><span class="toast-close" onclick="this.parentElement.remove()">✕</span>`;
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
  // Show mobile menu button if needed
  const menuBtn = document.getElementById('mob-menu');
  if (menuBtn && window.innerWidth <= 768) menuBtn.style.display = 'flex';
  window.addEventListener('resize', () => {
    if (menuBtn) menuBtn.style.display = window.innerWidth <= 768 ? 'flex' : 'none';
  });
  // Admin section init
  setTimeout(() => {
    buildBarChart('admin-chart','admin-chart-labels',[120,98,145,167,134,189,152],['Mon','Tue','Wed','Thu','Fri','Sat','Sun']);
  }, 200);
});
