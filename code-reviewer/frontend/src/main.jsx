// main.jsx
// --------
// Standard React 18 entry point: mounts the <App /> component into the
// #root div declared in index.html.

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
