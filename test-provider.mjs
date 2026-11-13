import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {parse} from 'acorn';
const file=process.argv[2];
const text=fs.readFileSync(file,'utf8');
const ast=parse(text,{ecmaVersion:'latest',sourceType:'module'});
const declarations=ast.body.filter(n=>n.type!=='ImportDeclaration'&&n.start<text.indexOf('/*END_LOCAL_OVERLAY*/'));
// Extract the real provider by its unique patched messages call, not a reimplementation.
const provider=ast.body.find(n=>n.type==='FunctionDeclaration'&&text.slice(n.start,n.end).includes('messages:__claudeGatewayZhOverlay('));
assert.ok(provider,'Patched actual provider function exists');
const overlay=text.slice(0,text.indexOf('/*END_LOCAL_OVERLAY*/'));
const appMessages={};let experiment={};
const context=vm.createContext({
 document:{documentElement:{lang:'en-US'}},
 nV:{target:null,ready:null},rV:null,tV:appMessages,
 D:x=>x,rB:()=>{},iB:()=>{},w:()=>{},h:f=>f(),
 fV:()=>{},mV:()=>{},_V:()=>{},KB:()=>experiment,
 pV:{},Ga:()=> 'ltr',uV:x=>x,ue:()=>null,pe:x=>x,iV:/^$/,
 y:(type,props)=>({type,props}),Lo:'IntlProvider',Zr:'en-US',WB:'values',v:'fragment',oV:'rtl',
});
vm.runInContext(overlay+'\n'+text.slice(provider.start,provider.end)+'\nglobalThis.render='+provider.id.name+';',context);
let result=context.render({locale:'en-US',messages:{},children:null});
let messages=result.props.messages;
const catalog=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
for(const source of ['Settings','New chat','Log out']){
 const key=Object.keys(catalog).find(k=>catalog[k]===source);
 if(key) {assert.ok(/[一-鿿]/.test(messages[key]),source+' translated');console.log(source,'=>',messages[key]);}
}
assert.equal(result.props.locale,'en-US');
assert.equal(messages['unknown-new-message'],undefined);
assert.ok(Object.keys(messages).length>41000);
console.log('PASS: actual packaged Intl provider under 3p en-US empty bootstrap receives >41,000 translated message IDs');
