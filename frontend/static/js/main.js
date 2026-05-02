// ── Sidebar (mobile) ──────────────────────────────────────
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const toggle = document.getElementById('sidebar-toggle');
  if (!sidebar || !overlay || !toggle) return;
  const isOpen = sidebar.classList.contains('translate-x-0');
  if (isOpen) {
    sidebar.classList.remove('translate-x-0');
    overlay.classList.add('hidden');
    toggle.setAttribute('aria-label', 'Open menu');
  } else {
    sidebar.classList.add('translate-x-0');
    overlay.classList.remove('hidden');
    toggle.setAttribute('aria-label', 'Close menu');
  }
}

function closeSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const toggle = document.getElementById('sidebar-toggle');
  if (!sidebar || !overlay || !toggle) return;
  sidebar.classList.remove('translate-x-0');
  overlay.classList.add('hidden');
  toggle.setAttribute('aria-label', 'Open menu');
}

// Expose for inline onclick handlers (e.g. in templates)
window.toggleSidebar = toggleSidebar;
window.closeSidebar = closeSidebar;

// ── Tag modal ────────────────────────────────────────────
function openTagModal() {
  document.getElementById('tag-modal').classList.remove('hidden');
  document.querySelector('#tag-modal input[name="name"]')?.focus();
  document.getElementById('parent-hint')?.classList.add('hidden');
  const sel = document.getElementById('parent-select');
  if (sel) sel.value = '';
}

function updateParentHint(select) {
  const hint = document.getElementById('parent-hint');
  const name = document.getElementById('parent-hint-name');
  if (!hint || !name) return;
  if (select.value) {
    name.textContent = select.options[select.selectedIndex].text;
    hint.classList.remove('hidden');
  } else {
    hint.classList.add('hidden');
  }
}

function closeTagModal() {
  document.getElementById('tag-modal').classList.add('hidden');
}

function openConfirmDeleteModal() {
  document.getElementById('confirm-delete-modal').classList.remove('hidden');
}

function closeConfirmDeleteModal() {
  document.getElementById('confirm-delete-modal').classList.add('hidden');
}

// ── New Card modal ───────────────────────────────────────
function openCardModal() {
  const form = document.getElementById('card-modal-form');
  form.reset();
  // Reset audio zone
  showNewCardAudioState('upload');
  // Reset custom tag checkbox visuals
  form.querySelectorAll('.modal-tag-row').forEach(row => row.classList.remove('bg-teal-600/15'));
  form.querySelectorAll('.modal-tag-checkbox').forEach(cb => {
    cb.classList.remove('bg-teal-600', 'border-teal-500');
    cb.classList.add('bg-stone-800', 'border-stone-600');
  });
  form.querySelectorAll('.modal-tag-check').forEach(svg => svg.classList.add('hidden'));
  form.querySelectorAll('.modal-tag-text').forEach(span => {
    span.classList.remove('text-teal-300');
    span.classList.add('text-stone-300');
  });
  document.getElementById('card-modal').classList.remove('hidden');
  form.querySelector('textarea[name="phrase"]')?.focus();
}

function closeCardModal() {
  document.getElementById('card-modal').classList.add('hidden');
}

// ── Card modal — audio ───────────────────────────────────
function showNewCardAudioState(state) {
  document.getElementById('audio-upload-zone').classList.toggle('hidden', state !== 'upload');
  document.getElementById('modal-abair-btn').classList.toggle('hidden', state !== 'upload');
  document.getElementById('audio-attached').classList.toggle('hidden', state !== 'attached');
  document.getElementById('modal-abair-generated').classList.toggle('hidden', state !== 'generated');
}

function handleModalAudio(input) {
  const file = input.files[0];
  if (!file) return;
  document.getElementById('modal-synthesised-filename').value = '';
  document.getElementById('audio-filename-display').textContent = file.name;
  showNewCardAudioState('attached');
}

function removeModalAudio() {
  document.getElementById('modal-audio-input').value = '';
  showNewCardAudioState('upload');
}

function removeModalAbairAudio() {
  document.getElementById('modal-synthesised-filename').value = '';
  showNewCardAudioState('upload');
}

