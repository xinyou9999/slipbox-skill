import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

function mounted(preferences=new Map(), options={}) {
  const states=[],refs=[],deps=[],themeListeners=[];let cursor=0,refCursor=0,effectCursor=0,component,tree,pageProps={};const pending=[];
  const tags=Array.from({length:500},(_,i)=>({name:'标签'+String(i+1).padStart(4,'0')}));
  const writes=[],requests=[];
  const cards=[];
  const React={
    createElement:(type,props,...children)=>({type,props:props||{},children:children.flat(Infinity).filter(x=>x!==false&&x!==null&&x!==undefined)}),
    useState(initial){const i=cursor++;if(!(i in states))states[i]=typeof initial==='function'?initial():initial;return [states[i],v=>{states[i]=typeof v==='function'?v(states[i]):v;}];},
    useRef(initial){const i=refCursor++;return refs[i]||(refs[i]={current:initial});},
    useEffect(fn,values){const i=effectCursor++;if(!deps[i]||values.some((v,n)=>v!==deps[i][n])){deps[i]=values;pending.push(fn);}},
  };
  const local=preferences;
  const context={window:{__ModuleLoader__:{load(module){const result=module.factory(()=>React);result.apply({effect(){},theme:options.hostTheme,on(event,listener){if(event==='theme/change')themeListeners.push(listener);return()=>{};},slots:{inject(_slot,fn){fn();},register(options,view){if(options.key==='slipbox'){component=view;pageProps=options.inject?.()||{};}}},sessions:{},uiWorkspace:{}});}}},localStorage:{getItem:k=>local.get(k)||null,setItem:(k,v)=>local.set(k,v)},console,AbortController,
    fetch:async(_url,requestOptions)=>{const input=JSON.parse(requestOptions.body);requests.push(input);let value={};
      if(input.action==='status')value={library:'synthetic-library',version:options.version||'0.1.13'};
      else if(input.action==='tag-list')value={tags};
      else if(input.action==='activity'){if(options.activityFails)throw new Error('activity unavailable');value={start:'2026-11-06',end:'2026-11-08',total:3,active_days:2,days:[{date:'2026-11-06',count:1},{date:'2026-11-07',count:0},{date:'2026-11-08',count:2}]};}
      else if(input.action==='ai-search'){if(options.aiSearch)value=await options.aiSearch(input);else value={cards:[],reasons:{},count:0,candidate_count:0,matched_total:0,terms:['sleep']};}
      else if(input.action==='list'||input.action==='search')value={cards:[...cards],count:cards.length,has_more:false};
      else {writes.push(input);
        if(input.action==='tag-add'){tags.push({name:input.name});value={name:input.name};}
        else if(input.action==='add'||input.action==='edit'){value={id:input.id||'a'.repeat(32),updated_at:'2026-11-07T01:00:00Z',content:input.content,tags:input.tags};cards.unshift(value);}
        else if(input.action==='ai-tag')value=options.tag?await options.tag(input):{applied:true,card:cards[0]};
        else if(input.action==='ai-maintain')value=options.maintenance||{updates:[],merges:[]};
        else if(input.action==='delete'){const i=cards.findIndex(c=>c.id===input.id);if(i>=0)cards.splice(i,1);value={deleted:i>=0,id:input.id};}
      }
      return {ok:true,json:async()=>({ok:true,value})};}};
  vm.runInNewContext(readFileSync(new URL('../plugins/dsh-slipbox/client.js',import.meta.url),'utf8'),context);
  function render(){cursor=refCursor=effectCursor=0;tree=component(pageProps);for(const fn of pending.splice(0))fn();return tree;}
  function nodes(node=tree){if(!node||typeof node!=='object')return [];return [node,...node.children.flatMap(x=>nodes(x))];}
  function text(node){return typeof node==='object'?node.children.map(text).join(''):String(node??'');}
  function one(predicate){const matches=nodes().filter(predicate);assert.equal(matches.length,1,'Expected one matching element, found '+matches.length);return matches[0];}
  function button(label){return one(n=>n.type==='button'&&(n.props['aria-label']||text(n))===label);}
  function input(label){return one(n=>n.props['aria-label']===label||n.props.id===label);}
  async function settle(){for(let i=0;i<4;i++){for(let j=0;j<8;j++)await Promise.resolve();render();}}
  render();
  return {render,settle,nodes,text,button,input,writes,requests,local,themeListeners};
}

