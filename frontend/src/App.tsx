import { Route, Routes } from "react-router-dom";
import { LoginPage } from "./auth/LoginPage";
import { RequireAuth } from "./auth/RequireAuth";
import { AppShell } from "./shell/AppShell";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<p className="text-dim">Dashboard coming in Task 3.</p>} />
        </Route>
      </Route>
    </Routes>
  );
}
