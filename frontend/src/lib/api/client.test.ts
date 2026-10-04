import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest';
import { APIError, fetchClient } from './client';

describe('fetchClient', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    vi.resetModules();
    process.env = { ...originalEnv };
    global.fetch = vi.fn();
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.restoreAllMocks();
  });

  it('指定したエンドポイントに正しいヘッダーでリクエストを送信すること', async () => {
    const mockData = { message: 'success' };
    (global.fetch as Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockData,
    });

    const result = await fetchClient('/api/test');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/test',
      expect.objectContaining({
        headers: expect.any(Headers),
        credentials: 'omit',
      })
    );
    expect(result).toEqual(mockData);
  });

  it('環境変数 NEXT_PUBLIC_MOCK_SCENARIO が設定されている場合、X-Mock-Scenario ヘッダーが付与されること', async () => {
    process.env.NEXT_PUBLIC_MOCK_SCENARIO = 'empty-groups';

    (global.fetch as Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ groups: [] }),
    });

    await fetchClient('/api/users/1/groups');

    const fetchMock = global.fetch as Mock;
    const callArgs = fetchMock.mock.calls[0];
    const headers: Headers = callArgs[1].headers;
    expect(headers.get('X-Mock-Scenario')).toBe('empty-groups');
  });

  it('HTTPエラーの場合に APIError をスローすること', async () => {
    const errorResponse = {
      detail: {
        code: 'UNAUTHORIZED',
        message: '認証エラーが発生しました．',
      },
    };

    (global.fetch as Mock).mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => errorResponse,
    });

    await expect(fetchClient('/api/users/me')).rejects.toThrow(APIError);
  });
});