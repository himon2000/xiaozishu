import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const root = new URL('../frontend/subpackages/jingzang/', import.meta.url);
function page(name, mocks) {
  let definition;
  const copied=[];
  vm.runInNewContext(readFileSync(new URL(`${name}/${name}.js`,root),'utf8'), {
    require:()=>mocks, Page:p=>{definition=p}, console,
    wx:{setClipboardData:args=>copied.push(args.data),navigateTo(){},navigateBack(){}},
  });
  const instance={...definition,data:JSON.parse(JSON.stringify(definition.data)),setData(values){Object.assign(this.data,values)}};
  return {instance,copied};
}
const school='香港中文大学（深圳）';
const source={id:'source:test',title:'官网',url:'https://sds.cuhk.edu.cn/page/361',reviewed_on:'2026-10-26'};

test('loads graph-backed schools and forwards selected school, evidence and caveats',async()=>{
  let request;
  const {instance,copied}=page('school-wiki',{
    get:async()=>({schools:[{name:school}],graph_version:'v-test'}),
    post:async(path,payload)=>{request={path,payload};return {answer:'课程事实',sources:[source],caveats:['适用年级待核验'],evidence_status:'supported',history_saved:true}},
  });
  await instance.loadSchools();
  assert.equal(instance.data.selectedSchool,school);
  instance.data.inputText='有哪些课程？';
  await instance.onAsk();
  assert.equal(request.path,'/school-wiki/ask');
  assert.equal(request.payload.school_name,school);
  assert.equal(instance.data.messages[1].sources[0].url,source.url);
  assert.equal(instance.data.messages[1].caveats[0],'适用年级待核验');
  assert.equal(instance.data.loading,false);
  instance.onCopySource({currentTarget:{dataset:{url:source.url}}});
  instance.onCopySource({currentTarget:{dataset:{url:'javascript:alert(1)'}}});
  assert.deepEqual(copied,[source.url]);
});

test('offline errors are visible and do not create a fabricated answer',async()=>{
  const {instance}=page('school-wiki',{get:async()=>{throw {message:'独立知识服务未配置'}},post:async()=>{throw {detail:'查询超时'}}});
  await instance.loadSchools();
  assert.equal(instance.data.schoolError,'独立知识服务未配置');
  instance.data.inputText='招生计划';
  await instance.onAsk();
  assert.equal(instance.data.messages[1].content,'查询超时');
  assert.equal(instance.data.loading,false);
});

test('typed graph catalog loads and a stale response cannot replace the newly selected scope',async()=>{
  let complete;
  const {instance}=page('school-wiki',{get:()=>new Promise(resolve=>{complete=resolve})});
  instance.data.selectedSchool=school;
  instance.data.topic='teaching';
  const pending=instance.loadKnowledge();
  instance.data.topic='research';
  complete({nodes:[{id:'wrong',name:'旧课程'}],sources:[]});
  await pending;
  assert.equal(instance.data.knowledge.length,0);
});

test('history consumes records contract and keeps source links',async()=>{
  const {instance}=page('school-wiki-history',{get:async()=>({records:[{id:'qa1',answer:'已保存回答',sources:[source]}]})});
  await instance.loadHistory();
  assert.equal(instance.data.history[0].answer,'已保存回答');
  assert.equal(instance.data.history[0].sources[0].url,source.url);
});

test('failed history request displays an error rather than an empty-history claim',async()=>{
  const {instance}=page('school-wiki-history',{get:async()=>{throw {message:'请先登录'}}});
  await instance.loadHistory();
  assert.equal(instance.data.historyError,'请先登录');
});
