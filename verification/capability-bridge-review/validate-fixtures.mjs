// Syntax/type validation only. This does not execute the bridge or owned VM.
import fs from 'node:fs';
const directory = process.argv[2];
const files = fs.readdirSync(directory).filter(name => name.endsWith('.wasm')).sort();
const results = files.map(name => {
    const bytes = fs.readFileSync(directory + '/' + name);
    if (!WebAssembly.validate(bytes)) throw new Error(name + ' is invalid Wasm');
    const module = new WebAssembly.Module(bytes);
    return {name, valid: true,
        imports: WebAssembly.Module.imports(module).map(x => x.module + '/' + x.name),
        exports: WebAssembly.Module.exports(module).map(x => x.name)};
});
console.log(JSON.stringify({scope: 'Fixture syntax validation only; no bridge/engine execution', node: process.version, results}, null, 2));
