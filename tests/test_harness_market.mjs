import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
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
});
