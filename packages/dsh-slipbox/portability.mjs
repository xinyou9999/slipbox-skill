// Browser file data is bounded and staged privately; caller paths are never accepted.
import {mkdtemp,writeFile,readFile,rm,chmod} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
const exec=promisify(execFile);
const MAX=10*1024*1024;
export function createPortability({python='python',script,home}){
  if(!script||!home)throw new Error('Missing library settings');
  return async input=>{
    if(!input||!['export','import-preview','import-apply'].includes(input.action))throw new Error('Unsupported file action');
    const dir=await mkdtemp(join(tmpdir(),'slipbox-transfer-'));
    try{
      await chmod(dir,0o700);
      let args,outfile;
      if(input.action==='export'){
        if(!['backup','context','markdown','json'].includes(input.format))throw new Error('Invalid export format');
        if(input.ids!==undefined&&(!Array.isArray(input.ids)||input.ids.length>500||input.ids.some(x=>typeof x!=='string'||!/^[a-f0-9]{32}$/.test(x))))throw new Error('Invalid selected notes');
        if(input.format==='context'&&!input.ids?.length)throw new Error('Select notes to export');
        outfile=join(dir,input.format==='backup'||input.format==='json'?'notes.json':'notes.md');
        args=['export','--format',input.format,'--output',outfile,...(input.ids||[]).map(x=>'--id='+x),'--json'];
      }else{
        if(typeof input.content!=='string'||input.content.length>Math.ceil(MAX/3)*4||!input.content.length||input.content.length%4!==0||!/^[A-Za-z0-9+/]*={0,2}$/.test(input.content))throw new Error('Choose a valid file up to10 MiB');
        const bytes=Buffer.from(input.content,'base64');
        if(!bytes.length||bytes.length>MAX||bytes.toString('base64')!==input.content)throw new Error('Invalid file encoding or size');
        const ext=typeof input.filename==='string'?input.filename.toLowerCase().match(/\.(json|html?|zip)$/)?.[0]:null;
        if(!ext)throw new Error('Choose a JSON, HTML or ZIP file');
        const source=join(dir,'input'+ext);await writeFile(source,bytes,{mode:0o600,flag:'wx'});
        const format=input.format||'auto';if(!['auto','slipbox','flomo'].includes(format))throw new Error('Invalid import format');
        args=[input.action,'--format',format,'--json','--',source];
        if(input.action==='import-apply'){
          if(input.confirmed!==true||typeof input.digest!=='string'||!/^[a-f0-9]{64}$/.test(input.digest))throw new Error('Preview and confirm import first');
          args=[input.action,'--format',format,'--digest',input.digest,'--json','--',source];
        }
      }
      let result;
      try{const {stdout}=await exec(python,[script,...args],{env:{...process.env,SLIPBOX_HOME:home,PYTHONIOENCODING:'utf-8'},encoding:'utf8',windowsHide:true,shell:false,timeout:60000,maxBuffer:16*1024*1024});result=JSON.parse(stdout);}
      catch(error){let message='File operation failed';try{message=JSON.parse(error.stdout||error.stderr).error||message;}catch{}throw new Error(String(message));}
      if(outfile){const content=await readFile(outfile);if(content.length>MAX)throw new Error('Export exceeds10 MiB; select fewer notes');return {filename:'slipbox-'+input.format+(outfile.endsWith('.json')?'.json':'.md'),content:content.toString('base64'),mime:outfile.endsWith('.json')?'application/json':'text/markdown',count:result.count,sha256:result.sha256};}
      return result;
    }finally{await rm(dir,{recursive:true,force:true});}
  };
}