test('AI search is explicit, discloses excerpts, preserves draft and invalidates late results',async()=>{
  let resolve;const ui=mounted(new Map(),{aiSearch:()=>new Promise(r=>{resolve=r;})});await ui.settle();
  ui.input('sbx-note').props.onChange({target:{value:'草稿仍然在'}});ui.render();
  ui.button('AI 智能搜索').props.onClick();ui.render();await ui.settle();
  assert.ok(ui.text(ui.render()).includes('候选笔记片段'));
  ui.input('搜索卡片').props.onChange({target:{value:'晚上怎么放松'}});ui.render();await ui.settle();
  assert.equal(ui.requests.filter(r=>r.action==='ai-search').length,0);
  ui.nodes().find(n=>n.type==='form'&&n.props.className==='sbx-search-form').props.onSubmit({preventDefault(){}});ui.render();await ui.settle();
  assert.equal(ui.requests.filter(r=>r.action==='ai-search').length,1);
  ui.button('普通搜索').props.onClick();ui.render();await ui.settle();
  resolve({cards:[{id:'a'.repeat(32),content:'late AI result',tags:[],updated_at:'2026-11-09T00:00:00Z'}],count:1,reasons:{}});await ui.settle();
  assert.ok(!ui.text(ui.render()).includes('late AI result'));
  assert.equal(ui.input('sbx-note').props.value,'草稿仍然在');
  ui.input('开始日期').props.onChange({target:{value:'2026-01-01'}});ui.render();await ui.settle();
  assert.equal(ui.requests.filter(r=>r.action==='list').at(-1).createdFrom,'2026-01-01');
});

test('AI search errors keep ordinary search usable',async()=>{const ui=mounted(new Map(),{aiSearch:()=>{throw new Error('AI_TIMEOUT');}});await ui.settle();ui.button('AI 智能搜索').props.onClick();ui.render();ui.input('搜索卡片').props.onChange({target:{value:'test'}});ui.render();ui.nodes().find(n=>n.type==='form'&&n.props.className==='sbx-search-form').props.onSubmit({preventDefault(){}});await ui.settle();assert.ok(ui.text(ui.render()).includes('智能搜索暂未完成'));ui.button('普通搜索').props.onClick();ui.render();ui.input('搜索卡片').props.onChange({target:{value:'literal'}});ui.render();await ui.settle();assert.equal(ui.requests.filter(r=>r.action==='search').at(-1).query,'literal');});
test('refresh clears prior AI cards without reuploading and submit names expected library',async()=>{const ui=mounted(new Map(),{aiSearch:async()=>({cards:[{id:'a'.repeat(32),content:'old AI card',tags:[],updated_at:'2026-11-09T00:00:00Z'}],reasons:{},count:1})});await ui.settle();ui.button('AI 智能搜索').props.onClick();ui.render();ui.input('搜索卡片').props.onChange({target:{value:'test'}});ui.render();ui.nodes().find(n=>n.type==='form'&&n.props.className==='sbx-search-form').props.onSubmit({preventDefault(){}});await ui.settle();assert.ok(ui.text(ui.render()).includes('old AI card'));assert.equal(ui.requests.filter(r=>r.action==='ai-search').at(-1).library,'synthetic-library');ui.button('刷新').props.onClick();await ui.settle();assert.ok(!ui.text(ui.render()).includes('old AI card'));assert.equal(ui.requests.filter(r=>r.action==='ai-search').length,1);});

test('prominent calendar precedes content and range switching preserves a draft',async()=>{
  const ui=mounted();await ui.settle();
  const inner=ui.nodes().find(n=>n.props.className==='sbx-inner');
  const activity=inner.children.findIndex(n=>n.props?.className==='sbx-activity');
  const grid=inner.children.findIndex(n=>n.props?.className==='sbx-grid');
  assert.ok(activity>=0&&activity<grid,'Calendar must be a full-width section above notes, outside sidebar');
  assert.equal(ui.requests.filter(r=>r.action==='activity').at(-1).days,365);
  ui.input('sbx-note').props.onChange({target:{value:'不要丢掉这个草稿'}});ui.render();
  ui.button('近 12 周').props.onClick();ui.render();await ui.settle();
  assert.equal(ui.requests.filter(r=>r.action==='activity').at(-1).days,84);
  assert.equal(ui.input('sbx-note').props.value,'不要丢掉这个草稿');
  ui.button('近一年').props.onClick();ui.render();await ui.settle();
  assert.equal(ui.requests.filter(r=>r.action==='activity').at(-1).days,365);
});

