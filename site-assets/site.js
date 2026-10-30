/* Decorative numbers belong to one document load, never to post metadata. */
(() => {
  const config = JSON.parse(document.getElementById('savour-config').textContent);
  const random = config.random;
  const unit = () => { const n = new Uint32Array(1); crypto.getRandomValues(n); return n[0] / 4294967296; };
  const integer = (min, max) => Math.floor(unit() * (max - min + 1)) + min;
  const pad = n => String(n).padStart(2, '0');
  document.querySelectorAll('.phone').forEach(phone => {
    const time = `${pad(integer(0, 23))}:${pad(integer(0, 59))}`;
    const battery = integer(random.battery_min, random.battery_max);
    const progress = (random.progress_min + unit() * (random.progress_max - random.progress_min)).toFixed(3);
    phone.querySelectorAll('[data-random="time"]').forEach(e => e.textContent = time);
    phone.querySelectorAll('[data-random="battery"]').forEach(e => e.textContent = battery);
    phone.querySelectorAll('[data-random="progress"]').forEach(e => e.textContent = progress);
  });
  // Return the source phone to the viewport Y of the detail frame being closed.
  const pendingKey = 'savour-pending-return';
  const sourceKey = path => 'savour-return:' + path;
  const plainClick = event => event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
  function feedURL(value, id) {
    try {
      const url = new URL(value, location.origin);
      const prefix = config.base_path || '';
      const path = url.pathname.slice(prefix.length).replace(/index\.html$/, '');
      if (url.origin !== location.origin || !url.pathname.startsWith(prefix + '/') ||
          !(path === '/' || /^\/feed\/[1-9]\d*\/$/.test(path)) ||
          id && decodeURIComponent(url.hash.slice(1)) !== id) return null;
      return url;
    } catch (_) { return null; }
  }
  document.querySelectorAll('.post-link,.photo-link').forEach(a => a.addEventListener('click', event => {
    if (!plainClick(event)) return;
    const phone = a.closest('.post-phone');
    if (!phone) return;
    try {
      const source = location.pathname + location.search + '#' + phone.id;
      sessionStorage.setItem(sourceKey(new URL(a.href).pathname), source);
      sessionStorage.setItem('savour-return', source);
    } catch (_) { /* The generated return link remains available. */ }
  }));
  const detail = document.querySelector('.detail .post-phone');
  if (detail) {
    document.querySelectorAll('[data-return]').forEach(a => {
      try {
        const saved = sessionStorage.getItem(sourceKey(location.pathname)) || sessionStorage.getItem('savour-return');
        const target = saved && feedURL(saved, detail.id);
        if (target) a.href = target.pathname + target.search + target.hash;
      } catch (_) { /* Direct visits use the generated return page and anchor. */ }
      const remember = () => {
        const target = feedURL(a.href, detail.id);
        if (!target) return;
        try { sessionStorage.setItem(pendingKey, JSON.stringify({
          url: target.pathname + target.search + target.hash,
          id: detail.id, top: detail.getBoundingClientRect().top
        })); } catch (_) { /* The native anchor still reaches the correct post. */ }
      };
      a.addEventListener('click', event => { if (plainClick(event)) remember(); });
      // Browser Back does not click the arrow; capture the same frame on departure.
      addEventListener('pagehide', remember);
    });
  } else {
    let stopAlignment = () => {};
    const restoreFrame = () => {
      let saved;
      try { saved = JSON.parse(sessionStorage.getItem(pendingKey)); } catch (_) { return; }
      const target = saved && feedURL(saved.url, saved.id);
      if (!target || target.pathname !== location.pathname || target.search !== location.search || !Number.isFinite(saved.top)) return;
      const phone = document.getElementById(saved.id);
      if (!phone?.matches('.post-phone')) return;
      stopAlignment();
      try { sessionStorage.removeItem(pendingKey); } catch (_) {}
      let active = true, queued = false, timer;
      const align = () => {
        if (!active) return;
        const delta = phone.getBoundingClientRect().top - saved.top;
        if (Math.abs(delta) <= .5) return;
        const top = Math.max(0, scrollY + delta);
        const shortage = top - Math.max(0, document.documentElement.scrollHeight - innerHeight);
        if (shortage > .5) {
          let space = document.getElementById('savour-return-space');
          if (!space) {
            space = document.createElement('div');
            space.id = 'savour-return-space';
            space.setAttribute('aria-hidden', 'true');
            space.style.cssText = 'height:0;overflow:hidden;pointer-events:none';
            document.body.append(space);
          }
          space.style.height = (parseFloat(space.style.height) || 0) + shortage + 'px';
        }
        scrollTo({ top, behavior: 'instant' });
      };
      const schedule = () => {
        if (!active || queued) return;
        queued = true;
        requestAnimationFrame(() => requestAnimationFrame(() => { queued = false; align(); }));
      };
      const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(schedule) : null;
      const cancelEvents = ['wheel', 'touchstart', 'pointerdown', 'keydown'];
      const stop = () => {
        active = false;
        clearTimeout(timer);
        observer?.disconnect();
        document.removeEventListener('load', schedule, true);
        removeEventListener('resize', schedule);
        cancelEvents.forEach(name => removeEventListener(name, stop));
      };
      stopAlignment = stop;
      cancelEvents.forEach(name => addEventListener(name, stop, { passive: true }));
      document.addEventListener('load', schedule, true);
      addEventListener('resize', schedule);
      observer?.observe(document.body);
      observer?.observe(phone);
      schedule();
      // Reapply after fonts/anchor restoration and image layout settle, then stop.
      Promise.resolve(document.fonts?.ready).then(() => {
        if (!active) return;
        schedule();
        timer = setTimeout(stop, 2000);
      });
    };
    restoreFrame();
    addEventListener('pageshow', restoreFrame);
    addEventListener('pagehide', () => stopAlignment());
  }
  // On a detail page the screen scrolls, while the surrounding frame stays still.
  document.querySelectorAll('.detail .composer-up').forEach(a => a.addEventListener('click', event => {
    event.preventDefault();
    a.closest('.phone').querySelector('.messages').scrollTo({
      top: 0,
      behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
    });
  }));
  // WordPress pagination bookmarks copied onto the new host remain useful.
  const legacyPage = new URLSearchParams(location.search).get('query-18-page');
  if (legacyPage && /^\d+$/.test(legacyPage) && Number(legacyPage) > 1 && Number(legacyPage) <= config.total_pages) {
    location.replace(`${config.base_path}/feed/${Number(legacyPage)}/${location.hash}`);
  }
})();
