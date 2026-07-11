import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { User } from "../lib/types";

export function useAuth() {
  const queryClient = useQueryClient();
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api.get<User>("/api/auth/me"),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const login = useMutation({
    mutationFn: (creds: { email: string; password: string }) =>
      api.post<User>("/api/auth/login", creds),
    onSuccess: (user) => queryClient.setQueryData(["me"], user),
  });

  const register = useMutation({
    mutationFn: (creds: { email: string; password: string }) =>
      api.post<User>("/api/auth/register", creds),
    onSuccess: (user) => queryClient.setQueryData(["me"], user),
  });

  const logout = useMutation({
    mutationFn: () => api.post("/api/auth/logout"),
    onSuccess: () => queryClient.setQueryData(["me"], null),
  });

  return { user: me.data ?? null, isLoading: me.isLoading, login, register, logout };
}
