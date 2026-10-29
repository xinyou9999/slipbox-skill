import { mkdir, readFile, writeFile, copyFile, mkdtemp } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
await mkdir(join(root,'.local-release'),{recursive:true});
const stage = process.argv[2] ? resolve(process.argv[2]) : await mkdtemp(join(root,'.local-release/harness-plugin-'));
if(process.argv[2]) await mkdir(stage, { recursive: false });
const files = ['package.json', 'index.mjs', 'bridge.mjs', 'client.js', 'icon.svg', 'cordis.patch.yml', 'README.md', 'locale/zh.json', 'locale/en.json'];
for (const file of files) {
  await mkdir(dirname(join(stage,file)),{recursive:true});
  await copyFile(join(root,'plugins/dsh-slipbox',file),join(stage,file));
}
const pkg = JSON.parse(await readFile(join(stage,'package.json'),'utf8'));
// Hosts supply these runtime peers; installing a local tarball never downloads SDK copies.
pkg.peerDependenciesMeta = Object.fromEntries(Object.keys(pkg.peerDependencies).map(k => [k,{optional:true}]));
await writeFile(join(stage,'package.json'),JSON.stringify(pkg,null,2)+'\n');
const core = ['SKILL.md','LICENSE','scripts/slipbox.py','references/data-format.md','references/tagging-policy.md','templates/tags.example.json','docs/INSTALL.md','docs/QUICKSTART.md','docs/AI_INSTALL.md','docs/capabilities.json'];
for (const file of core) {
  await mkdir(dirname(join(stage,'skill',file)),{recursive:true});
  await copyFile(join(root,file),join(stage,'skill',file));
}
// Static pack command only: no user content is interpolated into a shell string.
const command=process.platform==='win32'?'cmd.exe':'npm';
const args=process.platform==='win32'?['/d','/s','/c','npm.cmd pack --ignore-scripts --json']:['pack','--ignore-scripts','--json'];
const packed=JSON.parse(execFileSync(command,args,{cwd:stage,encoding:'utf8',windowsHide:true}));
console.log(join(stage,packed[0].filename));
