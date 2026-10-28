import fs from 'node:fs/promises';
import crypto from 'node:crypto';
const root='/Users/andreyyurlov/Documents/dev/mixer';
const out=root+'/verification/github-delivery-architecture-comparison';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const specs={
 'swift-execution-architecture-comparison':'b20440be09778e3209de5c1e6dae941e0580b8737fe28ed35be53777e3292f70',
 'swift-execution-architecture-independent':'c1ecb422803c2e43dc69206b28e6f51e2b023b9b8fab13054e20ecc7976a7486',
 'swift-execution-architecture-correction':'4efa21ab9e7bf43cec647c760bdacf6c3e5b2be944976240ec186c738370a6d2',
 'swift-execution-architecture-correction-independent':'4b09d719746ba04fbc722cd83751c2e2082d8997a984ce407031dc7e1f3daceb'};
const verified=[];
for(const [lane,digest]of Object.entries(specs)){
 const base=root+'/verification/'+lane;
 const raw=await fs.readFile(base+'/seal.json');if(hash(raw)!==digest)throw Error(lane+' seal');
 const seal=JSON.parse(raw);let count=0,bytes=0;
 const entries=Array.isArray(seal.files)?seal.files.map(x=>[x.path,x]):Object.entries(seal.files);
 for(const [p,row]of entries){if(p.startsWith('/')||p.split('/').includes('..'))throw Error('path');const st=await fs.lstat(base+'/'+p);if(!st.isFile()||st.isSymbolicLink())throw Error(p);const data=await fs.readFile(base+'/'+p);if(data.length!==row.bytes||hash(data)!==row.sha256)throw Error(lane+'/'+p);count++;bytes+=data.length;}
 if(seal.fileCount!==undefined&&count!==seal.fileCount)throw Error('count');
 if(seal.totalBytes!==undefined&&bytes!==seal.totalBytes)throw Error('bytes');
 verified.push({lane,sealSHA256:digest,count,bytes});
}
const receipt=JSON.parse(await fs.readFile(root+'/verification/swift-execution-architecture-correction-independent/receipt.json'));
if(receipt.decision!=='source-qualified-accept'||receipt.newActualFullAttempts!==0)throw Error('review');
const workflow=await fs.readFile(root+'/verification/swift-execution-architecture-correction/workflow.yml');
const target='.github/workflows/swift-execution-architecture-comparison.yml';
await fs.writeFile(root+'/'+target,workflow,{flag:'wx'});
const selection={schema:1,selectedAt:new Date().toISOString(),basisRevision:'8888d8e2c8431ee311c68e94a1abbb280f84802a',basisTree:'4afcac3a7354d7685fa9ebc55292b9871197e24e',decision:'Select the independently accepted corrected runner for one bounded remote architecture comparison',verifiedPackets:verified,workflow:{path:target,bytes:workflow.length,sha256:hash(workflow)},arms:['existing cache control','dense validated-function resident map and free-pin bitmap'],measurementLimits:{instructionFuel:1000000000,executionWork:8000000000,cacheWork:768000000,durationMilliseconds:600000,maxCombinedBytes:268435456,maxFullAttempts:2,maxCommands:11,driverSeconds:2700},preconditions:'Both optimized builds, finite suites, harness controls, compiled geometry and zero cleanup must pass before any full attempt.',failureRule:'No retry or refund. Binding, invariant, oracle and custody defects stop the campaign. Only clean ordinary resource failures may advance the other arm.',newActualFullAttempts:0,productionDefaultsChanged:false,feasibilityAccepted:false,GA:false,holdsPreserved:true};
await fs.writeFile(out+'/selection.json',JSON.stringify(selection,null,2)+String.fromCharCode(10),{flag:'wx'});
export default selection;
