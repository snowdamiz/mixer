import { render } from "solid-js/web";
import App from "./App.js";
import "./styles.css";

const container = document.getElementById("app");
if (!container) throw new Error("Missing Mixer console container");
render(() => <App />, container);
