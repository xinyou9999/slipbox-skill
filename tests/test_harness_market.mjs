import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createMarketIndex } from '../scripts/generate_harness_market.mjs';

const pkg=JSON.parse(readFileSync(new URL('../plugins/dsh-slipbox/package.json',import.meta.url),'utf8'));
test('market source is pinned to a full commit and uses the self-contained Git package',()=>{
  const commit='1234567890abcdef1234567890abcdef12345678';
  const index=createMarketIndex({commit,publishTimestamp:1793318400,packageJson:pkg});
  const plugin=index.plugins[0], version=plugin.versions[0];
  assert.equal(index.format,1);
  assert.ok(index.title.en && index.title.zh && plugin.description.en && plugin.description.zh);
  assert.equal(plugin.name,pkg.name);
  assert.equal(version.version,pkg.version);
  assert.deepEqual(version.engines,pkg.engines.dsh?{dsh:pkg.engines.dsh}:{});
  assert.deepEqual(version.source,{type:'git',url:'https://github.com/xinyou9999/slipbox-skill',commit,path:'packages/dsh-slipbox'});
  assert.equal(version.publishTimestamp,1793318400);
});
test('market generation rejects moving branches, malformed metadata and timestamps',()=>{
  const valid={commit:'a'.repeat(40),publishTimestamp:1793318400,packageJson:pkg};
  for(const commit of ['main','v0.1.2','abc123','a'.repeat(39),'g'.repeat(40),'a'.repeat(40)+'&path:/elsewhere']) assert.throws(()=>createMarketIndex({...valid,commit}),/commit/i);
  for(const publishTimestamp of [0,-1,1.5,Infinity,'1793318400']) assert.throws(()=>createMarketIndex({...valid,publishTimestamp}),/timestamp/i);
  assert.throws(()=>createMarketIndex({...valid,packageJson:{...pkg,name:'wrong-package'}}),/package/i);
  assert.throws(()=>createMarketIndex({...valid,packageJson:{...pkg,scripts:{prepare:'unexpected build'}}}),/script/i);
  assert.throws(()=>createMarketIndex({...valid,packageJson:{...pkg,version:'01.2.3'}}),/package/i);
  assert.throws(()=>createMarketIndex({...valid,packageJson:{...pkg,engines:{dsh:{}}}}),/package/i);
});

test('exported Git package is self-contained and its bundled core persists notes',{skip:!existsSync(resolve('packages/dsh-slipbox/package.json'))},async()=>{
  const base=resolve('packages/dsh-slipbox');
  const metadata=JSON.parse(readFileSync(join(base,'package.json'),'utf8'));
  assert.equal(metadata.name,'dsh-slipbox');
  assert.equal(Object.keys(metadata.scripts||{}).length,0);
  for(const peer of Object.keys(metadata.peerDependencies)) assert.equal(metadata.peerDependenciesMeta[peer].optional,true);
  for(const file of ['index.mjs','bridge.mjs','client.js','cordis.patch.yml','icon.svg','locale/en.json','locale/zh.json','skill/SKILL.md','skill/LICENSE','skill/scripts/slipbox.py','skill/docs/INSTALL.md','skill/docs/capabilities.json']) assert.ok(existsSync(join(base,file)),file);
  const {createBridge}=await import(pathToFileURL(join(base,'bridge.mjs')).href);
  const home=await mkdtemp(join(tmpdir(),'slipbox-market-'));
  try {
    const run=createBridge({python:'python',script:join(base,'skill/scripts/slipbox.py'),home});
    await run({action:'init'}); await run({action:'tag-add',name:'market-test'});
    const card=await run({action:'add',content:'self-contained Git package verification',tags:['market-test']});
    assert.equal((await run({action:'show',id:card.id})).content,card.content);
    assert.equal((await run({action:'search',query:'self-contained'})).count,1);
  } finally {await rm(home,{recursive:true,force:true});}
});
