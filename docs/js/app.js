/* ═══════════════════════════════════════════════════════════════
   AGNT Agentic Platform Course — Interactive Features
   Scroll animations · Code highlighting · Progress tracking
   ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ─── Reading Progress Bar ─── */
  const readingProgress = document.querySelector('.reading-progress');
  if (readingProgress) {
    window.addEventListener('scroll', () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      readingProgress.style.width = progress + '%';
    }, { passive: true });
  }

  /* ─── Nav Scroll Effect ─── */
  const nav = document.querySelector('.nav');
  if (nav) {
    let lastScroll = 0;
    window.addEventListener('scroll', () => {
      const currentScroll = window.scrollY;
      if (currentScroll > 50) {
        nav.classList.add('scrolled');
      } else {
        nav.classList.remove('scrolled');
      }
      lastScroll = currentScroll;
    }, { passive: true });
  }

  /* ─── Scroll Animations (Intersection Observer) ─── */
  const animateElements = document.querySelectorAll('.fade-in, .fade-in-left, .fade-in-right, .scale-in');
  if (animateElements.length > 0) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    animateElements.forEach(el => observer.observe(el));
  }

  /* ─── Code Block Copy Buttons ─── */
  document.querySelectorAll('.code-block').forEach(block => {
    const header = block.querySelector('.code-header');
    if (!header) return;

    const copyBtn = header.querySelector('.code-copy');
    if (!copyBtn) return;

    copyBtn.addEventListener('click', async () => {
      const code = block.querySelector('pre')?.textContent || '';
      try {
        await navigator.clipboard.writeText(code);
        copyBtn.classList.add('copied');
        copyBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!';
        setTimeout(() => {
          copyBtn.classList.remove('copied');
          copyBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copy';
        }, 2000);
      } catch (err) {
        console.error('Copy failed:', err);
      }
    });
  });

  /* ─── Collapsible Solutions ─── */
  document.querySelectorAll('.solution-toggle').forEach(toggle => {
    toggle.addEventListener('click', () => {
      const content = toggle.nextElementSibling;
      const isOpen = content.classList.contains('open');

      toggle.classList.toggle('open');
      content.classList.toggle('open');

      // Animate scroll into view if opening
      if (!isOpen) {
        setTimeout(() => {
          content.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 300);
      }
    });
  });

  /* ─── Table of Contents Active State ─── */
  const tocLinks = document.querySelectorAll('.toc-link');
  if (tocLinks.length > 0) {
    const headings = [];
    tocLinks.forEach(link => {
      const id = link.getAttribute('href')?.replace('#', '');
      const heading = document.getElementById(id);
      if (heading) headings.push({ el: heading, link: link });
    });

    const updateToc = () => {
      const scrollPos = window.scrollY + 100;
      let current = headings[0];

      for (const h of headings) {
        if (h.el.offsetTop <= scrollPos) {
          current = h;
        }
      }

      tocLinks.forEach(l => l.classList.remove('active'));
      if (current) current.link.classList.add('active');
    };

    window.addEventListener('scroll', updateToc, { passive: true });
    updateToc();
  }

  /* ─── Animated Number Counters ─── */
  const counters = document.querySelectorAll('[data-count]');
  if (counters.length > 0) {
    const counterObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const target = parseInt(entry.target.getAttribute('data-count'));
          const suffix = entry.target.getAttribute('data-suffix') || '';
          let current = 0;
          const step = Math.max(1, Math.floor(target / 40));
          const interval = setInterval(() => {
            current += step;
            if (current >= target) {
              current = target;
              clearInterval(interval);
            }
            entry.target.textContent = current + suffix;
          }, 30);
          counterObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });

    counters.forEach(c => counterObserver.observe(c));
  }

  /* ─── Keyboard Navigation ─── */
  document.addEventListener('keydown', (e) => {
    // Press '/' to focus search (if exists)
    if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
      const search = document.querySelector('input[type="search"]');
      if (search) {
        e.preventDefault();
        search.focus();
      }
    }

    // Press 'Escape' to close modals/overlays
    if (e.key === 'Escape') {
      document.querySelectorAll('.solution-content.open').forEach(c => {
        c.classList.remove('open');
        c.previousElementSibling?.classList.remove('open');
      });
    }
  });

  /* ─── Smooth Anchor Links ─── */
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const targetId = anchor.getAttribute('href')?.replace('#', '');
      const target = document.getElementById(targetId);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        // Update URL without scroll
        history.pushState(null, '', '#' + targetId);
      }
    });
  });

  /* ─── Module Card Hover Effects ─── */
  document.querySelectorAll('.module-card').forEach(card => {
    card.addEventListener('mouseenter', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty('--mouse-x', x + 'px');
      card.style.setProperty('--mouse-y', y + 'px');
    });

    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty('--mouse-x', x + 'px');
      card.style.setProperty('--mouse-y', y + 'px');
    });
  });

  /* ─── Typing Animation for Hero ─── */
  const typingElements = document.querySelectorAll('.typing-text');
  typingElements.forEach(el => {
    const text = el.textContent;
    el.textContent = '';
    el.style.borderRight = '2px solid var(--accent-blue)';
    let i = 0;
    const type = () => {
      if (i < text.length) {
        el.textContent += text.charAt(i);
        i++;
        setTimeout(type, 50 + Math.random() * 50);
      } else {
        setTimeout(() => {
          el.style.borderRight = 'none';
        }, 1000);
      }
    };
    // Start typing when visible
    const typeObserver = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        type();
        typeObserver.unobserve(el);
      }
    }, { threshold: 0.5 });
    typeObserver.observe(el);
  });

  /* ─── Particle System ─── */
  const particlesContainer = document.querySelector('.particles');
  if (particlesContainer) {
    const colors = ['#38bdf8', '#a78bfa', '#34d399', '#fbbf24'];
    for (let i = 0; i < 30; i++) {
      const particle = document.createElement('div');
      particle.className = 'particle';
      particle.style.left = Math.random() * 100 + '%';
      particle.style.animationDuration = (8 + Math.random() * 12) + 's';
      particle.style.animationDelay = Math.random() * 8 + 's';
      particle.style.width = (1 + Math.random() * 2) + 'px';
      particle.style.height = particle.style.width;
      particle.style.background = colors[Math.floor(Math.random() * colors.length)];
      particlesContainer.appendChild(particle);
    }
  }

  /* ─── Progress Tracking (localStorage) ─── */
  const STORAGE_KEY = 'agnt-course-progress';

  function getProgress() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    } catch {
      return {};
    }
  }

  function setProgress(moduleId, completed) {
    const progress = getProgress();
    progress[moduleId] = completed;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
    updateProgressUI();
  }

  function updateProgressUI() {
    const progress = getProgress();
    const total = document.querySelectorAll('.module-card').length;
    const completed = Object.values(progress).filter(Boolean).length;

    const progressEl = document.querySelector('.course-progress');
    if (progressEl) {
      const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
      progressEl.textContent = completed + '/' + total + ' modules (' + pct + '%)';
    }

    // Mark completed cards
    document.querySelectorAll('.module-card[data-module]').forEach(card => {
      const id = card.getAttribute('data-module');
      if (progress[id]) {
        card.classList.add('completed');
      }
    });
  }

  // Initialize progress on page load
  updateProgressUI();

  /* ─── Expose progress API globally ─── */
  window.AGNTCourse = {
    completeModule: (id) => setProgress(id, true),
    getProgress: getProgress,
    resetProgress: () => {
      localStorage.removeItem(STORAGE_KEY);
      updateProgressUI();
    }
  };

  /* ─── Page Load Animation ─── */
  document.body.classList.add('loaded');

})();
