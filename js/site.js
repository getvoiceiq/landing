/* VoiceIQ site script. Everything here is optional: with scripts off, the page still reads and works. */
(function () {
  'use strict';
  var d = document, w = window;
  var reduce = !!(w.matchMedia && w.matchMedia('(prefers-reduced-motion: reduce)').matches);

  /* reading progress and header shadow */
  var head = d.querySelector('.site-head'), bar = d.querySelector('.progress'), ticking = false;
  function onScroll() {
    if (ticking) return; ticking = true;
    w.requestAnimationFrame(function () {
      var y = w.pageYOffset || 0, h = d.documentElement.scrollHeight - w.innerHeight;
      if (head) head.classList.toggle('scrolled', y > 8);
      if (bar && h > 0) bar.style.transform = 'scaleX(' + Math.min(1, y / h) + ')';
      if (!d.querySelector('.hero .cta-row')) d.body.classList.toggle('show-sticky', y > 500);
      ticking = false;
    });
  }
  w.addEventListener('scroll', onScroll, { passive: true }); onScroll();

  /* numbers that count up */
  function countUp(root) {
    var nodes = root.querySelectorAll('[data-count]');
    [].forEach.call(nodes, function (n) {
      var to = +n.getAttribute('data-count'), t0 = null;
      if (reduce) { n.textContent = to; return; }
      function step(t) {
        if (!t0) t0 = t;
        var p = Math.min(1, (t - t0) / 900);
        n.textContent = Math.round(to * (1 - Math.pow(1 - p, 3)));
        if (p < 1) w.requestAnimationFrame(step);
      }
      n.textContent = '0'; w.requestAnimationFrame(step);
    });
  }

  /* reveal on scroll */
  var items = [].slice.call(d.querySelectorAll('.reveal'));
  if (reduce || !('IntersectionObserver' in w)) {
    items.forEach(function (e) { e.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.16, rootMargin: '0px 0px -6% 0px' });
    items.forEach(function (e) { io.observe(e); });
  }

  /* hero: the counts tick up once the comments have been sorted; the board can be replayed */
  var hero = d.querySelector('[data-hero-count]'), board = d.querySelector('.board'), rp = d.querySelector('[data-replay]'), heroTimer;
  function runHero() {
    if (!hero) return;
    clearTimeout(heroTimer);
    if (reduce) return;
    [].forEach.call(hero.querySelectorAll('[data-count]'), function (n) { n.textContent = '0'; });
    heroTimer = setTimeout(function () { countUp(hero); }, 3200);
  }
  runHero();
  if (rp && board) rp.addEventListener('click', function () {
    board.classList.add('restart'); void board.offsetWidth; board.classList.remove('restart'); runHero();
  });

  /* sticky call to action: appears once the hero buttons have scrolled away */
  var heroCta = d.querySelector('.hero .cta-row');
  if (heroCta && 'IntersectionObserver' in w) {
    new IntersectionObserver(function (es) {
      var e = es[0]; d.body.classList.toggle('show-sticky', !e.isIntersecting && e.boundingClientRect.top < 0);
    }).observe(heroCta);
  }

  /* "Try it on a comment" */
  var demo = d.querySelector('[data-demo]'), dataEl = d.getElementById('demo-data');
  if (demo && dataEl) {
    var data = []; try { data = JSON.parse(dataEl.textContent); } catch (e) { data = []; }
    var picks = demo.querySelectorAll('.pick'), res = demo.querySelector('.result'), typer;
    var $ = function (id) { return d.getElementById(id); };
    var show = function (i, animate) {
      var it = data[i]; if (!it) return;
      [].forEach.call(picks, function (b, k) { b.setAttribute('aria-pressed', k === i ? 'true' : 'false'); });
      $('r-text').textContent = it.text; $('r-text').setAttribute('lang', it.lang || 'en');
      var tg = $('r-tag'); tg.textContent = it.label; tg.className = 'tag t-' + it.tag;
      $('r-why').textContent = it.why; $('r-next').textContent = it.next;
      var rep = $('r-reply'); rep.setAttribute('lang', it.replyLang || 'en'); clearTimeout(typer);
      if (animate && !reduce) {
        res.classList.remove('go'); void res.offsetWidth; res.classList.add('go');
        rep.textContent = ''; var n = 0;
        (function type() { rep.textContent = it.reply.slice(0, ++n); if (n < it.reply.length) typer = setTimeout(type, 16); })();
      } else { rep.textContent = it.reply; }
    };
    [].forEach.call(picks, function (b, i) { b.addEventListener('click', function () { show(i, true); }); });
    show(0, false);
  }
})();
