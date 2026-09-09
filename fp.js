/* FRONT PAGE v1, page script. 9 Sep 2026. Reads and writes the Apps Script endpoint; renders the board.
   Configure ENDPOINT below (the web app /exec URL). The code (PIN) is entered once per device and kept in localStorage. */
(function () {
  'use strict';
  var ENDPOINT = 'https://script.google.com/macros/s/AKfycbwm0IY5gQJ-xJHAQD8MMQHWecmqeepPogAE8i-wuqMugLj-jVsuXTOZ8SsBYJbx2ILqnA/exec';
  var POLL_MS = 5 * 60 * 1000;
  var BY = 'page';

  var $ = function (id) { return document.getElementById(id); };
  var data = null, pin = null, openMenu = null, timer = null, busy = false;

  /* ---------------- boot */
  try { pin = localStorage.getItem('fp-pin'); } catch (e) {}
  $('hdrdate').textContent = new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
  if (!pin) showGate(''); else { $('app').hidden = false; load(); }

  $('pinbtn').addEventListener('click', function () {
    var v = $('pin').value.trim(); if (!v) return;
    pin = v; try { localStorage.setItem('fp-pin', v); } catch (e) {}
    $('gate').hidden = true; $('app').hidden = false; load();
  });
  $('pin').addEventListener('keydown', function (e) { if (e.key === 'Enter') $('pinbtn').click(); });
  $('forget').addEventListener('click', function () { try { localStorage.removeItem('fp-pin'); } catch (e) {} location.reload(); });
  $('refresh').addEventListener('click', function () { load(); });
  $('towaiting').addEventListener('click', function () { showTab('waiting'); });
  $('tabs').addEventListener('click', function (e) { var a = e.target.closest('a[data-tab]'); if (a) showTab(a.getAttribute('data-tab')); });
  $('addform').addEventListener('submit', function (e) {
    e.preventDefault(); var t = $('addtext').value.trim(); if (!t) return;
    post({ action: 'add', text: t }).then(function () { $('addtext').value = ''; });
  });
  document.addEventListener('visibilitychange', function () { if (!document.hidden) load(); });
  window.addEventListener('focus', function () { load(true); });

  function showGate(msg) { $('gate').hidden = false; $('app').hidden = true; $('gatemsg').textContent = msg || ''; }
  function showTab(name) {
    ['today', 'waiting', 'arcs', 'system'].forEach(function (t) { $('tab-' + t).hidden = t !== name; });
    Array.prototype.forEach.call($('tabs').querySelectorAll('a'), function (a) { a.classList.toggle('on', a.getAttribute('data-tab') === name); });
    window.scrollTo(0, 0);
  }

  /* ---------------- network */
  function load(quiet) {
    if (!pin) return;
    if (!quiet) status('loading…');
    clearTimeout(timer); timer = setTimeout(function () { load(true); }, POLL_MS);
    return fetch(ENDPOINT + '?pin=' + encodeURIComponent(pin) + '&t=' + Date.now(), { cache: 'no-store' })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.ok) { if (/pin/i.test(j.error || '')) { try { localStorage.removeItem('fp-pin'); } catch (e) {} pin = null; showGate('That code was not accepted: ' + j.error); } else status(j.error, true); return; }
        data = j; render(); status('');
      })
      .catch(function (err) { status('could not reach the endpoint: ' + err.message, true); });
  }
  function post(body) {
    if (busy) return Promise.resolve();
    busy = true; body.pin = pin; body.by = BY;
    status('saving…');
    return fetch(ENDPOINT, { method: 'POST', body: JSON.stringify(body), headers: { 'Content-Type': 'text/plain;charset=utf-8' } })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        busy = false;
        if (!j.ok) { status(j.error, true); return j; }
        if (j.payload) { data = j.payload; render(); }
        status((j.title ? j.title + ': ' : '') + (j.detail || 'done') + (j.warning ? ' (' + j.warning + ')' : ''));
        return j;
      })
      .catch(function (err) { busy = false; status('save failed: ' + err.message, true); });
  }
  function status(msg, isErr) { var s = $('status'); s.textContent = msg || ''; s.className = isErr ? 'err' : ''; }

  /* ---------------- render */
  function render() {
    var d = data, S = d.sections;
    renderHealth(d);
    if (d.brief && d.brief.text) { $('brief').textContent = d.brief.text; $('brief').hidden = false; } else $('brief').hidden = true;
    $('custody').textContent = d.custody || 'No custody block covers today (check Family Gunderwolfe).';
    fill('todaylist', d.today_events, function (ev) {
      var li = el('li', 'item');
      li.appendChild(txt((ev.allDay ? 'all day' : ev.time + (ev.end ? ' to ' + ev.end : '')) + '  '));
      li.appendChild(bold(ev.title));
      li.appendChild(tag(ev.cal === 'family' ? 'family' : 'Nathan', 'grey'));
      return li;
    }, 'Nothing timed today.');
    fill('habits', S.habits, function (it) { return row(it, ['done']); }, null);
    fill('recurring', S.recurring, function (it) { return row(it, ['done', 'snooze', 'set']); }, S.habits.length ? null : 'Nothing recurring today.');
    fill('nowlist', S.now, function (it) { var li = row(it, ['done', 'set', 'snooze', 'wait']); li.draggable = true; li.setAttribute('data-id', it.id); return li; }, 'Nothing in Now. Add something above or sit at the Desk.');
    fill('waitflag', S.waiting_flagged, function (it) { return row(it, ['done', 'ask', 'snooze']); }, 'Nothing waiting needs you.');
    fill('arcs', S.arcs, function (it) { return row(it, []); }, 'No longer arcs.');
    fill('arcsall', S.arcs, function (it) { return row(it, ['note']); }, 'No longer arcs.');
    fill('waitall', d.waiting, function (it) { return row(it, ['done', 'ask', 'snooze']); }, 'Nothing waiting.');
    fill('sethidden', d.set_hidden, function (it) { return row(it, ['reset', 'done']); }, 'Nothing set for later.');
    fill('snoozed', d.snoozed, function (it) { return row(it, ['reset', 'done']); }, 'Nothing snoozed.');
    fill('donelist', d.done_recent, function (it) { return row(it, ['restore']); }, 'Nothing done in the last 14 days.');
    fill('log', d.log, function (l) { var li = el('li'); li.textContent = l.t + '  ' + l.action + (l.title ? '  ' + l.title : '') + (l.detail ? '  (' + l.detail + ')' : '') + (l.by ? '  by ' + l.by : ''); return li; }, 'No actions yet.');
    $('gen').textContent = 'Fetched ' + d.generated.slice(11) + '.';
    wireDrag();
  }

  function renderHealth(d) {
    var h = d.health, stale = parseInt(h.stale_count || '0', 10);
    var html = 'Swept <b>' + esc(h.last_sweep) + '</b>.';
    if (h.portals) html += ' Portals: ' + esc(h.portals) + '.';
    html += ' ' + esc(h.watches) + ' watch' + (h.watches === '1' ? '' : 'es') + ', <span class="' + (stale ? 'bad' : '') + '">' + stale + ' stale</span>.';
    html += ' Endpoint ' + esc(h.endpoint_time) + '.';
    if (d.features && !d.features.advanced_calendar) html += ' <span class="bad">Advanced Calendar off (Set blocks will be busy, not free).</span>';
    $('health').innerHTML = html;
  }

  function fill(id, list, fn, emptyText) {
    var ul = $(id); ul.innerHTML = '';
    if (!list || !list.length) { if (emptyText) { var e = el('li', 'empty'); e.textContent = emptyText; ul.appendChild(e); } return; }
    list.forEach(function (x) { ul.appendChild(fn(x)); });
  }

  function row(it, buttons) {
    var li = el('li', 'item' + (it.stale ? ' stale' : '') + (it.overdue ? ' overdue' : '') + (it.returned ? ' returned' : ''));
    if (buttons.length) {
      var b = el('span', 'btns');
      buttons.forEach(function (name) { var a = el('a'); a.textContent = name; a.addEventListener('click', function (e) { e.preventDefault(); onButton(name, it, li); }); b.appendChild(a); });
      li.appendChild(b);
    }
    li.appendChild(bold(it.title));
    var when = whenText(it); if (when) li.appendChild(txt(' ')), li.appendChild(spanD(when));
    if (it.stale) li.appendChild(tag('stale', 'red'));
    if (it.overdue) li.appendChild(tag('overdue', 'red'));
    if (it.returned) li.appendChild(tag(it.f.status === 'set' ? 'back from its slot' : 'back from snooze', 'grey'));
    if (it.f.needs_attention === 'yes' && it.kind === 'waiting') li.appendChild(tag('needs you'));
    if (it.f.ask) li.appendChild(tag('nudge asked', 'grey'));
    if (it.f.owner && it.f.owner !== 'nathan' && it.f.owner !== 'none') li.appendChild(tag(it.f.owner, 'grey'));
    if (it.notes) { var n = el('span', 'note'); n.textContent = it.notes; li.appendChild(n); }
    var prov = [];
    if (it.kind === 'waiting' && it.f.waiting_on) prov.push('waiting on ' + it.f.waiting_on);
    if (it.kind === 'waiting' && it.f.expected_by) prov.push('expected by ' + fmtDate(it.f.expected_by));
    if (it.f.kind === 'recurring-after-completion') prov.push('completion-anchored, every ' + (it.f.interval || '30d'));
    if (it.f.source) prov.push(it.f.source);
    if (it.f.provenance) prov.push(it.f.provenance);
    if (it.f.done_at) prov.push('done ' + it.f.done_at.replace('T', ' ') + (it.f.done_by ? ' by ' + it.f.done_by : ''));
    if (it.f.link) { var l = el('a'); l.href = it.f.link; l.textContent = 'link'; l.target = '_blank'; l.rel = 'noopener'; l.style.color = 'var(--accent)'; li.appendChild(txt(' ')); li.appendChild(l); }
    if (prov.length) { var p = el('span', 'prov'); p.textContent = prov.join(' · '); li.appendChild(p); }
    return li;
  }

  function whenText(it) {
    if (it.f.status === 'snoozed' && it.f.snooze_until && it.f.snooze_until > data.today) return '- snoozed until ' + fmtDate(it.f.snooze_until);
    if (it.f.status === 'set' && it.f.set_start) return '- set ' + fmtDateTime(it.f.set_start);
    if (it.kind === 'waiting' || it.kind === 'arc') return '';
    if (it.undated) return '';
    if (it.recurring && it.f.kind === 'habit') return '- daily';
    return '- ' + fmtDate(it.date) + (it.time ? ' ' + it.time : '');
  }

  /* ---------------- buttons */
  function onButton(name, it, li) {
    closeMenu();
    var base = { id: it.id, cal: it.cal, start: it.start };
    if (name === 'done') return post(merge(base, { action: 'done' }));
    if (name === 'reset') return post(merge(base, { action: 'reset' }));
    if (name === 'restore') return post(merge(base, { action: 'restore' }));
    if (name === 'ask') return post(merge(base, { action: 'ask' }));
    if (name === 'snooze') return menuSnooze(it, li, base);
    if (name === 'set') return menuSet(it, li, base);
    if (name === 'wait') return menuWait(it, li, base);
    if (name === 'note') return menuNote(it, li, base);
  }
  function menu(li) { closeMenu(); var m = el('div', 'menu'); li.appendChild(m); openMenu = m; return m; }
  function closeMenu() { if (openMenu && openMenu.parentNode) openMenu.parentNode.removeChild(openMenu); openMenu = null; }

  function menuSnooze(it, li, base) {
    var m = menu(li), isWait = it.kind === 'waiting';
    m.appendChild(txt(isWait ? 'New expected-by date: ' : 'Snooze until: '));
    [['1 day', 1], ['1 week', 7], ['1 month', 30]].forEach(function (o) {
      var a = el('a'); a.textContent = o[0]; a.addEventListener('click', function () { post(merge(base, { action: 'snooze', until: addDays(data.today, o[1]) })); }); m.appendChild(a);
    });
    var inp = el('input'); inp.type = 'date'; inp.min = data.today; m.appendChild(inp);
    var go = el('button'); go.textContent = 'ok'; go.addEventListener('click', function () { if (inp.value) post(merge(base, { action: 'snooze', until: inp.value })); }); m.appendChild(go);
    var c = el('a'); c.textContent = 'cancel'; c.addEventListener('click', closeMenu); m.appendChild(c);
  }
  function menuSet(it, li, base) {
    var m = menu(li);
    m.appendChild(txt('Set a free block on your calendar. '));
    var d = el('input'); d.type = 'date'; d.value = data.today; d.min = data.today; m.appendChild(d);
    var t = el('input'); t.type = 'time'; t.value = it.time || '11:00'; m.appendChild(t);
    var dur = el('select'); [15, 30, 45, 60, 90, 120].forEach(function (n) { var o = el('option'); o.value = n; o.textContent = n + ' min'; if (n === 60) o.selected = true; dur.appendChild(o); }); m.appendChild(dur);
    var ta = el('textarea'); ta.value = it.notes || ''; ta.placeholder = 'Notes travel with the item into the calendar block'; m.appendChild(ta);
    var go = el('button'); go.textContent = 'set'; go.addEventListener('click', function () {
      if (!d.value || !t.value) return;
      post(merge(base, { action: 'set', start: d.value + 'T' + t.value, minutes: dur.value, notes: ta.value }));
    }); m.appendChild(go);
    var c = el('a'); c.textContent = 'cancel'; c.addEventListener('click', closeMenu); m.appendChild(c);
  }
  function menuWait(it, li, base) {
    var m = menu(li);
    m.appendChild(txt('Move to Waiting. Waiting on: '));
    var who = el('input'); who.placeholder = 'who or what'; m.appendChild(who);
    m.appendChild(txt(' expected by '));
    var d = el('input'); d.type = 'date'; d.value = addDays(data.today, 14); d.min = data.today; m.appendChild(d);
    var na = el('label'); var cb = el('input'); cb.type = 'checkbox'; na.appendChild(cb); na.appendChild(txt(' keep on the front page')); na.style.fontSize = '10.5px'; m.appendChild(na);
    var go = el('button'); go.textContent = 'move'; go.addEventListener('click', function () {
      post(merge(base, { action: 'wait', waiting_on: who.value, expected_by: d.value, needs_attention: cb.checked ? 'yes' : 'no' }));
    }); m.appendChild(go);
    var c = el('a'); c.textContent = 'cancel'; c.addEventListener('click', closeMenu); m.appendChild(c);
  }
  function menuNote(it, li, base) {
    var m = menu(li);
    var ta = el('textarea'); ta.placeholder = 'Add a line to this arc'; m.appendChild(ta);
    var go = el('button'); go.textContent = 'add'; go.addEventListener('click', function () { if (ta.value.trim()) post(merge(base, { action: 'note', text: ta.value.trim() })); }); m.appendChild(go);
    var c = el('a'); c.textContent = 'cancel'; c.addEventListener('click', closeMenu); m.appendChild(c);
  }

  /* ---------------- drag to reorder Now */
  function wireDrag() {
    var ol = $('nowlist'), dragging = null;
    Array.prototype.forEach.call(ol.querySelectorAll('li.item'), function (li) {
      li.addEventListener('dragstart', function (e) { dragging = li; li.classList.add('dragging'); e.dataTransfer.effectAllowed = 'move'; try { e.dataTransfer.setData('text/plain', li.getAttribute('data-id')); } catch (x) {} });
      li.addEventListener('dragend', function () { if (!dragging) return; li.classList.remove('dragging'); dragging = null; var ids = Array.prototype.map.call(ol.querySelectorAll('li.item'), function (x) { return x.getAttribute('data-id'); }); post({ action: 'reorder', ids: ids, cal: 'board' }); });
      li.addEventListener('dragover', function (e) { e.preventDefault(); if (!dragging || dragging === li) return; var r = li.getBoundingClientRect(); if (e.clientY < r.top + r.height / 2) ol.insertBefore(dragging, li); else ol.insertBefore(dragging, li.nextSibling); });
    });
  }

  /* ---------------- small helpers */
  function el(t, cls) { var e = document.createElement(t); if (cls) e.className = cls; return e; }
  function txt(s) { return document.createTextNode(s); }
  function bold(s) { var b = el('b'); b.textContent = s; return b; }
  function spanD(s) { var x = el('span', 'd'); x.textContent = s; return x; }
  function tag(s, cls) { var x = el('span', 'tag' + (cls ? ' ' + cls : '')); x.textContent = s; return x; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function merge(a, b) { var o = {}; for (var k in a) o[k] = a[k]; for (var j in b) o[j] = b[j]; return o; }
  function addDays(ymd, n) { var p = ymd.split('-'), d = new Date(+p[0], +p[1] - 1, +p[2] + n); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function fmtDate(ymd) { if (!ymd) return ''; var p = ymd.split('-'), d = new Date(+p[0], +p[1] - 1, +p[2]); var s = d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' }); if (+p[0] !== new Date().getFullYear()) s += ' ' + p[0]; return s; }
  function fmtDateTime(iso) { return fmtDate(iso.slice(0, 10)) + (iso.length > 10 ? ' ' + iso.slice(11, 16) : ''); }
})();
