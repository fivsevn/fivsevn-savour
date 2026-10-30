/* Exercise the shipped navigation script with browser lifecycle and frame geometry. */
import assert from 'node:assert/strict';
import { copyFile, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

export async function runNavigationTests() {
  const globals = new Map(['location', 'sessionStorage', 'document', 'addEventListener', 'removeEventListener',
    'requestAnimationFrame', 'ResizeObserver', 'scrollY', 'innerHeight', 'scrollTo']
    .map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const temporary = await mkdtemp(join(tmpdir(), 'savour-navigation-'));
  const source = new URL('../site-assets/site.js', import.meta.url);
  let number = 0;
  const results = [];
  const events = () => {
    const handlers = new Map();
    return {
      add(name, fn) { if (!handlers.has(name)) handlers.set(name, new Set()); handlers.get(name).add(fn); },
      remove(name, fn) { handlers.get(name)?.delete(fn); },
      emit(name, event = {}) { [...(handlers.get(name) || [])].forEach(fn => fn(event)); }
    };
  };
  async function page({ detail = false, storage = new Map(), base = '', path, height = 3000, ready = true } = {}) {
    const windowEvents = events(), documentEvents = events(), clicks = events(), outgoing = events();
    const state = { docY: 1216, fixedTop: 205, scrolls: [], nodes: new Map(), raf: [] };
    let fontReady;
    const fonts = new Promise(resolve => { fontReady = resolve; });
    if (ready) fontReady();
    const phone = { id: 'sample', matches: value => value === '.post-phone',
      getBoundingClientRect: () => ({ top: detail ? state.fixedTop : state.docY - globalThis.scrollY }) };
    const back = { href: base + '/feed/2/#sample', addEventListener: clicks.add };
    const open = { href: 'https://savour.test' + base + '/page/2026/10/sample/',
      closest: () => phone, addEventListener: outgoing.add };
    const root = { style: {} };
    Object.defineProperty(root, 'scrollHeight', { get: () => height + [...state.nodes.values()].reduce((sum, node) => sum + (parseFloat(node.style.height) || 0), 0) });
    globalThis.location = new URL('https://savour.test' + (path || (detail ? base + '/page/2026/10/sample/' : base + '/feed/2/')));
    globalThis.sessionStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) };
    globalThis.document = {
      documentElement: root, body: { append: node => state.nodes.set(node.id, node) }, fonts: { ready: fonts },
      querySelector: selector => selector === '.detail .post-phone' && detail ? phone : null,
      querySelectorAll: selector => selector === '[data-return]' ? (detail ? [back] : []) : selector === '.post-link,.photo-link' ? (detail ? [] : [open]) : [],
      getElementById: id => id === 'savour-config' ? { textContent: JSON.stringify({ random: {}, base_path: base, total_pages: 12 }) } : id === 'sample' ? phone : state.nodes.get(id),
      createElement: () => ({ style: {}, setAttribute() {} }), addEventListener: documentEvents.add, removeEventListener: documentEvents.remove
    };
    globalThis.addEventListener = windowEvents.add;
    globalThis.removeEventListener = windowEvents.remove;
    globalThis.requestAnimationFrame = callback => state.raf.push(callback);
    globalThis.ResizeObserver = class { observe() {} disconnect() {} };
    globalThis.scrollY = 1000; globalThis.innerHeight = 900;
    globalThis.scrollTo = options => { state.scrolls.push(options); globalThis.scrollY = Math.min(options.top, Math.max(0, root.scrollHeight - innerHeight)); };
    const target = join(temporary, `${number++}.mjs`);
    await copyFile(source, target);
    await import(pathToFileURL(target).href);
    const flush = async () => { await Promise.resolve(); while (state.raf.length) state.raf.splice(0).forEach(callback => callback()); };
    await flush();
    return { state, phone, back, clicks, outgoing, storage, windowEvents, documentEvents, fontReady, flush,
      stop: () => windowEvents.emit('wheel') };
  }
  const click = { button: 0, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false };
  try {
    const storage = new Map([['savour-return', '/feed/9/#unrelated']]);
    let detail = await page({ detail: true, storage });
    detail.clicks.emit('click', click);
    assert.deepEqual(JSON.parse(storage.get('savour-pending-return')), { url: '/feed/2/#sample', id: 'sample', top: 205 });
    results.push('direct detail uses its current outer-frame Y and its own fallback page');
    let feed = await page({ storage, ready: false });
    assert.equal(feed.phone.getBoundingClientRect().top, 205);
    assert.equal(feed.state.scrolls[0].top, 1011);
    assert.equal(feed.state.scrolls[0].behavior, 'instant');
    assert.equal(storage.has('savour-pending-return'), false);
    feed.state.docY += 120; feed.documentEvents.emit('load', { target: { tagName: 'IMG' } }); await feed.flush();
    assert.equal(feed.phone.getBoundingClientRect().top, 205);
    feed.fontReady(); await feed.flush();
    assert.equal(feed.phone.getBoundingClientRect().top, 205);
    feed.stop(); feed.state.docY += 80; feed.documentEvents.emit('load'); await feed.flush();
    assert.equal(feed.phone.getBoundingClientRect().top, 285);
    results.push('list aligns by 11px, survives image/font layout, and yields to user scrolling');
    detail = await page({ detail: true, storage: new Map(), base: '/project' });
    detail.state.fixedTop = 31;
    detail.windowEvents.emit('pagehide');
    feed = await page({ storage: detail.storage, base: '/project' });
    assert.equal(feed.phone.getBoundingClientRect().top, 31); feed.stop();
    feed.storage.set('savour-pending-return', JSON.stringify({ url: '/project/feed/2/#sample', id: 'sample', top: 44 }));
    feed.windowEvents.emit('pageshow', { persisted: true }); await feed.flush();
    assert.equal(feed.phone.getBoundingClientRect().top, 44); feed.stop();
    results.push('native Back and bfcache pageshow use the latest detail frame, including project paths');
    feed = await page({ storage: new Map([['savour-pending-return', JSON.stringify({ url: '/feed/2/#sample', id: 'sample', top: 205 })]]), height: 1100 });
    assert.equal(feed.phone.getBoundingClientRect().top, 205);
    assert.ok(feed.state.nodes.has('savour-return-space')); feed.stop();
    results.push('short final documents gain only the tail space required for exact alignment');
    feed = await page({ storage: new Map([['savour-pending-return', JSON.stringify({ url: 'https://other.test/feed/2/#sample', id: 'sample', top: 205 })]]) });
    assert.equal(feed.state.scrolls.length, 0); feed.stop();
    results.push('foreign return targets never trigger scrolling');
    return results;
  } finally {
    for (const [key, descriptor] of globals) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
    await rm(temporary, { recursive: true, force: true });
  }
}

if (typeof process !== 'undefined' && process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const results = await runNavigationTests();
  console.log(`Passed ${results.length} navigation scenarios.`);
}
