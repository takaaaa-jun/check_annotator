import { APIErrorResponse } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export class APIError extends Error {
  constructor(
    public status: number,
    public data: APIErrorResponse
  ) {
    super(data.detail.message);
    this.name = 'APIError';
  }
}

// 画面側コンポーネントとの表記互換性のためのエイリアス
export { APIError as ApiError };

export async function fetchClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  // バックエンド側のモックシナリオ制御用ヘッダーを付与
  const mockScenario = process.env.NEXT_PUBLIC_MOCK_SCENARIO;
  if (mockScenario) {
    headers.set('X-Mock-Scenario', mockScenario);
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'omit',
  });

  if (!response.ok) {
    let errorData: APIErrorResponse;
    try {
      errorData = await response.json();
    } catch {
      errorData = {
        detail: {
          code: 'UNEXPECTED_ERROR',
          message: 'An unexpected error occurred.',
        },
      };
    }
    throw new APIError(response.status, errorData);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// 既存APIクライアント（auth.ts / users.ts）との互換性のためのエイリアス
export const apiRequest = fetchClient;