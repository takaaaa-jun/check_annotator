export const APP_BASE_PATH =
  process.env.NEXT_PUBLIC_BASE_PATH ?? "/check_annotator";

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
  };
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== "object" || value === null || !("error" in value)) {
    return false;
  }

  const error = value.error;
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof error.code === "string" &&
    "message" in error &&
    typeof error.message === "string"
  );
}

export async function apiRequest<T>(
  path: `/api/${string}`,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${APP_BASE_PATH}${path}`, {
    ...init,
    credentials: "include",
    headers,
  });

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    if (isApiErrorBody(body)) {
      throw new ApiError(response.status, body.error.code, body.error.message);
    }
    throw new ApiError(
      response.status,
      "UNEXPECTED_RESPONSE",
      "APIとの通信に失敗しました",
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
