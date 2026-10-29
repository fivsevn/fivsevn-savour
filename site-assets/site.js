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
  // Restore the exact source pagination and phone, including after a full reload.
  document.querySelectorAll('.post-link,.photo-link').forEach(a => a.addEventListener('click', () => {
    try { sessionStorage.setItem('savour-return', location.pathname + location.search + '#' + a.closest('.phone').id); } catch (_) {}
  }));
  document.querySelectorAll('[data-return]').forEach(a => {
    try {
      const saved = sessionStorage.getItem('savour-return');
      if (saved) {
        const url = new URL(saved, location.origin);
        const prefix = config.base_path || '';
        const path = url.pathname.slice(prefix.length);
        if (url.origin === location.origin && url.pathname.startsWith(prefix + '/') && (path === '/' || /^\/feed\/\d+\/$/.test(path))) a.href = url.pathname + url.search + url.hash;
      }
    } catch (_) {}
  });
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