async function synthesiseModalAudio() {
  const phrase = document.querySelector('#card-modal-form textarea[name="phrase"]')?.value?.trim();
  if (!phrase) return;
  const btn = document.getElementById('modal-abair-btn');
  const originalHTML = btn.innerHTML;
  btn.disabled = true;
  btn.textContent = 'Generating…';
  try {
    const fd = new FormData();
    fd.append('phrase', phrase);
    const token = document.querySelector('meta[name="csrf-token"]')?.content ?? '';
    const res = await fetch('/cards/synthesise', {
      method: 'POST',
      body: fd,
      headers: { 'X-CSRF-Token': token },
    });
    if (!res.ok) throw new Error('synthesis failed');
    const data = await res.json();
    document.getElementById('modal-audio-input').value = '';
    document.getElementById('modal-synthesised-filename').value = data.filename;
    showNewCardAudioState('generated');
  } catch {
    // fail silently — button re-enabled below
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHTML;
  }
}

// ── Card modal — tag checkboxes ──────────────────────────
function updateTagCheckbox(input) {
  const row = input.closest('.modal-tag-row');
  const box = row.querySelector('.modal-tag-checkbox');
  const check = row.querySelector('.modal-tag-check');
  const text = row.querySelector('.modal-tag-text');
  if (input.checked) {
    row.classList.add('bg-teal-600/15');
    box.classList.replace('bg-stone-800', 'bg-teal-600');
    box.classList.replace('border-stone-600', 'border-teal-500');
    check.classList.remove('hidden');
    text.classList.replace('text-stone-300', 'text-teal-300');
  } else {
    row.classList.remove('bg-teal-600/15');
    box.classList.replace('bg-teal-600', 'bg-stone-800');
    box.classList.replace('border-teal-500', 'border-stone-600');
    check.classList.add('hidden');
    text.classList.replace('text-teal-300', 'text-stone-300');
  }
}

// ── Edit Card modal ─────────────────────────────────────
let _editCardId = null;
let _editExistingAudioFilename = null;
let _editAudio = null;

const EDIT_PLAY_ICON =
  '<svg class="w-3.5 h-3.5 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
const EDIT_PAUSE_ICON =
  '<svg class="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>';

function _fmtTime(t) {
  if (!isFinite(t) || isNaN(t)) return '0:00';
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return m + ':' + s.toString().padStart(2, '0');
}

function openEditModal(btn) {
  const cardEl = btn.closest('.card-item') || btn.closest('.swipe-card-container')?.querySelector('.card-item');
  _editCardId = cardEl.id.replace('card-', '');

  const phrase = cardEl.dataset.phrase;
  const translation = cardEl.dataset.translation || '';
  const tags = cardEl.dataset.tags ? cardEl.dataset.tags.split(',').filter(Boolean) : [];
  const audio = cardEl.dataset.audio;

  const form = document.getElementById('edit-modal-form');
  form.setAttribute('hx-put', '/cards/' + _editCardId);
  htmx.process(form);

  document.getElementById('edit-phrase').value = phrase;
  document.getElementById('edit-translation').value = translation;

  stopEditAudio();
  document.getElementById('edit-remove-audio').value = 'false';
  document.getElementById('edit-audio-input').value = '';
  document.getElementById('edit-synthesised-filename').value = '';

  if (audio) {
    _editExistingAudioFilename = audio;
    showEditAudioState('existing');
    setupEditAudioPlayer('/static/content/' + audio);
  } else {
    _editExistingAudioFilename = null;
    showEditAudioState('upload');
  }

  resetEditModalTags();
  tags.forEach((slug) => checkEditModalTag(slug));
  hideEditDeleteConfirm();

  document.getElementById('edit-modal').classList.remove('hidden');
  document.getElementById('edit-phrase').focus();
}

function closeEditModal() {
  stopEditAudio();
  document.getElementById('edit-modal').classList.add('hidden');
}

function showEditAudioState(state) {
  document.getElementById('edit-audio-existing').classList.toggle('hidden', state !== 'existing');
  document.getElementById('edit-audio-upload-zone').classList.toggle('hidden', state !== 'upload');
  document.getElementById('edit-abair-btn').classList.toggle('hidden', state !== 'upload');
  document.getElementById('edit-audio-new').classList.toggle('hidden', state !== 'new');
  document.getElementById('edit-abair-generated').classList.toggle('hidden', state !== 'abair');
}

