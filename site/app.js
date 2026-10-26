(function (root) {
  'use strict';
  const hosts = ['Codex', 'Hermes', 'OpenClaw', 'WorkBuddy'];
  const samples = [
    { id: 's1', zh: '阅读时，把触动自己的观点写成一张独立卡片。用自己的话复述，才会成为可以再次调用的想法。', en: 'Turn a useful passage into a single card. Restating it in your own words makes the idea easier to use again.', tags: ['reading'] },
    { id: 's2', zh: '好的工具应该降低记录的门槛。先捕捉一个想法，再慢慢补充它的上下文。', en: 'A good tool makes it easy to capture a thought. Start with the idea, then add context as it grows.', tags: ['ideas', 'writing'] },
    { id: 's3', zh: '下一次写作前，先检索已有的卡片。让过去的阅读和今天的问题产生联系。', en: 'Before writing, search your existing cards. Connect yesterday’s reading with today’s question.', tags: ['writing', 'reading'] }
  ];
  function createNotebook() {
    let serial = 0;
    const book = {
      lang: 'zh', host: 'Codex', query: '', tag: '', cards: [],
      reset() { this.cards = samples.map(c => ({ ...c, tags: [...c.tags] })); this.query = ''; this.tag = ''; },
      text(card) { return card.text === undefined ? card[this.lang] : card.text; },
      setLanguage(lang) { if (['zh', 'en'].includes(lang)) this.lang = lang; },
      setHost(host) { if (hosts.includes(host)) this.host = host; },
      add(raw) {
        const value = String(raw);
        if (!value.trim()) return { error: 'empty' };
        if (value.length > 2000) return { error: 'long' };
        const text = value.trim();
        const tags = [...new Set(Array.from(text.matchAll(/(?:^|\s)#([\p{L}\p{N}_-]{1,40})(?=\s|$|[.,，。!?！？])/gu), m => m[1].toLowerCase()))];
        this.cards.unshift({ id: `u${++serial}`, text, tags });
        return { ok: true };
      },
      visible() {
        const query = this.query.trim().toLocaleLowerCase();
        return this.cards.filter(c => (!this.tag || c.tags.includes(this.tag)) && (!query || `${this.text(c)} ${c.tags.join(' ')}`.toLocaleLowerCase().includes(query)));
      },
      applyExample() { const card = this.cards.find(c => c.id === 's1'); if (card && !card.tags.includes('ideas')) card.tags.push('ideas'); }
    };
    book.reset(); return book;
  }
  function preference(storage, key, value) {
    try { if (value === undefined) return storage.getItem(`slipbox-site-${key}`); storage.setItem(`slipbox-site-${key}`, value); return value; } catch (_) { return null; }
  }
  async function copyText(value, navigatorObject) {
    try { if (!navigatorObject.clipboard || !navigatorObject.clipboard.writeText) return false; await navigatorObject.clipboard.writeText(value); return true; } catch (_) { return false; }
  }
  function mount(doc, win) {
    const $ = id => doc.getElementById(id);
    const book = createNotebook();
    let storage; try { storage = win.localStorage; } catch (_) { storage = null; }
    book.setLanguage(preference(storage, 'language'));
    let theme = preference(storage, 'theme') === 'night' ? 'night' : 'light';
    const queryTheme = new URLSearchParams(win.location.search).get('theme');
    if (['light', 'night'].includes(queryTheme)) theme = queryTheme;
    const t = (zh, en) => book.lang === 'zh' ? zh : en;
    let statusKey = '';
    const messages = {
      empty: ['请先写下一点内容。', 'Write something before saving.'],
      long: ['卡片最多支持 2,000 个字符，请缩短后重试。', 'Cards support up to 2,000 characters. Please shorten the note.'],
      saved: ['已记录。新卡片在最前面，筛选已清除。', 'Saved. Your new card is first; filters have been cleared.'],
      reset: ['已恢复三张示例卡片。', 'The three sample cards have been restored.'],
      example: ['已应用预设示例：阅读卡片新增 #ideas。没有调用 AI。', 'Preset applied: #ideas added to the reading card. No AI was called.'],
      host: ['仅切换演示宿主，卡片保持不变。真实使用需访问同一资料库，或手动迁移后重建索引。', 'Illustrated host changed; cards are unchanged. Real reuse needs a shared library, or manual transfer and index rebuilding.']
    };
    function feedback(key) { statusKey = key; $('feedback').textContent = messages[key] ? t(...messages[key]) : ''; }
    function el(tag, className, text) { const node = doc.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; }
    function filterTag(tag, focusKey) { book.tag = book.tag === tag ? '' : tag; renderCards(focusKey); }
    function renderCards(focusKey) {
      let focusTarget;
      const allTags = [...new Set(book.cards.flatMap(c => c.tags))].sort();
      const tagButtons = [];
      for (const tag of ['', ...allTags]) {
        const count = tag ? book.cards.filter(c => c.tags.includes(tag)).length : book.cards.length;
        const btn = el('button', 'tag-button'); btn.type = 'button'; btn.setAttribute('aria-pressed', String(book.tag === tag));
        btn.append(el('span', '', tag ? `# ${tag}` : t('全部卡片', 'All cards')), el('span', '', String(count)));
        const key = `side:${tag}`;
        if (focusKey === key) focusTarget = btn;
        btn.addEventListener('click', () => filterTag(tag, key)); tagButtons.push(btn);
      }
      $('tags').replaceChildren(...tagButtons);
      const visible = book.visible();
      const cards = visible.map(card => {
        const node = el('article', 'card');
        const meta = el('div', 'card-meta'); meta.append(el('span', '', card.text === undefined ? t('示例卡片', 'SAMPLE CARD') : t('我的卡片', 'YOUR CARD')), el('span', '', `${card.id}.md`));
        node.append(meta, el('p', '', book.text(card)));
        const tags = el('div', 'card-tags');
        for (const tag of card.tags) {
          const btn = el('button', 'card-tag', `# ${tag}`); btn.type = 'button';
          btn.setAttribute('aria-label', t(`按标签 ${tag} 筛选`, `Filter by ${tag}`));
          btn.setAttribute('aria-pressed', String(book.tag === tag));
          const key = `${card.id}:${tag}`;
          if (focusKey === key) focusTarget = btn;
          btn.addEventListener('click', () => filterTag(tag, key)); tags.append(btn);
        }
        node.append(tags); return node;
      });
      $('cards').replaceChildren(...cards); $('empty').hidden = visible.length > 0;
      $('count').textContent = t(`${visible.length} / ${book.cards.length} 张卡片`, `${visible.length} / ${book.cards.length} cards`);
      $('search').value = book.query;
      $('example').disabled = book.cards.find(c => c.id === 's1').tags.includes('ideas');
      if (focusTarget) focusTarget.focus({ preventScroll: true });
    }
    function installText() {
      return t('请按照 https://github.com/xinyou9999/slipbox-skill/blob/main/docs/INSTALL.md 为当前宿主安装 slipbox。先确认宿主类型、安装位置和本地资料库目录，再选择匹配的 v0.1.0 中文包；不要覆盖已有卡片。', 'Please install slipbox for this host using https://github.com/xinyou9999/slipbox-skill/blob/main/docs/INSTALL.md. First confirm the host, installation location, and local library directory, then choose the matching v0.1.0 English bundle. Preserve existing cards.');
    }
    function renderLanguage() {
      doc.documentElement.lang = book.lang === 'zh' ? 'zh-CN' : 'en';
      for (const node of doc.querySelectorAll('[data-zh]')) node.textContent = node.dataset[book.lang].replace(/\\n/g, '\n');
      for (const node of doc.querySelectorAll('[data-placeholder-zh]')) node.placeholder = node.dataset[book.lang === 'zh' ? 'placeholderZh' : 'placeholderEn'];
      $('language').textContent = t('EN', '中文'); $('language').setAttribute('aria-label', t('Switch to English', '切换到中文'));
      doc.title = t('slipbox｜跨智能体的 AI 卡片笔记', 'slipbox | AI-powered card notes across agents');
      $('install-text').value = installText(); $('copy-status').textContent = '';
      renderTheme(); renderCards(); feedback(statusKey);
    }
    function renderTheme() {
      doc.documentElement.dataset.theme = theme;
      $('theme').setAttribute('aria-pressed', String(theme === 'night'));
      $('theme').setAttribute('aria-label', theme === 'night' ? t('切换浅色主题', 'Switch to light theme') : t('切换深色主题', 'Switch to dark theme'));
      $('theme').querySelector('.theme-label').textContent = theme === 'night' ? t('浅色', 'Light') : t('深色', 'Dark');
      doc.querySelector('meta[name="theme-color"]').setAttribute('content', theme === 'night' ? '#292733' : '#f8f9fc');
    }
    $('capture-form').addEventListener('submit', event => {
      event.preventDefault(); const result = book.add($('note').value);
      if (result.error) { feedback(result.error); $('note').focus(); return; }
      book.query = ''; book.tag = ''; $('note').value = ''; renderCards(); feedback('saved'); $('note').focus();
    });
    $('note').addEventListener('keydown', event => { if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) { event.preventDefault(); $('capture-form').requestSubmit(); } });
    $('search').addEventListener('input', event => { book.query = event.target.value; renderCards(); });
    $('host').addEventListener('change', event => { book.setHost(event.target.value); feedback('host'); });
    $('reset').addEventListener('click', () => { book.reset(); $('note').value = ''; renderCards(); feedback('reset'); });
    $('example').addEventListener('click', () => { book.applyExample(); book.query = ''; book.tag = ''; renderCards(); feedback('example'); });
    $('language').addEventListener('click', () => { book.setLanguage(book.lang === 'zh' ? 'en' : 'zh'); preference(storage, 'language', book.lang); renderLanguage(); });
    $('theme').addEventListener('click', () => { theme = theme === 'night' ? 'light' : 'night'; preference(storage, 'theme', theme); renderTheme(); });
    $('copy').addEventListener('click', async () => {
      const value = $('install-text').value;
      const copied = await copyText(value, win.navigator);
      $('copy-status').textContent = copied ? t('已复制安装请求。', 'Installation request copied.') : t('无法自动复制。已选中文本，请使用系统复制操作。', 'Automatic copy unavailable. Text selected; use your system copy command.');
      if (!copied) { $('install-text').focus(); $('install-text').select(); }
    });
    renderLanguage();
    return book;
  }
  const api = { createNotebook, preference, copyText, mount };
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root.document) mount(root.document, root);
})(typeof window !== 'undefined' ? window : globalThis);
