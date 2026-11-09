import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const exec = promisify(execFile);
function text(value, name, max, empty = false) {
  if (typeof value !== 'string' || value.includes('\0') || value.length > max || (!empty && !value.trim())) throw new Error(`Invalid ${name}`);
  return value;
}
function tags(values) {
  if (!Array.isArray(values)) throw new Error('Invalid tags: expected an array');
  return values.map(v => '--tag=' + text(v, 'tag', 64));
}
function id(value) {
  if (typeof value !== 'string' || !/^[a-f0-9]{32}$/.test(value)) throw new Error('Invalid card id');
  return value;
}
export function makeArgs(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Invalid action');
  let args, positional = [];
  switch (input.action) {
    case 'init': case 'tag-list': case 'tag-stats': args = [input.action]; break;
    case 'activity': {
      const days=input.days??84;
      if(!Number.isInteger(days)||days<1||days>366)throw new Error('Invalid activity days');
      args=['activity','--days',String(days)];break;
    }
    case 'list': case 'search': case 'search-candidates': {
      const limit = input.limit ?? (input.action==='search-candidates'?30:50), offset = input.offset ?? 0;
      if (!Number.isInteger(limit) || limit < 1 || limit > 100 || !Number.isInteger(offset) || offset < 0) throw new Error('Invalid pagination');
      args = [input.action];
      if(input.action==='search-candidates'){if(!Array.isArray(input.terms)||input.terms.length<1||input.terms.length>6||limit>40)throw new Error('Invalid retrieval terms');args.push(...input.terms.map(term=>'--term='+text(term,'term',80)));}
      for(const [field,option] of [['createdFrom','created-from'],['createdTo','created-to']])if(input[field]){if(typeof input[field]!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(input[field]))throw new Error('Invalid date');args.push('--'+option+'='+input[field]);}
      if (input.action === 'search') positional.push(text(input.query, 'query', 1000));
      if (input.tag) args.push('--tag=' + text(input.tag, 'tag', 64));
      if(input.createdOn){if(typeof input.createdOn!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(input.createdOn))throw new Error('Invalid date');args.push('--created-on='+input.createdOn);}
      args.push('--limit',String(limit));if(input.action!=='search-candidates')args.push('--offset',String(offset));break;
    }
    case 'show': args = ['show']; positional=[id(input.id)]; break;
    case 'delete': {
      if(input.confirmed!==true)throw new Error('Confirm deletion first');
      args=['delete','--expected='+text(input.expected,'expected',100)];positional=[id(input.id)];break;
    }
    case 'add': args = ['add', ...tags(input.tags ?? [])]; positional=[text(input.content, 'content', 20000)]; break;
    case 'edit': {
      const options = input.tags === undefined ? [] : tags(input.tags);
      args = ['edit', ...(input.tags !== undefined && options.length === 0 ? ['--clear-tags'] : options)];
      positional=[id(input.id),text(input.content, 'content', 20000)]; break;
    }
    case 'tag-add': args = ['tag-add', '--description=' + text(input.description ?? '', 'description', 1000, true)]; positional=[text(input.name, 'tag name', 64)]; break;
    case 'apply-card-tags': {
      if (!Array.isArray(input.definitions)) throw new Error('Invalid definitions');
      args = ['apply-card-tags', '--expected=' + text(input.expected, 'expected', 100), ...tags(input.tags), '--definitions-json=' + JSON.stringify(input.definitions)];
      positional = [id(input.id)]; break;
    }
    case 'tag-update': {
      if (!Array.isArray(input.aliases) || input.aliases.length > 12 || !input.expected || typeof input.expected !== 'object') throw new Error('Invalid metadata');
      args = ['tag-update', '--description=' + text(input.description, 'description', 1000, true), '--expected-json=' + JSON.stringify(input.expected), ...input.aliases.map(a=>'--alias='+text(a,'alias',64))];
      positional = [text(input.name,'tag name',64)]; break;
    }
    case 'tag-merge': args=['tag-merge']; positional=[text(input.source,'source tag',64),text(input.target,'target tag',64)]; break;
    default: throw new Error('Unsupported action');
  }
  return [...args, '--json', ...(positional.length ? ['--', ...positional] : [])];
}
export const renderToolResult = (_args, result) => [{ type:'text',text:result }];
export function createBridge({ python = 'python', script, home }) {
  if (!script || !home) throw new Error('Missing script or library path');
  return async input => {
    const args = makeArgs(input);
    try {
      const { stdout } = await exec(python, [script, ...args], {
        env: { ...process.env, SLIPBOX_HOME: home, PYTHONIOENCODING: 'utf-8' },
        encoding: 'utf8', windowsHide: true, timeout: 30000, maxBuffer: 16 * 1024 * 1024,
        shell: false,
      });
      return JSON.parse(stdout);
    } catch (error) {
      let message = 'slipbox command failed';
      try { const data = JSON.parse(error.stdout || error.stderr); message = data.error ?? message; } catch { if (error.code === 'ENOENT') message = 'Python executable not found; configure the plugin Python path'; }
      throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
    }
  };
}