function setupEditAudioPlayer(url) {
  stopEditAudio();
  _editAudio = new Audio(url);
  _editAudio.ontimeupdate = function () {
    if (!_editAudio || !_editAudio.duration) return;
    const pct = (_editAudio.currentTime / _editAudio.duration) * 100;
    document.getElementById('edit-audio-progress').style.width = pct + '%';
    document.getElementById('edit-audio-seek').value = _editAudio.currentTime;
    document.getElementById('edit-audio-time').textContent =
      _fmtTime(_editAudio.currentTime) + ' / ' + _fmtTime(_editAudio.duration);
  };
  _editAudio.onloadedmetadata = function () {
    document.getElementById('edit-audio-seek').max = _editAudio.duration;
    document.getElementById('edit-audio-time').textContent =
      '0:00 / ' + _fmtTime(_editAudio.duration);
  };
  _editAudio.onended = function () {
    const btn = document.getElementById('edit-audio-play-btn');
    if (btn) btn.innerHTML = EDIT_PLAY_ICON;
    document.getElementById('edit-audio-seek').value = 0;
    document.getElementById('edit-audio-progress').style.width = '0%';
    document.getElementById('edit-audio-time').textContent =
      '0:00' +
      (_editAudio && _editAudio.duration ? ' / ' + _fmtTime(_editAudio.duration) : '');
  };
}

function toggleEditAudioPlayback() {
  if (!_editAudio) return;
  const btn = document.getElementById('edit-audio-play-btn');
  if (_editAudio.paused) {
    _editAudio.play();
    btn.innerHTML = EDIT_PAUSE_ICON;
  } else {
    _editAudio.pause();
    btn.innerHTML = EDIT_PLAY_ICON;
  }
}

function seekEditAudio(value) {
  if (!_editAudio) return;
  _editAudio.currentTime = parseFloat(value);
}

function stopEditAudio() {
  if (_editAudio) {
    _editAudio.pause();
    _editAudio.src = '';
    _editAudio = null;
  }
  const btn = document.getElementById('edit-audio-play-btn');
  if (btn) btn.innerHTML = EDIT_PLAY_ICON;
  const seek = document.getElementById('edit-audio-seek');
  if (seek) {
    seek.value = 0;
    seek.max = 100;
  }
  const prog = document.getElementById('edit-audio-progress');
  if (prog) prog.style.width = '0%';
  const time = document.getElementById('edit-audio-time');
  if (time) time.textContent = '0:00';
}

function removeEditExistingAudio() {
  stopEditAudio();
  document.getElementById('edit-remove-audio').value = 'true';
  _editExistingAudioFilename = null;
  showEditAudioState('upload');
}

function handleEditAudioNew(input) {
  const file = input.files[0];
  if (!file) return;
  stopEditAudio();
  document.getElementById('edit-synthesised-filename').value = '';
  document.getElementById('edit-audio-new-name').textContent = file.name;
  showEditAudioState('new');
}

function removeEditNewAudio() {
  document.getElementById('edit-audio-input').value = '';
  if (_editExistingAudioFilename) {
    document.getElementById('edit-remove-audio').value = 'false';
    showEditAudioState('existing');
    setupEditAudioPlayer('/static/content/' + _editExistingAudioFilename);
  } else {
    document.getElementById('edit-remove-audio').value = 'false';
    showEditAudioState('upload');
  }
}

function removeEditAbairAudio() {
  document.getElementById('edit-synthesised-filename').value = '';
  showEditAudioState('upload');
}

async function synthesiseEditAudio() {
  const phrase = document.getElementById('edit-phrase')?.value?.trim();
  if (!phrase) return;
  const btn = document.getElementById('edit-abair-btn');
  const originalHTML = btn.innerHTML;
  btn.disabled = true;
  btn.textContent = 'Generating…';
  try {
    const fd = new FormData();
    fd.append('phrase', phrase);
    const token = document.querySelector('meta[name="csrf-token"]')?.content ?? '';
    const res = await fetch('/cards/synthesise', {
      method: 'POST',
      body: fd,
      headers: { 'X-CSRF-Token': token },
    });
    if (!res.ok) throw new Error('synthesis failed');
    const data = await res.json();
    document.getElementById('edit-audio-input').value = '';
    document.getElementById('edit-synthesised-filename').value = data.filename;
    showEditAudioState('abair');
  } catch {
    // fail silently — button re-enabled below
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHTML;
  }
}

