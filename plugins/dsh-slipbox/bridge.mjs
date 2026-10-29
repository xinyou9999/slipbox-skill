import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const exec = promisify(execFile);
function text(value, name, max, empty = false) {
  if (typeof value !== 'string' || value.includes('\0') || value.length > max || (!empty && !value.trim())) throw new Error(`Invalid ${name}`);
  return value;
}
function tags(values) {
  if (!Array.isArray(values) || values.length > 3) throw new Error('Invalid tags: at most 3');
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
    case 'list': case 'search': {
      const limit = input.limit ?? 50, offset = input.offset ?? 0;
      if (!Number.isInteger(limit) || limit < 1 || limit > 100 || !Number.isInteger(offset) || offset < 0) throw new Error('Invalid pagination');
      args = [input.action];
      if (input.action === 'search') positional.push(text(input.query, 'query', 1000));
      if (input.tag) args.push('--tag=' + text(input.tag, 'tag', 64));
      args.push('--limit', String(limit), '--offset', String(offset)); break;
    }
    case 'show': args = ['show']; positional=[id(input.id)]; break;
    case 'add': args = ['add', ...tags(input.tags ?? [])]; positional=[text(input.content, 'content', 20000)]; break;
    case 'edit': {
      const options = input.tags === undefined ? [] : tags(input.tags);
      args = ['edit', ...(input.tags !== undefined && options.length === 0 ? ['--clear-tags'] : options)];
      positional=[id(input.id),text(input.content, 'content', 20000)]; break;
    }
    case 'tag-add': args = ['tag-add', '--description=' + text(input.description ?? '', 'description', 1000, true)]; positional=[text(input.name, 'tag name', 64)]; break;
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
