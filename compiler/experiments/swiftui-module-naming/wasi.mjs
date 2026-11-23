import { readFileSync } from "node:fs";
import { WASI } from "node:wasi";

const wasi = new WASI({ version: "preview1", args: ["PortableApp"], returnOnExit: true });
const binary = await WebAssembly.compile(readFileSync(process.argv[2]));
const instance = await WebAssembly.instantiate(binary, wasi.getImportObject());
process.exitCode = wasi.start(instance);
