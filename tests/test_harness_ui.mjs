import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

function mounted(preferences=new Map()) {
  const states=[],refs=[],deps=[];let cursor=0,refCursor=0,effectCursor=0,component,tree;const pending=[];
  const tags=Array.from({length:500},(_,i)=>({name:'标签'+String(i+1).padStart(4,'0')}));
  const writes=[];
  const React={
    createElement:(type,props,...children)=>({type,props:props||{},children:children.flat(Infinity).filter(x=>x!==false&&x!==null&&x!==undefined)}),
    useState(initial){const i=cursor++;if(!(i in states))states[i]=typeof initial==='function'?initial():initial;return [states[i],v=>{states[i]=typeof v==='function'?v(states[i]):v;}];},
    useRef(initial){const i=refCursor++;return refs[i]||(refs[i]={current:initial});},
    useEffect(fn,values){const i=effectCursor++;if(!deps[i]||values.some((v,n)=>v!==deps[i][n])){deps[i]=values;pending.push(fn);}},
  };
  const local=preferences;
  const context={window:{__ModuleLoader__:{load(module){const result=module.factory(()=>React);result.apply({effect(){},slots:{inject(_slot,fn){fn();},register(options,view){if(options.key==='slipbox')component=view;}},sessions:{},uiWorkspace:{}});}}},localStorage:{getItem:k=>local.get(k)||null,setItem:(k,v)=>local.set(k,v)},console,
    fetch:async(_url,options)=>{const input=JSON.parse(options.body);let value={};
      if(input.action==='status')value={library:'synthetic-library'};
      else if(input.action==='tag-list')value={tags};
      else if(input.action==='list'||input.action==='search')value={cards:[],count:0,has_more:false};
      else {writes.push(input);if(input.action==='tag-add')tags.push({name:input.name});value={id:'a'.repeat(32)};}
      return {ok:true,json:async()=>({ok:true,value})};}};
  vm.runInNewContext(readFileSync(new URL('../plugins/dsh-slipbox/client.js',import.meta.url),'utf8'),context);
  function render(){cursor=refCursor=effectCursor=0;tree=component({organize:async()=>{}});for(const fn of pending.splice(0))fn();return tree;}
  function nodes(node=tree){if(!node||typeof node!=='object')return [];return [node,...node.children.flatMap(x=>nodes(x))];}
  function text(node){return typeof node==='object'?node.children.map(text).join(''):String(node??'');}
  function one(predicate){const matches=nodes().filter(predicate);assert.equal(matches.length,1,'Expected one matching element, found '+matches.length);return matches[0];}
  function button(label){return one(n=>n.type==='button'&&(n.props['aria-label']||text(n))===label);}
  function input(label){return one(n=>n.props['aria-label']===label||n.props.id===label);}
  async function settle(){for(let i=0;i<8;i++)await Promise.resolve();render();}
  render();
  return {render,settle,nodes,text,button,input,writes,local};
}

test('500 tags do not flood the homepage; full list is searchable and paginated',async()=>{
  const ui=mounted();await ui.settle();
  assert.ok(ui.nodes().filter(n=>n.type==='button').length<30,'Homepage must not render every tag');
  ui.input('sbx-note').props.onChange({target:{value:'未保存的卡片草稿'}});ui.render();
  ui.button('标签列表').props.onClick();ui.render();
  assert.equal(ui.nodes().filter(n=>n.props.className==='sbx-tag-entry').length,48);
  ui.button('下一页').props.onClick();ui.render();
  assert.ok(ui.text(ui.render()).includes('标签0049'));
  ui.input('搜索标签列表').props.onChange({target:{value:'标签0500'}});ui.render();
  assert.equal(ui.nodes().filter(n=>n.props.className==='sbx-tag-entry').length,1);
  ui.button('查看标签 标签0500 的卡片').props.onClick();await ui.settle();
  assert.equal(ui.input('sbx-note').props.value,'未保存的卡片草稿');
  assert.ok(ui.text(ui.render()).includes('# 标签0500'));
});

