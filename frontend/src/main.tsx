import "@fontsource/fraunces/700.css";
import "@fontsource/manrope/400.css";
import "@fontsource/manrope/600.css";
import "@fontsource/manrope/700.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";
import "./styles.css";

const container = document.getElementById("root");

if (!container) {
  throw new Error("Missing root container.");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
