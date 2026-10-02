import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiRequest } from "./client";
import { getCurrentUser, login, logout } from "./auth";

vi.mock("./client", () => ({ apiRequest: vi.fn() }));

const apiRequestMock = vi.mocked(apiRequest);

beforeEach(() => {
  apiRequestMock.mockReset();
});

describe("auth API", () => {
  it("posts login credentials", async () => {
    apiRequestMock.mockResolvedValue({
      user: { user_id: 1, user_name: "takahashi", role_name: "worker" },
    });

    await login({ user_name: "takahashi", password: "test1" });

    expect(apiRequestMock).toHaveBeenCalledWith("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ user_name: "takahashi", password: "test1" }),
    });
  });

  it("calls the logout and current-user endpoints", async () => {
    apiRequestMock.mockResolvedValue(undefined);
    await logout();
    await getCurrentUser();

    expect(apiRequestMock).toHaveBeenNthCalledWith(1, "/api/auth/logout", {
      method: "POST",
    });
    expect(apiRequestMock).toHaveBeenNthCalledWith(2, "/api/users/me");
  });
});
