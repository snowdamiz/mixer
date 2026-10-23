(() => {
  'use strict';
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const header = document.querySelector('.site-header');
  const menuButton = document.querySelector('.menu-toggle');
  const menu = document.querySelector('.main-nav');
  function closeMenu() {
    if (!menuButton || !menu) return;
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.setAttribute('aria-label', 'Open navigation');
    menu.classList.remove('is-open');
  }
  menuButton?.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') !== 'true';
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    menu?.classList.toggle('is-open', open);
  });
  menu?.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menuButton?.getAttribute('aria-expanded') === 'true') {
      closeMenu();
      menuButton.focus();
    }
  });
  window.addEventListener('resize', () => { if (window.innerWidth > 640) closeMenu(); }, { passive: true });
  const updateHeader = () => header?.classList.toggle('scrolled', window.scrollY > 12);
  window.addEventListener('scroll', updateHeader, { passive: true });
  updateHeader();

  if ('IntersectionObserver' in window && !reducedMotion.matches) {
    document.documentElement.classList.add('js-ready');
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.08, rootMargin: '0px 0px 20px 0px' });
    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
  }

  let toastTimer;
  const toast = document.getElementById('toast');
  function notify(message) {
    if (!toast) return;
    clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.add('visible');
    toastTimer = setTimeout(() => toast.classList.remove('visible'), 2500);
  }
  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', async () => {
      const content = button.dataset.copy || document.getElementById(button.dataset.copyTarget)?.textContent;
      if (!content) return;
      try {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(content.trim());
        notify('Copied. Go make something good.');
        const label = button.querySelector('.copy-label');
        if (label) { label.textContent = 'Copied'; setTimeout(() => { label.textContent = 'Copy'; }, 2200); }
      } catch {
        notify('Select and copy the command below.');
        const code = button.querySelector('code') || document.getElementById(button.dataset.copyTarget);
        if (code) { const selection = window.getSelection(); const range = document.createRange(); range.selectNodeContents(code); selection.removeAllRanges(); selection.addRange(range); }
      }
    });
  });

  const tabs = [...document.querySelectorAll('[data-stage]')];
  const fileNames = { write: 'ProjectFeature.swift', build: 'terminal — native builds', update: 'terminal — release workflow' };
  function selectStage(stage, focus = false) {
    tabs.forEach(tab => {
      const active = tab.dataset.stage === stage;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      document.getElementById(tab.getAttribute('aria-controls')).hidden = !active;
      if (active && focus) tab.focus();
    });
    const fileName = document.getElementById('editor-filename');
    if (fileName) fileName.textContent = fileNames[stage];
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectStage(tab.dataset.stage));
    tab.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      selectStage(tabs[next].dataset.stage, true);
    });
  });

  const ship = document.getElementById('ship-update');
  const reset = document.getElementById('reset-demo');
  const app = document.getElementById('demo-app');
  const status = document.getElementById('preview-status');
  let updateTimers = [];
  function setStatus(message) { if (status) status.replaceChildren(Object.assign(document.createElement('span'), { className: 'status-dot' }), document.createTextNode(message)); }
  function finishUpdate() {
    app.classList.add('updated');
    document.getElementById('preview-heading').replaceChildren(document.createTextNode('Good ideas.'), document.createElement('br'), document.createTextNode('Even better.'));
    document.getElementById('preview-subtitle').textContent = 'A fresh home for whatever comes next.';
    document.getElementById('preview-version').textContent = 'v1.1';
    document.getElementById('new-note').hidden = false;
    setStatus('Example update applied. Same native app.');
    ship.textContent = 'Update applied ✓';
    reset.hidden = false;
    app.removeAttribute('aria-busy');
  }
  ship?.addEventListener('click', () => {
    ship.disabled = true;
    ship.textContent = 'Checking compatibility…';
    app.setAttribute('aria-busy', 'true');
    setStatus('Checking the installed runtime…');
    if (reducedMotion.matches) { finishUpdate(); return; }
    updateTimers.push(setTimeout(() => { ship.textContent = 'Verifying signatures…'; setStatus('Signature and compatibility checks passed.'); }, 650));
    updateTimers.push(setTimeout(() => { ship.textContent = 'Applying the example…'; setStatus('Activating the compatible update…'); }, 1350));
    updateTimers.push(setTimeout(finishUpdate, 2100));
  });
  reset?.addEventListener('click', () => {
    updateTimers.forEach(clearTimeout); updateTimers = [];
    app.classList.remove('updated'); app.removeAttribute('aria-busy');
    document.getElementById('preview-heading').replaceChildren(document.createTextNode('Make something'), document.createElement('br'), document.createTextNode('great.'));
    document.getElementById('preview-subtitle').textContent = 'Your next idea starts here.';
    document.getElementById('preview-version').textContent = 'v1.0';
    document.getElementById('new-note').hidden = true;
    setStatus('One screen. Two native experiences.');
    ship.textContent = 'Try an update →'; ship.disabled = false; reset.hidden = true;
    ship.focus();
  });
})();
