import { apiRequest } from "./client";
import type { CurrentUser, LoginResponse } from "./types";

export type LoginRequest = {
  user_name: string;
  password: string;
};

export function login(payload: LoginRequest): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function logout(): Promise<void> {
  return apiRequest<void>("/api/auth/logout", { method: "POST" });
}

export function getCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/api/users/me");
}
