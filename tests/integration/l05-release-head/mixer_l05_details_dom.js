async (expectedStatus) => {
  const main = document.querySelector("main");
  const deadline = performance.now() + 7000;
  const status = () => main?.querySelector('[role="status"] h2')?.innerText.trim();
  while (status() !== expectedStatus && performance.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  const fields = label => {
    const list = main?.querySelector(`dl[aria-label="${label}"]`);
    if (!list) return null;
    return Object.fromEntries([...list.querySelectorAll("dt")].filter(term =>
      term.innerText.trim() !== "Manifest capabilities"
    ).map(term => [term.innerText.trim(), term.nextElementSibling.innerText.trim()]));
  };
  const release = fields("Published release details");
  const list = main?.querySelector("dl[aria-label='Published release details'] .release-head-capabilities");
  const capabilities = release === null ? null : [...(list?.children ?? [])].map(row => ({
    id: row.querySelector(":scope > code").innerText,
    permissions: row.querySelector(":scope > div").innerText === "No grant entry"
      ? null : [...row.querySelectorAll(":scope > div code")].map(code => code.innerText),
  }));
  return {path: location.pathname + location.search, status: status() ?? null,
    target: fields("Release target"), release, capabilities};
}
