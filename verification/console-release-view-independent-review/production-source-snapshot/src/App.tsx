import { A, Navigate, Route, Router } from "@solidjs/router";
import { lazy, Show } from "solid-js";
import type { ParentProps } from "solid-js";
import { ReleaseChecks } from "./components/ReleaseChecks.js";

const Preview = import.meta.env.DEV ? lazy(() => import("./preview/ReleaseChecksPreview.js")) : undefined;

function Shell(props: ParentProps) {
  return <>
    <a class="skip-link" href="#main-content" target="_self">Skip to content</a>
    <div class="console-shell">
      <aside class="workspace-rail">
        <A class="brand" href="/releases" aria-label="Mixer console home">
          <img src="/assets/flick-128.webp" width="38" height="38" alt="" />
          <span>mixer<span class="brand-period">.</span></span>
        </A>
        <div class="workspace-label"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg><span>Project workspace</span></div>
        <nav class="project-navigation" aria-label="Main navigation">
          <p class="navigation-label">Delivery</p>
          <A href="/releases" activeClass="active"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/></svg>Releases</A>
        </nav>
        <nav class="resource-navigation" aria-label="Resources">
          <p class="navigation-label">Resources</p>
          <a href="https://github.com/snowdamiz/mixer/tree/main/docs" target="_blank" rel="noopener noreferrer">Documentation <span aria-hidden="true">↗</span><span class="sr-only"> (opens in a new tab)</span></a>
          <a href="https://github.com/snowdamiz/mixer" target="_blank" rel="noopener noreferrer">Source code <span aria-hidden="true">↗</span><span class="sr-only"> (opens in a new tab)</span></a>
        </nav>
        <p class="rail-caption">One Swift app.<br/>A world of possibility.</p>
      </aside>
      <div class="console-workspace">
        <header class="workspace-bar"><p>Workspace <span aria-hidden="true">/</span> <strong>Releases</strong></p><span class="workspace-product">Builds &amp; updates</span></header>
        <main id="main-content" tabIndex={-1}>{props.children}</main>
        <footer class="app-footer"><span>mixer<span class="brand-period">.</span></span><span>Thoughtfully built for the things you’ll build.</span></footer>
      </div>
    </div>
  </>;
}

function NotFound() {
  return <div class="empty-state"><h1>Page not found</h1><p><A href="/releases">Go to releases</A></p></div>;
}

export default function App() {
  return <Router root={Shell}>
    <Route path="/" component={() => <Navigate href="/releases" />} />
    <Route path="/releases" component={() => <ReleaseChecks state={{ kind: "unavailable" }} />} />
    <Show when={Preview}>{Component => <Route path="/preview/release-checks" component={Component()} />}</Show>
    <Route path="*" component={NotFound} />
  </Router>;
}