test('calendar days filter notes without losing a draft and support keyboard navigation',async()=>{
  const ui=mounted();await ui.settle();
  assert.ok(ui.text(ui.render()).includes('记录足迹'));
  ui.input('sbx-note').props.onChange({target:{value:'保留未保存的草稿'}});ui.render();
  ui.button('2026-11-08，新增 2 条笔记').props.onClick();ui.render();await ui.settle();
  assert.equal(ui.input('sbx-note').props.value,'保留未保存的草稿');
  assert.equal(ui.requests.filter(r=>r.action==='list').at(-1).createdOn,'2026-11-08');
  const day=ui.button('2026-11-07，新增 0 条笔记');let focused=false;
  ui.button('2026-11-08，新增 2 条笔记').props.ref({focus(){focused=true;}});
  day.props.onKeyDown({key:'ArrowDown',preventDefault(){}});ui.render();
  assert.equal(focused,true);
  const picker=ui.input('按日期查看笔记');
  assert.equal(picker.props.type,'date');
  picker.props.onChange({target:{value:'2025-01-01'}});ui.render();await ui.settle();
  assert.equal(ui.requests.filter(r=>r.action==='list').at(-1).createdOn,'2025-01-01');
  assert.equal(ui.nodes().filter(n=>n.props.className==='sbx-day'&&n.props.tabIndex===0).length,1);
  assert.equal(ui.input('sbx-note').props.value,'保留未保存的草稿');
  ui.button('清除日期筛选').props.onClick();ui.render();await ui.settle();
  assert.equal(ui.requests.filter(r=>r.action==='list').at(-1).createdOn,'');
});

test('activity failures leave the note workflow usable',async()=>{
  const ui=mounted(new Map(),{activityFails:true});await ui.settle();
  assert.ok(ui.button('记录笔记'));
  assert.ok(ui.text(ui.render()).includes('暂时无法读取记录足迹'));
});

test('native appearance follows the host and switches through its theme service without losing the draft',async()=>{
  let scheme='dark';const calls=[];
  const hostTheme={getTheme:()=>({active:{colorScheme:scheme}}),setTheme:value=>{calls.push(value);scheme=value;}};
  const prefs=new Map([['slipbox.plugin.theme','light']]);
  const ui=mounted(prefs,{hostTheme});await ui.settle();
  assert.equal(ui.nodes().find(n=>n.props.className==='sbx').props['data-theme'],'night');
  ui.input('sbx-note').props.onChange({target:{value:'Preserve this draft'}});ui.render();
  ui.button('浅色模式').props.onClick();ui.render();
  assert.deepEqual(calls,['light']);
  assert.equal(ui.nodes().find(n=>n.props.className==='sbx').props['data-theme'],'light');
  scheme='dark';ui.themeListeners.forEach(fn=>fn({active:{colorScheme:scheme}}));ui.render();
  assert.equal(ui.nodes().find(n=>n.props.className==='sbx').props['data-theme'],'night');
  assert.equal(ui.input('sbx-note').props.value,'Preserve this draft');
  assert.equal(ui.writes.length,0);
});

test('many inline/manual tags can be saved and AI still runs; card ids stay out of visible copy',async()=>{
  const ui=mounted();await ui.settle();
  ui.input('sbx-note').props.onChange({target:{value:'记下思考 '+Array.from({length:12},(_,i)=>'#标签'+String(i+1).padStart(4,'0')).join(' ')}});ui.render();
  assert.equal(ui.button('添加标签').props.disabled,false);
  await ui.nodes().find(n=>n.props.className==='sbx-compose').props.onSubmit({preventDefault(){}});await ui.settle();
  assert.equal(ui.writes.find(x=>x.action==='add').tags.length,12);
  assert.equal(ui.writes.filter(x=>x.action==='ai-tag').length,1);
  const card=ui.nodes().find(n=>n.type==='article');
  assert.ok(!ui.text(card).includes('aaaaaaaa'));
});

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

