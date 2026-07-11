import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../lib/api";
import { useAuth } from "./useAuth";

export function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const action = mode === "login" ? login : register;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await action.mutateAsync({ email, password });
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="display text-2xl mb-1">
          Person<span className="text-signal">Trace</span>
        </h1>
        <p className="text-dim mb-8">Find people in footage.</p>

        <form onSubmit={submit} className="bg-panel border border-line rounded-lg p-6 space-y-4">
          <label className="block">
            <span className="text-sm text-dim">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-md bg-void border border-line px-3 py-2"
            />
          </label>
          <label className="block">
            <span className="text-sm text-dim">Password</span>
            <input
              type="password"
              required
              minLength={8}
              maxLength={72}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md bg-void border border-line px-3 py-2"
            />
          </label>
          {error && <p className="text-danger text-sm">{error}</p>}
          <button
            type="submit"
            disabled={action.isPending}
            className="w-full rounded-md bg-signal text-void font-semibold py-2 disabled:opacity-50"
          >
            {mode === "login" ? "Sign in" : "Create account"}
          </button>
          <button
            type="button"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
            className="w-full text-sm text-dim hover:text-text"
          >
            {mode === "login" ? "New here? Create an account" : "Have an account? Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
