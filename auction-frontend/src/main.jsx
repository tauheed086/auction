import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";
import AdminDashboard from "./admin/AdminDashboard.jsx";

const normalizedPath = window.location.pathname.replace(/\/+$/, "") || "/";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    {normalizedPath === "/admin-board" ? <AdminDashboard /> : <App />}
  </StrictMode>
);