test('composer tags are searched on demand, bounded in search results and removable without a note tag cap',async()=>{
  const ui=mounted();await ui.settle();
  ui.button('添加标签').props.onClick();ui.render();
  ui.input('搜索要添加的标签').props.onChange({target:{value:'标签'}});ui.render();
  assert.ok(ui.nodes().filter(n=>n.props.className==='sbx-tag-option').length<=8);
  for(const name of ['标签0001','标签0002','标签0500']) {
    ui.input('搜索要添加的标签').props.onChange({target:{value:name}});ui.render();
    ui.button('选择标签 '+name).props.onClick();ui.render();
    if(name!=='标签0500'){ui.button('添加标签').props.onClick();ui.render();}
  }
  assert.equal(ui.button('添加标签').props.disabled,false);
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

test('inline hashtags become manual tags without interpreting headings, code, URLs or C#',async()=>{
  const ui=mounted();await ui.settle();
  const content='思考 #标签0001 #新主题\n# Markdown 标题\nC# https://example.test/#anchor `#inline`\n```js\n#code\n```';
  ui.input('sbx-note').props.onChange({target:{value:content}});ui.render();
  assert.ok(ui.button('移除标签 标签0001'));
  await ui.nodes().find(n=>n.props.className==='sbx-compose').props.onSubmit({preventDefault(){}});await ui.settle();
  assert.deepEqual(ui.writes.find(x=>x.action==='add').tags,['标签0001','新主题']);
  assert.equal(ui.writes.find(x=>x.action==='add').content,content);
  assert.equal(ui.writes.filter(x=>x.action==='tag-add').length,1);
});

test('removing an inline tag also removes its source token and button picker creates a new tag',async()=>{
  const ui=mounted();await ui.settle();
  ui.input('sbx-note').props.onChange({target:{value:'原文 #标签0001'}});ui.render();
  ui.button('移除标签 标签0001').props.onClick();ui.render();
  assert.equal(ui.input('sbx-note').props.value.trim(),'原文');
  ui.button('添加标签').props.onClick();ui.render();
  ui.input('搜索要添加的标签').props.onChange({target:{value:'按钮新标签'}});ui.render();
  await ui.button('创建并添加 #按钮新标签').props.onClick();await ui.settle();
  assert.ok(ui.button('移除标签 按钮新标签'));
});

test('save-first AI runs in background, leaves next draft editable and supports failure retry',async()=>{
  let fail;const pending=new Promise((_resolve,reject)=>{fail=reject;});
  const ui=mounted(new Map(),{tag:()=>pending});await ui.settle();
  ui.input('sbx-note').props.onChange({target:{value:'第一条笔记'}});ui.render();
  await ui.nodes().find(n=>n.props.className==='sbx-compose').props.onSubmit({preventDefault(){}});await ui.settle();
  assert.equal(ui.input('sbx-note').props.disabled,false);
  assert.equal(ui.input('sbx-note').props.value,'');
  assert.equal(ui.writes.filter(x=>x.action==='ai-tag').length,1);
  ui.input('sbx-note').props.onChange({target:{value:'下一条草稿'}});ui.render();
  fail(new Error('model offline'));await ui.settle();
  assert.equal(ui.input('sbx-note').props.value,'下一条草稿');
  assert.ok(ui.button('重试 AI 标签'));
});

test('auto-tag switch is remembered for this library and respects an explicit off state',async()=>{
  const prefs=new Map([['slipbox.plugin.autoTags:synthetic-library','off']]);
  const ui=mounted(prefs);await ui.settle();
  assert.equal(ui.input('自动 AI 标签').props.checked,false);
  ui.input('sbx-note').props.onChange({target:{value:'只保存在本地'}});ui.render();
  await ui.nodes().find(n=>n.props.className==='sbx-compose').props.onSubmit({preventDefault(){}});await ui.settle();
  assert.equal(ui.writes.filter(x=>x.action==='ai-tag').length,0);
});

test('AI vocabulary suggestions require explicit apply and merges require a second confirmation',async()=>{
  const suggestion={name:'标签0001',aliases:['别名'],description:'更清楚的定义',expected:{name:'标签0001',aliases:[],description:''}};
  const ui=mounted(new Map(),{maintenance:{updates:[suggestion],merges:[{source:'标签0002',target:'标签0001',reason:'含义相同'}]}});await ui.settle();
  ui.button('标签列表').props.onClick();ui.render();
  await ui.button('AI 整理标签库').props.onClick();await ui.settle();
  assert.equal(ui.writes.filter(x=>x.action==='tag-update'||x.action==='tag-merge').length,0);
  await ui.button('应用建议 标签0001').props.onClick();await ui.settle();
  assert.equal(ui.writes.filter(x=>x.action==='tag-update').length,1);
  ui.button('合并标签 标签0002 → 标签0001').props.onClick();ui.render();
  assert.equal(ui.writes.filter(x=>x.action==='tag-merge').length,0);
  await ui.button('确认合并').props.onClick();await ui.settle();
  assert.equal(ui.writes.filter(x=>x.action==='tag-merge').length,1);
});

test('inline completion replaces the third partial tag instead of counting it as a fourth',async()=>{
  const ui=mounted();await ui.settle();
  for(const name of ['标签0001','标签0002']){
    ui.button('添加标签').props.onClick();ui.render();
    ui.input('搜索要添加的标签').props.onChange({target:{value:name}});ui.render();
    ui.button('选择标签 '+name).props.onClick();ui.render();
  }
  ui.input('sbx-note').props.onChange({target:{value:'draft #050'}});ui.render();
  ui.button('选择标签 标签0500').props.onClick();ui.render();
  assert.ok(ui.input('sbx-note').props.value.includes('#标签0500'));
  assert.ok(ui.button('移除标签 标签0500'));
  assert.ok(!ui.nodes().some(n=>n.props['aria-label']==='移除标签 050'));
});

test('inline completion of a spaced canonical name preserves the full selected tag',async()=>{
  const ui=mounted();await ui.settle();
  ui.button('标签列表').props.onClick();ui.render();
  ui.button('新建标签').props.onClick();ui.render();
  ui.input('sbx-new-tag').props.onChange({target:{value:'Machine Learning'}});ui.render();
  await ui.nodes().find(n=>n.type==='form'&&n.props.className==='sbx-create').props.onSubmit({preventDefault(){}});await ui.settle();
  ui.button('我的笔记').props.onClick();ui.render();
  ui.input('sbx-note').props.onChange({target:{value:'draft #Mach'}});ui.render();
  ui.button('选择标签 Machine Learning').props.onClick();ui.render();
  assert.ok(ui.button('移除标签 Machine Learning'));
  assert.ok(!ui.nodes().some(n=>n.props['aria-label']==='移除标签 Machine'));
  await ui.nodes().find(n=>n.props.className==='sbx-compose').props.onSubmit({preventDefault(){}});await ui.settle();
  assert.deepEqual(ui.writes.find(x=>x.action==='add').tags,['Machine Learning']);
});

test('card action icons expose names and deletion requires confirmation or can be cancelled',async()=>{
  const ui=mounted(new Map([['slipbox.plugin.autoTags:synthetic-library','off']]));await ui.settle();
  ui.input('sbx-note').props.onChange({target:{value:'Synthetic card to delete'}});ui.render();
  await ui.nodes().find(n=>n.props.className==='sbx-compose').props.onSubmit({preventDefault(){}});await ui.settle();
  for(const label of ['编辑','删除笔记']){const action=ui.button(label);assert.equal(action.props.title,label);assert.ok(action.children.some(n=>n.type==='svg'));}
  let restoredFocus=false;
  ui.button('删除笔记').props.onClick({currentTarget:{focus(){restoredFocus=true;}}});ui.render();
  assert.equal(ui.writes.filter(x=>x.action==='delete').length,0);
  assert.ok(ui.text(ui.render()).includes('删除后无法恢复'));
  const confirm=ui.nodes().find(n=>n.props.className==='sbx-delete-confirm');
  let escaped=false;confirm.props.onKeyDown({key:'Escape',preventDefault(){escaped=true;}});ui.render();
  assert.equal(escaped,true);
  assert.equal(restoredFocus,true);
  assert.ok(!ui.nodes().some(n=>n.props.className==='sbx-delete-confirm'));
  ui.button('删除笔记').props.onClick();ui.render();
  ui.button('取消').props.onClick();ui.render();
  assert.equal(ui.nodes().filter(n=>n.props.className==='sbx-card').length,1);
  ui.button('删除笔记').props.onClick();ui.render();
  await ui.button('确认删除').props.onClick();await ui.settle();
  assert.equal(ui.writes.filter(x=>x.action==='delete').length,1);
  assert.equal(ui.writes.find(x=>x.action==='delete').confirmed,true);
  assert.equal(ui.nodes().filter(n=>n.props.className==='sbx-card').length,0);
});

test('an old host backend requests restart and does not submit an unsupported AI call',async()=>{
  const ui=mounted(new Map(),{version:'0.1.5'});await ui.settle();
  assert.ok(ui.text(ui.render()).includes('请完全退出并重新打开 DSH'));
  ui.input('sbx-note').props.onChange({target:{value:'Local note survives upgrade'}});ui.render();
  await ui.nodes().find(n=>n.props.className==='sbx-compose').props.onSubmit({preventDefault(){}});await ui.settle();
  assert.equal(ui.writes.filter(x=>x.action==='add').length,1);
  assert.equal(ui.writes.filter(x=>x.action==='ai-tag').length,0);
});

test('an empty model result is explained and can be retried rather than called tagged',async()=>{
  const ui=mounted(new Map(),{tag:async()=>({applied:true,card:{id:'a'.repeat(32),updated_at:'revision',tags:[]}})});await ui.settle();
  ui.input('sbx-note').props.onChange({target:{value:'No clear topic'}});ui.render();
  await ui.nodes().find(n=>n.props.className==='sbx-compose').props.onSubmit({preventDefault(){}});await ui.settle();
  assert.ok(ui.text(ui.render()).includes('暂无合适标签'));
  assert.ok(ui.button('重试 AI 标签'));
});
