import ts from "typescript";
import {readFile,writeFile} from "node:fs/promises";
import {resolve,dirname} from "node:path";
import {createHash} from "node:crypto";
const root=resolve(import.meta.dirname,".."),project=import.meta.dirname,visited=new Set(),externals=new Set(),files=[];
async function visit(path){
  if(visited.has(path))return;visited.add(path);
  if(!path.startsWith(resolve(project,"dist/src")+"/"))throw new Error("nonproduction_module_in_bundle");
  const bytes=await readFile(path);files.push({path:path.slice(project.length+1),bytes:bytes.length,sha256:createHash("sha256").update(bytes).digest("hex")});
  if(path.endsWith(".sql"))return;
  const source=ts.createSourceFile(path,bytes.toString("utf8"),ts.ScriptTarget.ES2022,true,ts.ScriptKind.JS);
  const imports=[];
  function walk(node){
    if((ts.isImportDeclaration(node)||ts.isExportDeclaration(node))&&node.moduleSpecifier){if(!ts.isStringLiteral(node.moduleSpecifier))throw new Error("computed_module");imports.push(node.moduleSpecifier.text);}
    if(ts.isCallExpression(node)&&node.expression.kind===ts.SyntaxKind.ImportKeyword)throw new Error("dynamic_module_in_deployment");
    ts.forEachChild(node,walk);
  }walk(source);
  for(const id of imports){if(id==="cloudflare:workers")externals.add(id);else if(id.startsWith("."))await visit(resolve(dirname(path),id));else throw new Error("unselected_runtime_dependency");}
}
await visit(resolve(project,"dist/src/index.js"));
const report={status:"passed",scope:"TypeScript-AST-static-production-module-closure-only",files,externals:[...externals],testBundleIncluded:false,
  note:"This proves static build closure; it is not a hostile-code or OTA authorization gate."};
await writeFile(resolve(root,"verification/hosted-worker-controller-implementation/production-build-closure.json"),JSON.stringify(report,null,2)+"\n");
console.log(JSON.stringify({status:"passed",productionFiles:files.length,externalModules:[...externals],testBundleIncluded:false}));
