import { render } from "solid-js/web";
import App from "./App.js";
import { createBrowserSessionBinding } from "./state/browser-session-binding.js";
import "./styles.css";

const container = document.getElementById("app");
if (!container) throw new Error("Missing Mixer console container");
function ConsoleRoot() {
  const binding = createBrowserSessionBinding();
  return <App workspaceSession={binding.workspaceSession()} />;
}

render(() => <ConsoleRoot />, container);
