import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const source = await readFile(new URL('../src/app.js', import.meta.url), 'utf8');

function eventTarget() {
  const listeners = new Map();
  return {
    addEventListener(type, callback) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(callback);
    },
    dispatch(type, event = {}) {
      listeners.get(type)?.forEach(callback => callback(event));
    }
  };
}

function classList() {
  const values = new Set();
  return {
    add: value => values.add(value),
    remove: value => values.delete(value),
    contains: value => values.has(value)
  };
}

function motionPage({ reduced = false, fine = true, intersectionObserver = true } = {}) {
  const frames = new Map();
  const properties = new Map();
  const reveals = [{ classList: classList() }, { classList: classList() }];
  const root = { classList: classList() };
  const hero = {
    ...eventTarget(),
    style: { setProperty: (name, value) => properties.set(name, value) },
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 200, height: 200 })
  };
  function preference(matches) {
    return {
      ...eventTarget(),
      matches,
      setMatches(value) {
        if (value === this.matches) return;
        this.matches = value;
        this.dispatch('change', { matches: value });
      }
    };
  }
  const reducedMotion = preference(reduced);
  const finePointer = preference(fine);
  const observers = [];
  let nextFrame = 0;
  const window = {
    ...eventTarget(),
    scrollY: 0,
    matchMedia(query) {
      if (query.includes('prefers-reduced-motion')) return reducedMotion;
      if (query.includes('pointer: fine')) return finePointer;
      throw new Error(`Unimplemented media query: ${query}`);
    },
    requestAnimationFrame(callback) {
      frames.set(++nextFrame, callback);
      return nextFrame;
    },
    cancelAnimationFrame: id => frames.delete(id)
  };
  const document = {
    ...eventTarget(),
    documentElement: root,
    querySelector: selector => selector === '.hero-art' ? hero : null,
    querySelectorAll: selector => selector === '.reveal' ? reveals : [],
    getElementById: () => null
  };
  class IntersectionObserver {
    constructor() {
      this.observed = new Set();
      this.disconnected = false;
      observers.push(this);
    }
    observe(element) { this.observed.add(element); }
    unobserve(element) { this.observed.delete(element); }
    disconnect() {
      this.observed.clear();
      this.disconnected = true;
    }
  }
  if (intersectionObserver) window.IntersectionObserver = IntersectionObserver;
  vm.runInNewContext(source, { window, document, IntersectionObserver });
  return {
    root, hero, frames, properties, reveals, observers, reducedMotion, finePointer,
    move(x, y, pointerType = 'mouse') {
      hero.dispatch('pointermove', { clientX: x, clientY: y, pointerType });
    },
    renderFrame() {
      const pending = [...frames.entries()];
      frames.clear();
      pending.forEach(([, callback]) => callback());
    }
  };
}

test('navigation enhancement is available independently of motion and reveal support', () => {
  for (const options of [{}, { reduced: true }, { intersectionObserver: false }]) {
    assert.ok(motionPage(options).root.classList.contains('js-enhanced'));
  }
});

test('pointer movement coalesces, stays bounded, and leaves no idle animation', () => {
  const page = motionPage();
  assert.equal(page.frames.size, 0);
  page.move(100, 100);
  page.move(220, -20);
  assert.equal(page.frames.size, 1, 'many pointer events need one frame');
  page.renderFrame();
  assert.equal(parseFloat(page.properties.get('--hero-x')), 8);
  assert.equal(parseFloat(page.properties.get('--hero-y')), -6);
  assert.equal(parseFloat(page.properties.get('--spotlight-x')), 100);
  assert.equal(parseFloat(page.properties.get('--spotlight-y')), 0);
  assert.equal(page.frames.size, 0, 'rendering must not schedule an idle loop');
});

test('leaving or cancelling a pointer cancels pending work and restores the hero', () => {
  for (const event of ['pointerleave', 'pointercancel']) {
    const page = motionPage();
    page.move(200, 200);
    page.renderFrame();
    page.move(0, 0);
    page.hero.dispatch(event);
    assert.equal(page.frames.size, 0, `${event} cancels the pending frame`);
    assert.equal(page.properties.get('--hero-x'), '0px');
    assert.equal(page.properties.get('--hero-y'), '0px');
    assert.equal(page.properties.get('--spotlight-x'), '50%');
    assert.equal(page.properties.get('--spotlight-y'), '50%');
  }
});

test('reduced motion, coarse pointers, and touch input never schedule hero movement', () => {
  for (const options of [{ reduced: true }, { fine: false }]) {
    const page = motionPage(options);
    page.move(200, 200);
    assert.equal(page.frames.size, 0);
    assert.equal(page.properties.size, 0);
  }
  const page = motionPage();
  page.move(200, 200, 'touch');
  assert.equal(page.frames.size, 0);
  assert.equal(page.properties.size, 0);
});

test('enabling reduced motion cancels animation and reveals all waiting content', () => {
  const page = motionPage();
  assert.ok(page.root.classList.contains('js-ready'));
  assert.equal(page.observers[0].observed.size, page.reveals.length);
  page.move(200, 200);
  page.reducedMotion.setMatches(true);
  assert.equal(page.frames.size, 0);
  assert.equal(page.properties.get('--hero-x'), '0px');
  assert.ok(page.observers[0].disconnected);
  assert.ok(page.reveals.every(element => element.classList.contains('is-visible')));
  assert.equal(page.root.classList.contains('js-ready'), false);
  assert.ok(page.root.classList.contains('js-enhanced'));
  page.move(200, 200);
  assert.equal(page.frames.size, 0);
  page.reducedMotion.setMatches(false);
  assert.ok(page.reveals.every(element => element.classList.contains('is-visible')));
  page.move(200, 200);
  assert.equal(page.frames.size, 1, 'movement resumes after opting back in');
});

test('losing fine-pointer capability cancels motion until it is available again', () => {
  const page = motionPage();
  page.move(200, 200);
  page.finePointer.setMatches(false);
  assert.equal(page.frames.size, 0);
  assert.equal(page.properties.get('--hero-x'), '0px');
  page.move(200, 200);
  assert.equal(page.frames.size, 0);
  page.finePointer.setMatches(true);
  page.move(200, 200);
  assert.equal(page.frames.size, 1);
});
