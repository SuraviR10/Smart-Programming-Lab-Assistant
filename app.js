// ── Particles Background ──
(function initParticles() {
  const canvas = document.getElementById('particles-bg');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let particles = [];

  const resize = () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  };
  resize();
  window.addEventListener('resize', resize);

  class Particle {
    constructor() { this.reset(); }
    reset() {
      this.x = Math.random() * canvas.width;
      this.y = Math.random() * canvas.height;
      this.r = Math.random() * 1.5 + 0.3;
      this.vx = (Math.random() - 0.5) * 0.3;
      this.vy = (Math.random() - 0.5) * 0.3;
      this.alpha = Math.random() * 0.5 + 0.1;
      const colors = ['108,99,255', '0,212,170', '255,101,132', '79,195,247'];
      this.color = colors[Math.floor(Math.random() * colors.length)];
    }
    update() {
      this.x += this.vx; this.y += this.vy;
      if (this.x < 0 || this.x > canvas.width || this.y < 0 || this.y > canvas.height) this.reset();
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${this.color},${this.alpha})`;
      ctx.fill();
    }
  }

  for (let i = 0; i < 120; i++) particles.push(new Particle());

  function drawLines() {
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 100) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(108,99,255,${0.06 * (1 - dist / 100)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => { p.update(); p.draw(); });
    drawLines();
    requestAnimationFrame(animate);
  }
  animate();
})();

// ── Navbar scroll effect ──
window.addEventListener('scroll', () => {
  const nav = document.getElementById('navbar');
  if (nav) nav.classList.toggle('scrolled', window.scrollY > 40);
});

// ── Animated Counters (landing page) ──
function animateCounters() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = +el.dataset.count;
    const suffix = target >= 98 ? '%' : target >= 1000 ? '+' : '+';
    let current = 0;
    const step = target / 80;
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = Math.floor(current).toLocaleString() + suffix;
      if (current >= target) clearInterval(timer);
    }, 20);
  });
}

// IntersectionObserver for counter
const heroObs = new IntersectionObserver((entries) => {
  entries.forEach(e => { if (e.isIntersecting) { animateCounters(); heroObs.disconnect(); } });
}, { threshold: 0.5 });
const heroStats = document.querySelector('.hero-stats');
if (heroStats) heroObs.observe(heroStats);

// ── Preview Tab Switcher (landing page) ──
function switchTab(id, btn) {
  document.querySelectorAll('.preview-body').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.preview-tab').forEach(b => b.classList.remove('active'));
  const el = document.getElementById(id);
  if (el) el.classList.add('active');
  if (btn) btn.classList.add('active');
}

// ── Dashboard Page Navigation ──
function showPage(name) {
  document.querySelectorAll('.page-section').forEach(s => s.style.display = 'none');
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const page = document.getElementById('page-' + name);
  if (page) {
    page.style.display = 'block';
    page.style.animation = 'fade-up 0.4s ease';
  }

  // Title map
  const titles = {
    home: 'Dashboard', labs: 'My Labs', editor: 'Code Editor',
    writeups: 'Write-Ups', exams: 'Examinations', analytics: 'Analytics',
    errors: 'Error History', monitor: 'Live Monitor', students: 'Students',
    manual: 'Lab Manual', grades: 'Grades', reports: 'Reports'
  };
  const titleEl = document.getElementById('page-title');
  if (titleEl) titleEl.textContent = titles[name] || name;

  // Mark nav active
  document.querySelectorAll('.nav-item').forEach(n => {
    if (n.getAttribute('onclick') && n.getAttribute('onclick').includes(`'${name}'`)) {
      n.classList.add('active');
    }
  });

  // Render chart if needed
  if (['home', 'analytics', 'reports'].includes(name)) renderChart(name);

  // Scroll to top of content
  const content = document.querySelector('.dash-content');
  if (content) content.scrollTop = 0;
}

// ── Chart Renderer ──
function renderChart(pageId) {
  const chartId = pageId === 'home' ? 'home-chart' :
                  pageId === 'analytics' ? 'analytics-chart' : 'reports-chart';
  const el = document.getElementById(chartId);
  if (!el || el.children.length > 0) return;

  const heights = [40, 65, 55, 80, 70, 90, 75];
  heights.forEach((h, i) => {
    const bar = document.createElement('div');
    bar.className = 'bar';
    bar.style.height = h + '%';
    bar.style.animationDelay = (i * 0.1) + 's';
    el.appendChild(bar);
  });
}

// ── Init charts on dashboard load ──
window.addEventListener('load', () => {
  renderChart('home');

  // Animate progress bars after a short delay
  setTimeout(() => {
    document.querySelectorAll('.progress-fill').forEach(el => {
      const w = el.style.width;
      el.style.width = '0%';
      setTimeout(() => { el.style.width = w; }, 100);
    });
  }, 300);
});

// ── Code Editor: Compile & Run simulation ──
const errorScenarios = [
  {
    trigger: true, // always show error for demo
    output: '',
    errorMsg: "main.c:18:5: error: expected ';' before 'return'",
    aiTitle: '🚫 Missing Semicolon',
    aiMsg: `<strong>What went wrong:</strong> The <code style="color:#c3e88d">printf</code> statement on line 18 is missing a semicolon (<code style="color:#c3e88d">;</code>) at the end.<br><br>
            <strong>How to fix it:</strong> Add a <code style="color:#c3e88d">;</code> after the closing parenthesis on line 18:<br>
            <code style="color:#f78c6c;font-family:'JetBrains Mono',monospace">printf("%d ", a[i]);</code><br><br>
            <em style="color:#6c63ff">💡 Tip: In C, every statement must end with a semicolon.</em>`
  }
];

let runCount = 0;
function runCode() {
  const outputEl = document.getElementById('output-area');
  const aiPanel = document.getElementById('ai-panel');
  const aiContent = document.getElementById('ai-content');
  if (!outputEl) return;

  outputEl.innerHTML = '<span style="color:#4fc3f7">Compiling with GCC...</span>';
  if (aiPanel) aiPanel.style.display = 'none';

  setTimeout(() => {
    runCount++;
    if (runCount % 2 === 1) {
      // Show error
      outputEl.innerHTML = `<div class="output-error">${errorScenarios[0].errorMsg}</div>`;
      if (aiPanel && aiContent) {
        aiContent.innerHTML = `<div style="margin-bottom:0.5rem;font-weight:600;color:var(--danger)">${errorScenarios[0].aiTitle}</div>${errorScenarios[0].aiMsg}`;
        aiPanel.style.display = 'block';
        aiPanel.style.animation = 'fade-in 0.5s ease';
      }
      showToast('Compilation failed — AI analysis ready below', 'error');
    } else {
      // Success
      outputEl.innerHTML = `<div class="output-success">✅ Compilation successful<br><br>Sorted: 12 22 25 34 64 </div>`;
      if (aiPanel) aiPanel.style.display = 'none';
      showToast('Program compiled and executed successfully!', 'success');
    }
  }, 1200);
}

function submitCode() {
  const outputEl = document.getElementById('output-area');
  if (outputEl && !outputEl.innerHTML.includes('Compilation successful')) {
    showToast('Please fix compilation errors before submitting', 'error');
    return;
  }
  showToast('Submission sent! Auto-evaluation in progress...', 'success');
  setTimeout(() => showToast('Auto-graded: 9/10 — Excellent logic structure!', 'success'), 2500);
}

// ── Exam Timer ──
function startTimer(id, seconds) {
  const el = document.getElementById(id);
  if (!el) return;
  let remaining = seconds;
  const tick = setInterval(() => {
    remaining--;
    if (remaining <= 0) { clearInterval(tick); el.textContent = '⏱ Time\'s up!'; el.style.color = 'var(--danger)'; return; }
    const m = Math.floor(remaining / 60).toString().padStart(2, '0');
    const s = (remaining % 60).toString().padStart(2, '0');
    el.textContent = `⏱ ${m}:${s} remaining`;
    if (remaining < 120) el.style.color = 'var(--danger)';
  }, 1000);
}

window.addEventListener('load', () => {
  startTimer('timer', 19 * 60 + 45);
  startTimer('faculty-timer', 14 * 60 + 20);
});

// ── Toast Notifications ──
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const icons = { success: '✅', error: '❌', info: '💡' };
  toast.className = `toast toast-${type === 'error' ? 'error' : type === 'success' ? 'success' : 'info'}`;
  toast.innerHTML = `<span>${icons[type] || '💡'}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'toast-in 0.3s ease reverse';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ── Modal ──
function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add('open');
}
function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove('open');
}
// Close modal on backdrop click
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) e.target.classList.remove('open');
});

