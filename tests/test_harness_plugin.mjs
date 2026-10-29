import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { createBridge, makeArgs, renderToolResult } from '../plugins/dsh-slipbox/bridge.mjs';

test('bridge rejects unsupported actions and treats user content as a literal argument', () => {
  assert.throws(() => makeArgs({ action: 'exec', command: 'whoami' }), /action/);
  assert.throws(() => makeArgs({ action: 'add', content: 'x', tags: ['a','b','c','d'] }), /tags/);
  assert.throws(() => makeArgs({ action: 'show', id: '../../file' }), /id/);
  assert.throws(() => makeArgs({ action: 'add', content: ' ' }), /content/);
  const value = '$(whoami) & echo sensitive; <script>literal</script>';
  assert.deepEqual(makeArgs({ action: 'add', content: value, tags: ['test'] }), ['add', '--tag=test', '--json', '--', value]);
});

test('host output render returns the canonical result rather than the tool arguments', () => {
  const output='{"cards":[{"content":"read result"}]}';
  assert.deepEqual(renderToolResult({action:'list'},output),[{type:'text',text:output}]);
});

test('installed bridge uses existing Markdown core across separate operations', async () => {
  const home = await mkdtemp(join(tmpdir(), 'slipbox-plugin-'));
  const bridge = createBridge({ python: 'python', script: resolve('scripts/slipbox.py'), home });
  try {
    await bridge({ action: 'init' });
    await bridge({ action: 'tag-add', name: 'test' });
    const card = await bridge({ action: 'add', content: 'portable $(literal) card', tags: ['test'] });
    const found = await bridge({ action: 'search', query: 'portable' });
    assert.equal(found.count, 1);
    assert.equal((await bridge({ action: 'show', id: card.id })).content, 'portable $(literal) card');
    await assert.rejects(bridge({ action: 'add', content: 'bad tag', tags: ['unknown'] }), /unknown|tag/i);
    const edited = await bridge({ action: 'edit', id: card.id, content: 'updated card', tags: ['test'] });
    assert.equal(edited.content, 'updated card');
    const retained = await bridge({ action: 'edit', id: card.id, content: 'body only edit' });
    assert.deepEqual(retained.tags, ['test']);
    await assert.rejects(bridge({ action:'edit',id:card.id,content:'bad tags',tags:{} }), /tags/);
    const cleared = await bridge({ action:'edit',id:card.id,content:'cleared',tags:[] });
    assert.deepEqual(cleared.tags, []);
    for(const content of ['--tag','--clear-tags','--json']) {
      const literal = await bridge({action:'add',content,tags:['test']});
      assert.equal(literal.content,content);
      assert.deepEqual(literal.tags,['test']);
      assert.equal((await bridge({action:'search',query:content})).count,1);
    }
  } finally { await rm(home, { recursive: true, force: true }); }
});