test('composer tags are searched on demand, bounded, removable and capped at three',async()=>{
  const ui=mounted();await ui.settle();
  ui.button('添加标签').props.onClick();ui.render();
  ui.input('搜索要添加的标签').props.onChange({target:{value:'标签'}});ui.render();
  assert.ok(ui.nodes().filter(n=>n.props.className==='sbx-tag-option').length<=8);
  for(const name of ['标签0001','标签0002','标签0500']) {
    ui.input('搜索要添加的标签').props.onChange({target:{value:name}});ui.render();
    ui.button('选择标签 '+name).props.onClick();ui.render();
    if(name!=='标签0500'){ui.button('添加标签').props.onClick();ui.render();}
  }
  assert.equal(ui.button('添加标签').props.disabled,true);
  ui.button('移除标签 标签0002').props.onClick();ui.render();
  assert.equal(ui.button('添加标签').props.disabled,false);
  ui.input('sbx-note').props.onChange({target:{value:'卡片正文'}});ui.render();
  const form=ui.nodes().find(n=>n.props.className==='sbx-compose');
  await form.props.onSubmit({preventDefault(){}});await ui.settle();
  const saved=ui.writes.find(x=>x.action==='add');
  assert.deepEqual(saved.tags,['标签0001','标签0500']);
  assert.equal(saved.content,'卡片正文');
});

test('Enter in the tag picker selects an exact result without submitting the draft',async()=>{
  const ui=mounted();await ui.settle();
  ui.input('sbx-note').props.onChange({target:{value:'仍在编辑，不应自动保存'}});ui.render();
  ui.button('添加标签').props.onClick();ui.render();
  ui.input('搜索要添加的标签').props.onChange({target:{value:'标签0500'}});ui.render();
  let prevented=false;
  ui.input('搜索要添加的标签').props.onKeyDown?.({key:'Enter',preventDefault(){prevented=true;}});
  assert.equal(prevented,true,'Picker Enter must block implicit form submission');
  ui.render();
  assert.ok(ui.button('移除标签 标签0500'));
  assert.equal(ui.writes.length,0);
  assert.equal(ui.input('sbx-note').props.value,'仍在编辑，不应自动保存');
});

test('Chinese naming is default; language switching preserves drafts, tags and search state',async()=>{
  const ui=mounted();await ui.settle();
  assert.equal(ui.text(ui.nodes().find(n=>n.type==='h1')),'卡片笔记');
  assert.ok(ui.button('我的笔记'));
  ui.input('sbx-note').props.onChange({target:{value:'保留原始中文笔记'}});ui.render();
  ui.input('搜索卡片').props.onChange({target:{value:'原始查询'}});ui.render();await ui.settle();
  ui.button('添加标签').props.onClick();ui.render();
  ui.input('搜索要添加的标签').props.onChange({target:{value:'标签0500'}});ui.render();
  ui.button('选择标签 标签0500').props.onClick();ui.render();
  ui.button('English').props.onClick();ui.render();
  assert.equal(ui.text(ui.nodes().find(n=>n.type==='h1')),'slipbox · Card Notes');
  assert.ok(ui.button('My Notes'));
  assert.equal(ui.input('sbx-note').props.value,'保留原始中文笔记');
  assert.equal(ui.input('Search notes').props.value,'原始查询');
  assert.ok(ui.button('Remove tag 标签0500'));
  assert.equal(ui.local.get('slipbox.plugin.language'),'en');
  assert.equal(ui.writes.length,0);
  ui.button('Tags').props.onClick();ui.render();
  assert.equal(ui.nodes().filter(n=>n.props.className==='sbx-tag-entry').length,48);
  ui.button('简体中文').props.onClick();ui.render();
  assert.ok(ui.button('我的笔记'));assert.equal(ui.local.get('slipbox.plugin.language'),'zh');
});

test('saved English preference is restored without translating note or tag data',async()=>{
  const ui=mounted(new Map([['slipbox.plugin.language','en']]));await ui.settle();
  assert.equal(ui.text(ui.nodes().find(n=>n.type==='h1')),'slipbox · Card Notes');
  ui.button('Add tag').props.onClick();ui.render();
  ui.input('Search tags to add').props.onChange({target:{value:'标签0500'}});ui.render();
  assert.ok(ui.button('Choose tag 标签0500'));
  assert.equal(ui.writes.length,0);
});
