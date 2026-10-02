import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiRequest", () => {
  it("uses the application base path and includes credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest<{ status: string }>("/api/health")).resolves.toEqual({
      status: "ok",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/check_annotator/api/health",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("throws the backend error response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: "TASK_NOT_FOUND", message: "タスクがありません" },
          }),
          { status: 404, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const request = apiRequest("/api/tasks/999/comments");
    await expect(request).rejects.toMatchObject({
      status: 404,
      code: "TASK_NOT_FOUND",
      message: "タスクがありません",
    } satisfies Partial<ApiError>);
  });

  it("handles non-JSON errors and empty success responses", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("error", { status: 502 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest("/api/test")).rejects.toMatchObject({
      code: "UNEXPECTED_RESPONSE",
    });
    await expect(
      apiRequest<void>("/api/auth/logout", { method: "POST" }),
    ).resolves.toBeUndefined();
  });
});
