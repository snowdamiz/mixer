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
    return Object.fromEntries([...list.querySelectorAll("dt")].map(term => [
      term.innerText.trim(), term.nextElementSibling.innerText.trim(),
    ]));
  };
  return {
    path: location.pathname + location.search,
    status: status() ?? null,
    target: fields("Release target"),
    release: fields("Published release details"),
  };
}
