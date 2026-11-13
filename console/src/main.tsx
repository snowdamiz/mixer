import { render } from "solid-js/web";
import { SignInBoundary } from "./components/SignIn.js";
import App from "./App.js";
import { createBrowserSessionBinding } from "./state/browser-session-binding.js";
import "./styles.css";

const container = document.getElementById("app");
if (!container) throw new Error("Missing Mixer console container");
function ConsoleRoot() {
  const binding = createBrowserSessionBinding();
  return <SignInBoundary session={binding.workspaceSession} invalidate={binding.invalidate}><App workspaceSession={binding.workspaceSession()} onRetrySession={binding.revalidate} /></SignInBoundary>;
}

render(() => <ConsoleRoot />, container);
