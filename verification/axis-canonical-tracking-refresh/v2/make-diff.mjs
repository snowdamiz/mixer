import fs from "node:fs/promises";
const diff = function sourceDiff(before,after,path) {
  const oldLines=before.split('\n'),newLines=after.split('\n');oldLines.pop();newLines.pop();
  function chunk(a0,a1,b0,b1,depth=0){
    const prefix=[];while(a0<a1&&b0<b1&&oldLines[a0]===newLines[b0])prefix.push({t:' ',s:oldLines[a0++],a:a0,b:++b0});
    const suffix=[];while(a0<a1&&b0<b1&&oldLines[a1-1]===newLines[b1-1])suffix.push({t:' ',s:oldLines[--a1],a:a1+1,b:b1--});
    if(a0===a1||b0===b1||depth>16){const middle=[];for(let a=a0;a<a1;a++)middle.push({t:'-',s:oldLines[a],a:a+1,b:b0+1});for(let b=b0;b<b1;b++)middle.push({t:'+',s:newLines[b],a:a1+1,b:b+1});return [...prefix,...middle,...suffix.reverse()];}
    const counts=new Map();for(let a=a0;a<a1;a++){const s=oldLines[a];const v=counts.get(s);counts.set(s,v?{ac:v.ac+1,a:v.a,bc:v.bc,b:v.b}:{ac:1,a,bc:0,b:-1});}for(let b=b0;b<b1;b++){const s=newLines[b];const v=counts.get(s);if(v){v.bc++;v.b=b;}}
    const candidates=[...counts.values()].filter(x=>x.ac===1&&x.bc===1).sort((a,b)=>a.a-b.a);
    const tails=[],prev=[];for(let i=0;i<candidates.length;i++){let l=0,h=tails.length;while(l<h){const m=(l+h)>>1;if(candidates[tails[m]].b<candidates[i].b)l=m+1;else h=m;}prev[i]=l?tails[l-1]:-1;tails[l]=i;}
    if(!tails.length){const middle=[];for(let a=a0;a<a1;a++)middle.push({t:'-',s:oldLines[a],a:a+1,b:b0+1});for(let b=b0;b<b1;b++)middle.push({t:'+',s:newLines[b],a:a1+1,b:b+1});return [...prefix,...middle,...suffix.reverse()];}
    const anchors=[];for(let i=tails.at(-1);i!==-1;i=prev[i])anchors.push(candidates[i]);anchors.reverse();
    const middle=[];let ai=a0,bi=b0;for(const anchor of anchors){middle.push(...chunk(ai,anchor.a,bi,anchor.b,depth+1),{t:' ',s:oldLines[anchor.a],a:anchor.a+1,b:anchor.b+1});ai=anchor.a+1;bi=anchor.b+1;}middle.push(...chunk(ai,a1,bi,b1,depth+1));return [...prefix,...middle,...suffix.reverse()];
  }
  const ops=chunk(0,oldLines.length,0,newLines.length);
  if(ops.filter(x=>x.t!=='+').map(x=>x.s).join('\n')!==oldLines.join('\n')||ops.filter(x=>x.t!=='-').map(x=>x.s).join('\n')!==newLines.join('\n'))throw Error('Diff does not reconstruct source '+path);
  let oldPos=1,newPos=1;for(const op of ops){op.old=oldPos;op.new=newPos;if(op.t!=='+')oldPos++;if(op.t!=='-')newPos++;}
  const indexes=ops.flatMap((x,i)=>x.t===' '?[]:[i]);const groups=[];for(const idx of indexes){const start=Math.max(0,idx-3),end=Math.min(ops.length,idx+4);if(groups.length&&start<=groups.at(-1).end)groups.at(-1).end=end;else groups.push({start,end});}
  const rows=['--- a/'+path,'+++ b/'+path];for(const {start,end} of groups){const part=ops.slice(start,end),oc=part.filter(x=>x.t!=='+').length,nc=part.filter(x=>x.t!=='-').length;rows.push('@@ -'+(oc?part[0].old:part[0].old-1)+','+oc+' +'+(nc?part[0].new:part[0].new-1)+','+nc+' @@',...part.map(x=>x.t+x.s));}
  return {text:rows.join('\n')+'\n',hunks:groups.length,added:ops.filter(x=>x.t==='+').length,deleted:ops.filter(x=>x.t==='-').length};
};
const root = "/Users/andreyyurlov/Documents/dev/mixer";
const out = "/Users/andreyyurlov/Documents/dev/mixer/verification/axis-canonical-tracking-refresh/v2";
let combined="";for (const path of ["PLAN.md","STATUS.md","work-graph.json","gates/ga.json"]) { combined += diff(await fs.readFile(root+"/"+path,"utf8"),await fs.readFile(out+"/proposed/"+path,"utf8"),path).text; }
await fs.writeFile(out+"/tracking.diff",combined);
