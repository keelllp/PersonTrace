import { Route, Routes } from "react-router-dom";
import { LoginPage } from "./auth/LoginPage";
import { RequireAuth } from "./auth/RequireAuth";
import { AppShell } from "./shell/AppShell";
import { DashboardPage } from "./traces/DashboardPage";
import { NewTracePage } from "./traces/NewTracePage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="/new" element={<NewTracePage />} />
        </Route>
      </Route>
    </Routes>
  );
}
