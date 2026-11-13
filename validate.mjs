import {parse} from '@formatjs/icu-messageformat-parser';
import {parse as parseJs} from 'acorn';
import fs from 'node:fs';
const [input,output]=process.argv.slice(2);
const data=JSON.parse(fs.readFileSync(input,'utf8'));
function contract(ast){
 const variables=new Set(),tags=new Set(),selectors=[];
 function visit(nodes){for(const n of nodes){
  if([1,2,3,4,5,6].includes(n.type))variables.add(n.value);
  if(n.type===8){tags.add(n.value);visit(n.children);}
  if(n.options){if(n.type===5)selectors.push([n.value,Object.keys(n.options).sort()]);Object.values(n.options).forEach(o=>visit(o.value));}
 }}
 visit(ast);return JSON.stringify({variables:[...variables].sort(),tags:[...tags].sort(),selectors:selectors.sort()});
}
const rejected=[];let accepted=0;
for(const [key,row] of Object.entries(data.messages??{})){
 if(row.source===row.target)continue;
 try{
  if(contract(parse(row.source))!==contract(parse(row.target)))throw Error('ICU placeholders, tags or selectors differ');
  accepted++;
 }catch(error){rejected.push({key,reason:error.message});row.target=row.source;}
}
for(const file of data.scripts??[])parseJs(fs.readFileSync(file,'utf8'),{ecmaVersion:'latest',sourceType:'script'});
fs.writeFileSync(output,JSON.stringify({messages:data.messages,accepted,rejected}));
console.log(JSON.stringify({accepted,rejected:rejected.length}));
