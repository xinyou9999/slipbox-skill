'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const SITE = fs.existsSync(path.join(__dirname, '../public/site/app.js')) ? path.join(__dirname, '../public/site') : path.join(__dirname, '../site');
const site = require(path.join(SITE, 'app.js'));

test('capture rejects blank and oversized input without changing collection', () => {
  const book = site.createNotebook();
  assert.equal(book.add('  \n ').error, 'empty');
  assert.equal(book.add('a'.repeat(2001)).error, 'long');
  assert.equal(book.cards.length, 3);
  assert.equal(book.add('a'.repeat(2000)).ok, true);
});
test('plain text is preserved; manual tags and search work together', () => {
  const book = site.createNotebook();
  const text = '<img src=x onerror=alert(1)> #reading';
  book.add(text);
  assert.equal(book.cards[0].text, text);
  book.query = 'onerror'; book.tag = 'reading';
  assert.equal(book.visible().length, 1);
  book.tag = 'ideas'; assert.equal(book.visible().length, 0);
});
test('language and host preserve notes; reset restores samples and filters', () => {
  const book = site.createNotebook(); book.add('my own note');
  book.setLanguage('en'); book.setHost('WorkBuddy');
  assert.equal(book.cards[0].text, 'my own note');
  assert.equal(book.lang, 'en'); assert.equal(book.host, 'WorkBuddy');
  book.setLanguage('invalid'); book.setHost('invalid');
  assert.equal(book.lang, 'en'); assert.equal(book.host, 'WorkBuddy');
  book.query = 'no match'; book.tag = 'reading'; book.reset();
  assert.equal(book.cards.length, 3); assert.equal(book.visible().length, 3);
  assert.equal(book.query, ''); assert.equal(book.tag, '');
});
test('tag preset is explicit and does not invoke a model', () => {
  const book = site.createNotebook();
  book.add('unrelated'); book.applyExample(); book.applyExample();
  assert.equal(book.cards.length, 4);
  assert.ok(book.cards.find(c => c.id === 's1').tags.includes('ideas'));
});
test('denied preferences and clipboard do not throw', async () => {
  const denied = { getItem() { throw Error('denied'); }, setItem() { throw Error('denied'); } };
  assert.equal(site.preference(denied, 'theme'), null);
  assert.equal(site.preference(denied, 'theme', 'night'), null);
  assert.equal(await site.copyText('install', {}), false);
  assert.equal(await site.copyText('install', { clipboard: { writeText: async () => { throw Error('denied'); } } }), false);
  let copied; assert.equal(await site.copyText('install', { clipboard: { writeText: async v => { copied = v; } } }), true);
  assert.equal(copied, 'install');
});
test('rendering uses text nodes, static page has accessible forms and exact assets', () => {
  const js = fs.readFileSync(path.join(SITE, 'app.js'), 'utf8');
  assert.doesNotMatch(js, /innerHTML|insertAdjacentHTML|\beval\(|\bfetch\(|XMLHttpRequest/);
  const html = fs.readFileSync(path.join(SITE, 'index.html'), 'utf8');
  assert.match(html, /aria-live="polite"/);
  for (const bundle of ['generic-zh', 'generic-en', 'workbuddy-zh', 'workbuddy-en']) {
    assert.ok(html.includes(`https://github.com/xinyou9999/slipbox-skill/releases/download/v0.1.0/slipbox-0.1.0-${bundle}.zip`));
  }
});

test('website analytics uses the issued public beacon with bilingual disclosure', () => {
  const html = fs.readFileSync(path.join(SITE, 'index.html'), 'utf8');
  const beacons = html.match(/<script\b[^>]*\bdata-cf-beacon=[^>]*><\/script>/g) || [];
  assert.equal(beacons.length, 1);
  assert.match(beacons[0], /type="module"/);
  assert.match(beacons[0], /src="https:\/\/static\.cloudflareinsights\.com\/beacon\.min\.js"/);
  const config = JSON.parse(beacons[0].match(/data-cf-beacon='([^']+)'/)[1]);
  assert.deepEqual(config, { token: '6eddef5400a04c038810266cf2352184' });
  assert.ok(html.indexOf(beacons[0]) < html.indexOf('</body>'));
  assert.match(html, /data-zh="本站使用 Cloudflare Web Analytics/);
  assert.match(html, /data-en="This site uses Cloudflare Web Analytics/);
  assert.equal((html.match(/<script\b[^>]*src="https?:/g) || []).length, 1);
});

// Small DOM contract harness: exercises mounted handlers without installing a DOM library.
// This is behavior evidence, not browser layout or visual verification.
function domHarness() {
  class Element {
    constructor() { this.children = []; this.dataset = {}; this.events = {}; this.value = ''; this.textContent = ''; this.attributes = {}; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    setAttribute(name, value) { this.attributes[name] = value; }
    addEventListener(name, handler) { this.events[name] = handler; }
    querySelector() { return this.themeLabel || (this.themeLabel = new Element()); }
    focus() { this.focused = true; }
    select() { this.selected = true; }
    fire(name) { return this.events[name]({ target: this, preventDefault() {} }); }
  }
  const nodes = Object.fromEntries(['feedback', 'tags', 'cards', 'empty', 'count', 'search', 'example', 'language', 'install-text', 'copy-status', 'theme', 'capture-form', 'note', 'host', 'reset', 'copy'].map(id => [id, new Element()]));
  const meta = new Element();
  const doc = { documentElement: new Element(), getElementById: id => nodes[id], createElement: () => new Element(), querySelectorAll: () => [], querySelector: () => meta };
  const win = { location: { search: '' }, navigator: {} };
  Object.defineProperty(win, 'localStorage', { get() { throw Error('denied'); } });
  return { nodes, doc, win };
}
test('mounted demo handles capture, DOM text safety, filtering, host/language/theme, reset and clipboard denial', async () => {
  const { nodes, doc, win } = domHarness();
  const book = site.mount(doc, win);
  assert.equal(nodes.cards.children.length, 3);
  nodes.note.value = '   '; nodes['capture-form'].fire('submit');
  assert.match(nodes.feedback.textContent, /请先/);
  nodes.note.value = '<script>alert(1)</script> #test'; nodes['capture-form'].fire('submit');
  assert.equal(nodes.cards.children[0].children[1].textContent, '<script>alert(1)</script> #test');
  assert.equal(nodes.cards.children[0].children[1].children.length, 0);
  nodes.search.value = 'no-match'; nodes.search.fire('input'); assert.equal(nodes.empty.hidden, false);
  nodes.language.fire('click'); nodes.host.value = 'Hermes'; nodes.host.fire('change');
  assert.equal(book.cards.length, 4); assert.equal(book.host, 'Hermes'); assert.equal(book.lang, 'en');
  assert.equal(nodes.cards.children.length, 0);
  nodes.theme.fire('click'); assert.equal(doc.documentElement.dataset.theme, 'night');
  nodes.reset.fire('click'); assert.equal(nodes.cards.children.length, 3); assert.equal(nodes.search.value, '');
  nodes.tags.children[1].fire('click');
  assert.equal(nodes.tags.children[1].focused, true);
  assert.equal(nodes.cards.children.length, 1);
  nodes.cards.children[0].children[2].children[0].fire('click');
  assert.equal(nodes.cards.children[1].children[2].children[0].focused, true);
  assert.equal(nodes.cards.children.length, 3);
  nodes.example.fire('click'); assert.equal(nodes.example.disabled, true);
  await nodes.copy.fire('click'); assert.equal(nodes['install-text'].selected, true); assert.match(nodes['copy-status'].textContent, /Automatic copy unavailable/);
});