function resetEditModalTags() {
  const container = document.getElementById('edit-modal-tags');
  if (!container) return;
  container.querySelectorAll('input[name="tag_slugs"]').forEach((input) => {
    if (input.checked) {
      input.checked = false;
      updateTagCheckbox(input);
    }
  });
}

function checkEditModalTag(slug) {
  const container = document.getElementById('edit-modal-tags');
  if (!container) return;
  const input = container.querySelector(
    `input[name="tag_slugs"][value="${CSS.escape(slug)}"]`
  );
  if (input && !input.checked) {
    input.checked = true;
    updateTagCheckbox(input);
  }
}

function showEditDeleteConfirm() {
  document.getElementById('edit-delete-btn').classList.add('hidden');
  document.getElementById('edit-delete-confirm').classList.remove('hidden');
}

function hideEditDeleteConfirm() {
  document.getElementById('edit-delete-btn').classList.remove('hidden');
  document.getElementById('edit-delete-confirm').classList.add('hidden');
}

function confirmEditDelete() {
  const id = _editCardId;
  closeEditModal();
  htmx.ajax('DELETE', '/cards/' + id, { target: '#card-list', swap: 'outerHTML' });
}

// ── Sidebar — tag filter + breadcrumb ───────────────────
function setActiveTag(el) {
  document.querySelectorAll('.tag-filter-btn').forEach((b) => b.classList.remove('is-active'));
  el.classList.add('is-active');

  const hxGet = el.getAttribute('hx-get') || '';
  const slug = new URL(hxGet, window.location.origin).searchParams.get('tag_slug') || '';
  document.getElementById('active-tag-slug').value = slug;

  const breadcrumb = document.getElementById('main-breadcrumb');
  const isAllCards = el.id === 'btn-all-cards';
  if (isAllCards) {
    breadcrumb.innerHTML = 'All cards';
    breadcrumb.className = 'font-mono text-base text-stone-300 truncate';
  } else {
    const tagName = el.querySelector('.flex-1')?.textContent?.trim() ?? '';
    breadcrumb.innerHTML =
      '<span class="text-stone-600">All cards</span>' +
      '<span class="text-stone-600 mx-2">/</span>' +
      '<span class="text-teal-400">' +
      tagName +
      '</span>';
    breadcrumb.className = 'font-mono text-base truncate';
  }
}

function collapseAllAccordions() {
  document.querySelectorAll('.tag-children').forEach((c) => c.classList.remove('is-open'));
  document.querySelectorAll('.tag-chevron').forEach((c) => {
    c.classList.add('-rotate-90');
    c.classList.remove('rotate-0');
  });
}

function toggleTagItem(btn) {
  const item = btn.closest('.tag-item');
  const children = item.querySelector('.tag-children');
  const chevron = btn.querySelector('.tag-chevron');
  const isOpen = children.classList.contains('is-open');

  // Accordion: close sibling expandables at the same level (and all their nested children)
  const parentUl = item.parentElement.parentElement; // .tag-item > li > ul
  parentUl.querySelectorAll(':scope > li > .tag-item').forEach((other) => {
    if (other !== item) {
      other.querySelectorAll('.tag-children').forEach((c) => c.classList.remove('is-open'));
      other.querySelectorAll('.tag-chevron').forEach((c) => {
        c.classList.add('-rotate-90');
        c.classList.remove('rotate-0');
      });
    }
  });

  if (isOpen) {
    children.classList.remove('is-open');
    chevron?.classList.add('-rotate-90');
    chevron?.classList.remove('rotate-0');
  } else {
    children.classList.add('is-open');
    chevron?.classList.remove('-rotate-90');
    chevron?.classList.add('rotate-0');
  }
}

// ── Result count badge ───────────────────────────────────
function updateResultBadge() {
  const cardList = document.getElementById('card-list');
  const badge = document.getElementById('result-count-badge');
  if (!cardList || !badge) return;
  const count = cardList.querySelectorAll('.card-item').length;
  const activeTag = document.querySelector('.tag-filter-btn.is-active');
  const isAllCards = !activeTag || activeTag.id === 'btn-all-cards';
  const searchInput = document.querySelector('input[name="q"]');
  const hasSearch = searchInput?.value?.trim();
  if (!isAllCards || hasSearch) {
    badge.textContent = count + ' result' + (count !== 1 ? 's' : '');
    badge.classList.remove('hidden');
  } else {
    badge.classList.add('hidden');
  }
}

