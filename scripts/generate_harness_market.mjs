import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export function createMarketIndex({commit,publishTimestamp,packageJson:pkg}) {
  if(typeof commit!=='string'|| !/^[a-f0-9]{40}$/.test(commit)) throw new Error('Expected full lowercase Git commit SHA');
  if(!Number.isSafeInteger(publishTimestamp)||publishTimestamp<=0) throw new Error('Expected positive integer publish timestamp');
  if(pkg?.name!=='dsh-slipbox'|| typeof pkg.version!=='string'|| !/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(pkg.version)|| typeof pkg.dsh?.bundle?.patch!=='string'|| !pkg.dsh.bundle.patch || typeof pkg.engines?.dsh!=='string'|| !pkg.engines.dsh.trim()) throw new Error('Invalid native package metadata');
  if(Object.keys(pkg.scripts||{}).length) throw new Error('Market package must not require lifecycle scripts');
  return {
    format:1,
    title:{en:'slipbox plugins',zh:'slipbox 插件市场'},
    description:{en:'AI-powered card notes across agents. Install directly from a pinned GitHub commit.',zh:'用 AI 整理卡片笔记，持续积累，跨智能体复用。从固定 GitHub 提交安装。'},
    plugins:[{
      name:pkg.name,
      title:{en:'slipbox | AI-powered card notes across agents',zh:'slipbox｜跨智能体的 AI 卡片笔记'},
      description:{en:'A permanent card-note page, local Markdown storage, tags, search and AI assistance from your Harness default model.',zh:'常驻卡片笔记页面，本地 Markdown 存储、标签整理、搜索与宿主默认模型 AI 助力。'},
      icon:'icon.svg',author:'slipbox contributors',
      homepage:'https://github.com/xinyou9999/slipbox-skill/blob/main/docs/HARNESS_PLUGIN.md',
      repository:{url:'https://github.com/xinyou9999/slipbox-skill',directory:'packages/dsh-slipbox'},
      versions:[{version:pkg.version,publishTimestamp,engines:{dsh:pkg.engines.dsh},source:{type:'git',url:'https://github.com/xinyou9999/slipbox-skill',commit,path:'packages/dsh-slipbox'}}],
    }],
  };
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
  const [commit,timestamp,output]=process.argv.slice(2);
  const pkg=JSON.parse(await readFile(join(root,'plugins/dsh-slipbox/package.json'),'utf8'));
  const index=createMarketIndex({commit,publishTimestamp:Number(timestamp),packageJson:pkg});
  if(!output) throw new Error('Usage: node scripts/generate_harness_market.mjs <full-public-package-commit> <Unix-seconds> <output-path>');
  const target=resolve(output);
  await mkdir(dirname(target),{recursive:true});
  await writeFile(target,JSON.stringify(index,null,2)+'\n');
  console.log(target);
}
