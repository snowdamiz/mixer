import {readFile,writeFile} from 'node:fs/promises';
import {resolve,join,dirname} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const here=import.meta.dirname,bindings=JSON.parse(await readFile(join(here,'bindings.json'),'utf8'));
const project=join(bindings.scratch,'hosted-worker-controller'),base=join(project,'dist/src');
const {default:ts}=await import(pathToFileURL(join(project,'node_modules/typescript/lib/typescript.js')));
const seen=new Set(),files=[],externals=new Set(),selectors=[];
async function visit(path){
  if(seen.has(path))return;seen.add(path);if(!path.startsWith(base+'/'))throw new Error('outside_production_closure');
  const bytes=await readFile(path);files.push({path:path.slice(project.length+1),bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')});
  if(path.endsWith('.sql')){if(bytes.toString().includes('test_'))throw new Error('test_schema_in_production');return;}
  const source=ts.createSourceFile(path,bytes.toString(),ts.ScriptTarget.ES2022,true,ts.ScriptKind.JS),imports=[];
  function walk(n){
    if(ts.isCallExpression(n)&&(n.expression.kind===ts.SyntaxKind.ImportKeyword||(ts.isIdentifier(n.expression)&&['require','eval'].includes(n.expression.text))))throw new Error('unclosed_loader');
    if((ts.isImportDeclaration(n)||ts.isExportDeclaration(n))&&n.moduleSpecifier){if(!ts.isStringLiteral(n.moduleSpecifier))throw new Error('computed_module');imports.push(n.moduleSpecifier.text);}
    if(ts.isStringLiteral(n)&&(/__test|MIXER_CONTROLLER_TEST_REPORT|synthetic-verification|test_settings|test_calls/.test(n.text)))selectors.push(n.text);
    ts.forEachChild(n,walk);
  }walk(source);
  for(const id of imports){if(id==='cloudflare:workers')externals.add(id);else if(id.startsWith('.'))await visit(resolve(dirname(path),id));else throw new Error('unselected_external:'+id);}
}
await visit(join(base,'index.js'));if(selectors.length)throw new Error('fixture_selector_in_production');if(files.length!==9)throw new Error('unexpected_closure');
const report={status:'passed',scope:'independent-AST-production-import-closure-and-fixture-selector-check-only',files,externals:[...externals],fixtureSelectors:selectors,authorizationGate:false};
await writeFile(join(here,'independent-closure.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