// ── HTMX hooks ───────────────────────────────────────────
// Track what triggered the last card-list request (parent vs leaf tag)
let _lastCardListTriggerTagType = null;

document.addEventListener('htmx:beforeRequest', function (evt) {
  const elt = evt.detail?.elt;
  if (elt?.getAttribute?.('hx-target') === '#card-list') {
    _lastCardListTriggerTagType = elt.dataset?.tagType ?? 'leaf';
  }
});

// Close mobile sidebar only when navigating (card list swap) from a leaf tag,
// not when clicking a parent tag (so user can select a child) or when adding/deleting tags
document.addEventListener('htmx:afterSwap', function (evt) {
  if (evt.detail?.target?.id === 'card-list') {
    if (_lastCardListTriggerTagType !== 'parent') {
      closeSidebar();
    }
    _lastCardListTriggerTagType = null;
  }
});

// After any HTMX settle, check if the active tag was removed (e.g. by deleting empty tags).
// If no filter button is active, fall back to "All Cards".
document.addEventListener('htmx:afterSettle', function () {
  updateResultBadge();
  const anyActive = document.querySelector('.tag-filter-btn.is-active');
  if (!anyActive) {
    const allCardsBtn = document.getElementById('btn-all-cards');
    if (allCardsBtn) {
      htmx.trigger(allCardsBtn, 'click');
    }
  }
});

// Close modals and mobile sidebar on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeSidebar();
    closeTagModal();
    closeConfirmDeleteModal();
    closeCardModal();
    closeEditModal();
  }
});

// ── Swipe to reveal edit (mobile only) ───────────────────
const SWIPE_THRESHOLD = 40;
const SWIPE_SNAP_THRESHOLD = 0.3;

function closeAllSwipeCards(exceptContainer) {
  document.querySelectorAll('.swipe-card-container').forEach((container) => {
    if (container === exceptContainer) return;
    if ((container._swipeCurrentX ?? 0) < 0) {
      const inner = container.querySelector('.swipe-card-inner');
      if (inner) {
        container._swipeCurrentX = 0;
        inner.style.transform = 'translateX(0px)';
      }
    }
  });
}

function initSwipeCards() {
  const containers = document.querySelectorAll('.swipe-card-container');
  containers.forEach((container) => {
    const inner = container.querySelector('.swipe-card-inner');
    const action = container.querySelector('.swipe-action');
    if (!inner || !action || !container.matches('.swipe-card-container')) return;

    let startX = 0;
    let startY = 0;
    let startTranslate = 0;
    const actionWidth = parseInt(inner.dataset.swipeActionWidth || '64', 10);
    container._swipeCurrentX = container._swipeCurrentX ?? 0;

    function isMobile() {
      return window.matchMedia('(max-width: 767px)').matches;
    }

    function setTranslate(x) {
      container._swipeCurrentX = Math.max(-actionWidth, Math.min(0, x));
      inner.style.transform = `translateX(${container._swipeCurrentX}px)`;
    }

    function closeOtherOpenCards() {
      closeAllSwipeCards(container);
    }

    function onTouchStart(e) {
      if (!isMobile()) return;
      closeOtherOpenCards();
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      startTranslate = container._swipeCurrentX;
    }

    function onTouchMove(e) {
      if (!isMobile()) return;
      const dx = e.touches[0].clientX - startX;
      const dy = e.touches[0].clientY - startY;
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 10) {
        e.preventDefault();
      }
      const newX = startTranslate + dx;
      setTranslate(newX);
    }

    function onTouchEnd() {
      if (!isMobile()) return;
      const threshold = actionWidth * SWIPE_SNAP_THRESHOLD;
      const shouldReveal =
        container._swipeCurrentX < -threshold ||
        (container._swipeCurrentX < 0 && -container._swipeCurrentX > actionWidth / 2);
      const finalX = shouldReveal ? -actionWidth : 0;
      inner.style.transform = `translateX(${finalX}px)`;
      container._swipeCurrentX = finalX;
      if (shouldReveal) {
        container.dataset.swipeOccurred = 'true';
        setTimeout(() => delete container.dataset.swipeOccurred, 300);
      }
    }

    container.addEventListener('touchstart', onTouchStart, { passive: true });
    container.addEventListener('touchmove', onTouchMove, { passive: false });
    container.addEventListener('touchend', onTouchEnd, { passive: true });
  });
}