// ── Sidebar Mobile Toggle ──
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  if (sb) sb.classList.toggle('open');
}

// ── Scroll Reveal ──
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.style.opacity = '1';
      e.target.style.transform = 'translateY(0)';
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.feature-card, .step-card, .testimonial-card, .lab-card').forEach(el => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(30px)';
  el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
  observer.observe(el);
});

// ── Cursor Glow Effect ──
const cursor = document.createElement('div');
cursor.style.cssText = `
  position: fixed; width: 300px; height: 300px; border-radius: 50%;
  background: radial-gradient(circle, rgba(108,99,255,0.06) 0%, transparent 70%);
  pointer-events: none; z-index: 0; transform: translate(-50%,-50%);
  transition: opacity 0.3s;
`;
document.body.appendChild(cursor);
document.addEventListener('mousemove', e => {
  cursor.style.left = e.clientX + 'px';
  cursor.style.top = e.clientY + 'px';
});

// ── Typing animation for hero ──
(function typeHero() {
  const targets = document.querySelectorAll('.hero-badge');
  targets.forEach(el => {
    const text = el.textContent.trim();
    el.textContent = '';
    let i = 0;
    const type = setInterval(() => {
      el.textContent += text[i];
      i++;
      if (i >= text.length) clearInterval(type);
    }, 40);
  });
})();

// ── Ripple effect on buttons ──
document.addEventListener('click', e => {
  const btn = e.target.closest('.btn');
  if (!btn) return;
  const ripple = document.createElement('span');
  const rect = btn.getBoundingClientRect();
  ripple.style.cssText = `
    position:absolute;border-radius:50%;background:rgba(255,255,255,0.3);
    width:0;height:0;left:${e.clientX - rect.left}px;top:${e.clientY - rect.top}px;
    transform:translate(-50%,-50%);animation:ripple 0.5s ease;pointer-events:none;
  `;
  if (!document.getElementById('ripple-style')) {
    const style = document.createElement('style');
    style.id = 'ripple-style';
    style.textContent = '@keyframes ripple{to{width:150px;height:150px;opacity:0}}';
    document.head.appendChild(style);
  }
  btn.style.position = 'relative';
  btn.appendChild(ripple);
  setTimeout(() => ripple.remove(), 500);
});
