/* ============================================================
   itfresh2025 — Portfolio JS
   ============================================================ */

// ── PARTICLE CANVAS BACKGROUND ──────────────────────────────
(function () {
  const canvas = document.getElementById('bg-canvas');
  const ctx    = canvas.getContext('2d');

  let W, H, particles = [];

  const COLORS = ['#58a6ff', '#7ee787', '#d2a8ff', '#ff7b72'];
  const COUNT  = 60;

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function randRange(a, b) { return Math.random() * (b - a) + a; }

  function createParticle() {
    return {
      x: randRange(0, W),
      y: randRange(0, H),
      r: randRange(.5, 2),
      dx: randRange(-.3, .3),
      dy: randRange(-.3, .3),
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      alpha: randRange(.1, .5),
    };
  }

  function init() {
    particles = Array.from({ length: COUNT }, createParticle);
  }

  function drawLine(a, b, dist) {
    const alpha = (1 - dist / 140) * 0.12;
    ctx.strokeStyle = `rgba(88,166,255,${alpha})`;
    ctx.lineWidth = .5;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }

  function animate() {
    ctx.clearRect(0, 0, W, H);

    for (const p of particles) {
      p.x += p.dx;
      p.y += p.dy;
      if (p.x < 0) p.x = W;
      if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H;
      if (p.y > H) p.y = 0;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.color + Math.round(p.alpha * 255).toString(16).padStart(2, '0');
      ctx.fill();
    }

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 140) drawLine(particles[i], particles[j], dist);
      }
    }

    requestAnimationFrame(animate);
  }

  resize();
  init();
  animate();
  window.addEventListener('resize', () => { resize(); init(); });
})();


// ── NAVBAR SCROLL ───────────────────────────────────────────
(function () {
  const nav = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 30);
  });
})();


// ── BURGER MENU ─────────────────────────────────────────────
(function () {
  const burger = document.getElementById('burger');
  const links  = document.querySelector('.nav-links');

  burger.addEventListener('click', () => {
    burger.classList.toggle('open');
    links.classList.toggle('open');
  });

  links.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => {
      burger.classList.remove('open');
      links.classList.remove('open');
    });
  });
})();


// ── TYPING ANIMATION ────────────────────────────────────────
(function () {
  const el     = document.getElementById('typed');
  const words  = [
    'Full Stack Developer',
    'Go & Rust Engineer',
    'Linux Sysadmin',
    'Network Security Fan',
    'Open Source Advocate',
  ];
  let wi = 0, ci = 0, deleting = false;

  function type() {
    const word = words[wi];
    if (!deleting) {
      el.textContent = word.slice(0, ++ci);
      if (ci === word.length) {
        deleting = true;
        setTimeout(type, 1800);
        return;
      }
    } else {
      el.textContent = word.slice(0, --ci);
      if (ci === 0) {
        deleting = false;
        wi = (wi + 1) % words.length;
      }
    }
    setTimeout(type, deleting ? 40 : 80);
  }

  type();
})();


// ── INTERSECTION OBSERVER — fade-in cards ───────────────────
(function () {
  const items = document.querySelectorAll('.skill-card, .project-card');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el    = entry.target;
      const delay = parseInt(el.dataset.delay || 0);
      setTimeout(() => {
        el.classList.add('visible');
        // Animate skill bars inside
        el.querySelectorAll('.bar-fill').forEach(bar => {
          bar.style.width = (bar.dataset.w || 0) + '%';
        });
      }, delay);
      observer.unobserve(el);
    });
  }, { threshold: 0.15 });

  items.forEach(el => observer.observe(el));
})();


// ── SMOOTH ACTIVE NAV LINK ───────────────────────────────────
(function () {
  const sections = document.querySelectorAll('section[id]');
  const links    = document.querySelectorAll('.nav-links a');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      links.forEach(l => l.classList.remove('active'));
      const active = document.querySelector(`.nav-links a[href="#${e.target.id}"]`);
      if (active) active.classList.add('active');
    });
  }, { rootMargin: '-40% 0px -55% 0px' });

  sections.forEach(s => observer.observe(s));
})();