// Prevent card click (e.g. audio) when user just swiped — allow edit button
document.addEventListener('click', (e) => {
  const container = e.target.closest('.swipe-card-container');
  if (container?.dataset.swipeOccurred === 'true') {
    if (e.target.closest('.swipe-action')) return;
    e.preventDefault();
    e.stopPropagation();
  }
}, true);

// Close open swipe cards when clicking on background (mobile only)
document.addEventListener('click', (e) => {
  if (!window.matchMedia('(max-width: 767px)').matches) return;
  if (e.target.closest('.swipe-card-container')) return;
  closeAllSwipeCards();
});

// Init swipe on load and after HTMX swaps
function initSwipeCardsIfNeeded() {
  if (window.matchMedia('(max-width: 767px)').matches) {
    initSwipeCards();
  }
}
document.addEventListener('DOMContentLoaded', initSwipeCardsIfNeeded);
document.addEventListener('htmx:afterSettle', initSwipeCardsIfNeeded);

// ── Audio playback ──────────────────────────────────────
// Use Web Audio API to avoid Chrome's ~10 WebMediaPlayer limit on HTMLAudioElement.
let _audioCtx = null;
let _currentSource = null;
let _playingCardId = null;

function getAudioContext() {
  if (!_audioCtx) {
    _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  return _audioCtx;
}

function toggleCardAudio(cardId, url) {
  const card = document.getElementById('card-' + cardId);

  if (_playingCardId === cardId && _currentSource) {
    try {
      _currentSource.stop();
    } catch (_) {}
    _currentSource = null;
    card?.classList.remove('playing');
    _playingCardId = null;
    return;
  }

  if (_playingCardId && _playingCardId !== cardId) {
    document.getElementById('card-' + _playingCardId)?.classList.remove('playing');
    try {
      if (_currentSource) _currentSource.stop();
    } catch (_) {}
    _currentSource = null;
  }

  _playingCardId = cardId;
  card?.classList.add('playing');

  const ctx = getAudioContext();
  if (ctx.state === 'suspended') {
    ctx.resume();
  }

  fetch(url)
    .then((r) => r.arrayBuffer())
    .then((buf) => ctx.decodeAudioData(buf))
    .then((buffer) => {
      if (_playingCardId !== cardId) return;
      const src = ctx.createBufferSource();
      src.buffer = buffer;
      src.connect(ctx.destination);
      src.onended = () => {
        if (_playingCardId === cardId) {
          card?.classList.remove('playing');
          _playingCardId = null;
        }
      };
      _currentSource = src;
      src.start(0);
    })
    .catch(() => {
      card?.classList.remove('playing');
      _playingCardId = null;
    });
}

// ── Tag drag-and-drop reordering ─────────────────────────
function getCsrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : '';
}

let _reorderModeActive = false;

function toggleReorderMode(btn) {
  _reorderModeActive = !_reorderModeActive;

  const tagTree = document.getElementById('tag-tree');
  if (tagTree) {
    tagTree.classList.toggle('reorder-mode', _reorderModeActive);
    tagTree.querySelectorAll('li[data-slug]').forEach((li) => {
      li.draggable = _reorderModeActive;
    });
  }

  btn.classList.toggle('is-reordering', _reorderModeActive);
  const label = btn.querySelector('.reorder-btn-label');
  if (label) label.textContent = _reorderModeActive ? 'Done reordering' : 'Reorder tags';

  if (!_reorderModeActive) {
    htmx.ajax('GET', '/tags', { target: '#tag-tree', swap: 'outerHTML' });
  }
}
window.toggleReorderMode = toggleReorderMode;

let _tagDragController = null;

