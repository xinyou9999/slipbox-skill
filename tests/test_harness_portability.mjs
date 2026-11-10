import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {createPortability} from '../plugins/dsh-slipbox/portability.mjs';
import {createBridge,makeArgs} from '../plugins/dsh-slipbox/bridge.mjs';

test('lifecycle and filters validate literal arguments and explicit purge confirmation',()=>{
  const id='a'.repeat(32);
  assert.throws(()=>makeArgs({action:'purge',id,expected:'v'}),/Confirm/);
  assert.throws(()=>makeArgs({action:'restore',id:'../bad',expected:'v'}),/id/);
  assert.ok(makeArgs({action:'edit',id,content:'revision',expected:'snapshot'}).includes('--expected=snapshot'));
  assert.ok(makeArgs({action:'list',untagged:true,excludeTags:['literal$(text)']}).includes('--exclude-tag=literal$(text)'));
  assert.throws(()=>makeArgs({action:'list',untagged:'true'}),/filter/);
});

test('browser transfer rejects paths, malformed encoding and unconfirmed apply',async()=>{
  const transfer=createPortability({script:resolve('scripts/slipbox.py'),home:'unused'});
  await assert.rejects(transfer({action:'export',format:'context',ids:[]}),/Select/);
  await assert.rejects(transfer({action:'export',format:'backup',ids:['../x']}),/selected/);
  await assert.rejects(transfer({action:'import-preview',filename:'note.exe',content:'e30='}),/JSON/);
  await assert.rejects(transfer({action:'import-preview',filename:'note.json',content:'!'}),/valid/);
  await assert.rejects(transfer({action:'import-apply',filename:'note.json',content:'e30=',digest:'a'.repeat(64)}),/confirm/i);
});

test('browser export/import safely roundtrips a library without publishing other vocabulary',async()=>{
  const home=await mkdtemp(join(tmpdir(),'slipbox-transfer-test-'));
  const target=await mkdtemp(join(tmpdir(),'slipbox-transfer-target-'));
  try{
    const bridge=createBridge({script:resolve('scripts/slipbox.py'),home});
    const transfer=createPortability({script:resolve('scripts/slipbox.py'),home});
    await bridge({action:'init'});await bridge({action:'tag-add',name:'private-unused'});
    const card=await bridge({action:'add',content:'Selected portable idea',tags:[]});
    const context=await transfer({action:'export',format:'context',ids:[card.id]});
    const text=Buffer.from(context.content,'base64').toString('utf8');
    assert.ok(text.includes('Selected portable idea'));assert.ok(!text.includes('private-unused'));assert.ok(!text.includes(home));
    const backup=await transfer({action:'export',format:'backup'});
    const restore=createPortability({script:resolve('scripts/slipbox.py'),home:target});
    const file={filename:backup.filename,content:backup.content};
    const preview=await restore({action:'import-preview',...file});assert.equal(preview.new_count,1);
    const applied=await restore({action:'import-apply',...file,digest:preview.digest,confirmed:true});assert.equal(applied.imported,1);
    const other=createBridge({script:resolve('scripts/slipbox.py'),home:target});assert.equal((await other({action:'show',id:card.id})).content,card.content);
    const again=await restore({action:'import-preview',...file});assert.equal(again.duplicate_count,1);
  }finally{await rm(home,{recursive:true,force:true});await rm(target,{recursive:true,force:true});}
});
