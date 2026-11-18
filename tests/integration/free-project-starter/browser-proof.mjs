import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const [portFile] = process.argv.slice(2);
const [port] = (await readFile(portFile, "utf8")).trim().split("\n");
const debuggerOrigin = `http://127.0.0.1:${port}`;
const getJSON = async path => (await fetch(debuggerOrigin + path, {signal: AbortSignal.timeout(4000)})).json();
const targets = await getJSON("/json/list");
const browser = await getJSON("/json/version");
const [page] = targets.filter(target => target.type === "page");
assert.ok(page?.webSocketDebuggerUrl);

const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.addEventListener("open", resolve, {once: true});
  ws.addEventListener("error", reject, {once: true});
});
let next = 0;
const pending = new Map();
const responses = [];
const mutations = [];
let usageReads = 0;
const target = JSON.parse(process.env.MIXER_SOURCE_TARGET);
ws.addEventListener("message", ({data}) => {
  const message = JSON.parse(data);
  pending.get(message.id)?.(message);
  if (message.method === "Network.requestWillBeSent") {
    const {url, method, postData} = message.params.request;
    const path = new URL(url).pathname;
    if (path === "/console-api/v1/workspace-admin" && method === "POST" &&
        JSON.parse(postData ?? "{}").operation === "usage") {
      usageReads++;
    } else if (path.startsWith("/console-api/") && method === "POST") {
      mutations.push(path);
    }
  }
  if (message.method === "Network.responseReceived") {
    const {url, status} = message.params.response;
    const path = new URL(url).pathname;
    if (path.startsWith("/console-api/")) responses.push({path, status});
  }
});

function call(method, params = {}) {
  const id = ++next;
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`Timed out: ${method}`));
    }, 5000);
    pending.set(id, message => {
      clearTimeout(timeout);
      pending.delete(id);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result);
    });
    ws.send(JSON.stringify({id, method, params}));
  });
}

async function evaluate(expression) {
  const value = await call("Runtime.evaluate", {expression, returnByValue: true, awaitPromise: true});
  if (value.exceptionDetails) throw new Error(value.exceptionDetails.exception?.description ?? value.exceptionDetails.text);
  return value.result.value;
}

async function waitFor(expression, label) {
  const deadline = Date.now() + 9500;
  do {
    try {
      if (await evaluate(expression)) return;
    } catch (error) {
      if (!String(error.message).includes("Cannot find context")) throw error;
    }
    await new Promise(resolve => setTimeout(resolve, 100));
  } while (Date.now() < deadline);
  const summary = await evaluate(`document.querySelector('#workspace-projects-heading')?.closest('section')?.innerText?.slice(0, 400) ??
    document.querySelector('main')?.innerText?.slice(0, 800)`);
  throw new Error(`Missing ${label}. Content: ${summary}\nResponses: ${JSON.stringify(responses.slice(-12))}`);
}

function element(selector, label) {
  return `[...document.querySelectorAll(${JSON.stringify(selector)})]
    .find(node => node.innerText.trim().split("\\n").map(text => text.trim()).includes(${JSON.stringify(label)}))`;
}

async function click(selector, label) {
  const query = element(selector, label);
  await waitFor(`!!(${query})`, label);
  await evaluate(`(${query}).click()`);
}

async function selectProject(organization, project) {
  for (const [list, name] of [["Organizations", organization], ["Projects", project]]) {
    const query = `[...document.querySelectorAll('ul[aria-label="${list}"] button')]
      .find(button => button.querySelector('.workspace-row-name')?.textContent.trim() === ${JSON.stringify(name)})`;
    if (list === "Projects") {
      const retry = `[...document.querySelector('#workspace-projects-heading')?.closest('section')?.querySelectorAll('button') ?? []]
        .find(button => button.innerText.trim() === 'Try again')`;
      await waitFor(`!!(${query}) || !!(${retry})`, name);
      if (!await evaluate(`!!(${query})`)) {
        await new Promise(resolve => setTimeout(resolve, 600));
        await evaluate(`(${retry})?.click()`);
      }
    }
    await waitFor(`!!(${query})`, name);
    await evaluate(`(${query}).click()`);
  }
  await click("main a", "View builds");
  await waitFor("location.pathname === '/builds' && !!document.querySelector('#application-list-heading')", "builds route");
}

async function openInputs() {
  await selectProject("Local starter HTTP owner", "Starter project");
  await click('[aria-label="Applications"] button', target.app);
  await click("main button", "New build");
}

const starter = element("main button", "Select local starter");
const exactInput = `(() => {
  const rows = [...document.querySelectorAll('main details')];
  return rows.filter(row => row.querySelector('summary')?.textContent.includes(${JSON.stringify(target.starterId)})
    && [...row.querySelectorAll('dd code')].some(code => code.textContent === ${JSON.stringify(target.sourceSha256)})).length === 1;
})()`;

try {
  await call("Page.enable");
  await call("Network.enable");
  const nav = await call("Page.navigate", {url: process.env.MIXER_SOURCE_BROWSER_URL});
  assert.equal(nav.errorText, undefined);
  await waitFor("location.pathname === '/workspace' && !!document.querySelector('main')", "workspace route");
  await openInputs();
  await waitFor(`!!(${starter})`, "trusted starter");
  assert.equal(await evaluate(exactInput), false);
  await click("main button", "Select local starter");
  await waitFor(exactInput, "exact selected input");
  assert.equal(await evaluate(`!!(${starter})`), false);

  await call("Page.reload");
  await waitFor("location.pathname === '/builds' && document.querySelector('main h2')?.innerText === 'Choose a project'", "reloaded builds route");
  await click("nav[aria-label='Main navigation'] a", "Organizations & projects");
  await openInputs();
  await waitFor(exactInput, "exact input after reload and app reselection");
  assert.equal(await evaluate(`!!(${starter})`), false);
  assert.deepEqual(mutations, ["/console-api/v1/source-starters"]);
  assert.equal(await evaluate(`fetch('/__fixture_done', {method:'POST'}).then(response => response.status)`), 204);
  console.log("BROWSER_SOURCE_SELECTION " + JSON.stringify({
    application: target.app, starterId: target.starterId, sourceSha256: target.sourceSha256,
    firstSelection: true, reload: true, consoleMutations: mutations, workspaceUsageReads: usageReads,
  }));
} finally {
  ws.close();
  const close = new WebSocket(browser.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      close.close();
      reject(new Error("Chrome did not close its DevTools connection"));
    }, 4000);
    close.addEventListener("open", () => close.send(JSON.stringify({id: 1, method: "Browser.close"})), {once: true});
    close.addEventListener("close", () => {
      clearTimeout(timeout);
      resolve();
    }, {once: true});
  });
}