function initTagDragDrop() {
  const tagTree = document.getElementById('tag-tree');
  if (!tagTree) return;

  // Re-apply reorder mode if it was active before this re-render.
  if (_reorderModeActive) {
    tagTree.classList.add('reorder-mode');
    tagTree.querySelectorAll('li[data-slug]').forEach((li) => {
      li.draggable = true;
    });
  }

  if (_tagDragController) _tagDragController.abort();
  _tagDragController = new AbortController();
  const { signal } = _tagDragController;

  let draggedEl = null;

  function clearDropIndicators() {
    tagTree.querySelectorAll('li[data-slug]').forEach((el) => {
      el.style.borderTop = '';
      el.style.borderBottom = '';
    });
  }

  tagTree.addEventListener('dragstart', (e) => {
    const li = e.target.closest('li[data-slug]');
    if (!li) return;
    draggedEl = li;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', li.dataset.slug);

    // Ghost image: clone only the header row so expanded children aren't included.
    // For expandable tags the row is li > .tag-item > .flex;
    // for leaf tags it is li > .flex — in both cases the direct parent of the button.
    const btn = li.querySelector('button.tag-filter-btn');
    const buttonRow = btn ? btn.parentElement : li;
    const rowRect = buttonRow.getBoundingClientRect();

    const ghost = buttonRow.cloneNode(true);
    ghost.style.cssText = `
      position: fixed;
      left: ${rowRect.left}px;
      top: -9999px;
      width: ${rowRect.width}px;
      background: rgb(28 25 23);
      border-radius: 8px;
      pointer-events: none;
    `;
    document.body.appendChild(ghost);

    const cursorX = Math.min(e.clientX - rowRect.left, rowRect.width);
    const cursorY = Math.max(0, e.clientY - rowRect.top);
    e.dataTransfer.setDragImage(ghost, cursorX, cursorY);

    // Browser snapshots the ghost at dragstart; remove it next frame.
    requestAnimationFrame(() => {
      ghost.remove();
      li.classList.add('opacity-40');
    });
  }, { signal });

  tagTree.addEventListener('dragend', () => {
    if (draggedEl) draggedEl.classList.remove('opacity-40');
    clearDropIndicators();
    draggedEl = null;
  }, { signal });

  tagTree.addEventListener('dragover', (e) => {
    e.preventDefault();
    if (!draggedEl) return;
    const target = e.target.closest('li[data-slug]');
    if (!target || target === draggedEl) return;
    if (target.dataset.parentSlug !== draggedEl.dataset.parentSlug) return;
    e.dataTransfer.dropEffect = 'move';
    clearDropIndicators();
    const rect = target.getBoundingClientRect();
    if (e.clientY < rect.top + rect.height / 2) {
      target.style.borderTop = '2px solid rgb(20 184 166)';
    } else {
      target.style.borderBottom = '2px solid rgb(20 184 166)';
    }
  }, { signal });

  tagTree.addEventListener('dragleave', (e) => {
    const target = e.target.closest('li[data-slug]');
    if (target && !target.contains(e.relatedTarget)) {
      target.style.borderTop = '';
      target.style.borderBottom = '';
    }
  }, { signal });

  tagTree.addEventListener('drop', (e) => {
    e.preventDefault();
    if (!draggedEl) return;
    const target = e.target.closest('li[data-slug]');
    if (!target || target === draggedEl) return;
    if (target.dataset.parentSlug !== draggedEl.dataset.parentSlug) return;

    const rect = target.getBoundingClientRect();
    const insertBefore = e.clientY < rect.top + rect.height / 2;

    clearDropIndicators();
    draggedEl.classList.remove('opacity-40');

    const parent = target.parentElement;
    if (insertBefore) {
      parent.insertBefore(draggedEl, target);
    } else {
      parent.insertBefore(draggedEl, target.nextSibling);
    }

    const slugs = Array.from(parent.children)
      .filter((el) => el.tagName === 'LI' && el.dataset?.slug)
      .map((el) => el.dataset.slug);
    const parentSlug = draggedEl.dataset.parentSlug || null;

    draggedEl = null;

    fetch('/tags/reorder', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': getCsrfToken() },
      body: JSON.stringify({ slugs, parent_slug: parentSlug }),
    }).catch(() => {
      htmx.ajax('GET', '/tags', { target: '#tag-tree', swap: 'outerHTML' });
    });
  }, { signal });
}

window.initTagDragDrop = initTagDragDrop;
document.addEventListener('DOMContentLoaded', initTagDragDrop);
document.addEventListener('htmx:afterSettle', initTagDragDrop);
