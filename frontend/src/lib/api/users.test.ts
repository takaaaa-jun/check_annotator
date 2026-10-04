import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./client";
import { getUserGroups } from "./users";

vi.mock("./client", () => ({
  apiRequest: vi.fn(),
}));

const apiRequestMock = vi.mocked(apiRequest);

beforeEach(() => {
  apiRequestMock.mockReset();
});

describe("getUserGroups", () => {
  it("指定ユーザーのグループ進捗APIを呼び出す", async () => {
    apiRequestMock.mockResolvedValue({
      user: {
        user_id: 1,
        user_name: "takahashi",
      },
      groups: [],
    });

    const result = await getUserGroups(1);

    expect(apiRequestMock).toHaveBeenCalledTimes(1);

    expect(apiRequestMock).toHaveBeenCalledWith(
      "/api/users/1/groups",
    );

    expect(result).toEqual({
      user: {
        user_id: 1,
        user_name: "takahashi",
      },
      groups: [],
    });
  });

  it("指定されたユーザーIDをURLに使用する", async () => {
    apiRequestMock.mockResolvedValue({
      user: {
        user_id: 25,
        user_name: "other-user",
      },
      groups: [],
    });

    await getUserGroups(25);

    expect(apiRequestMock).toHaveBeenCalledWith(
      "/api/users/25/groups",
    );
  });

  it("APIエラーを呼び出し元へ伝える", async () => {
    const apiError = new Error(
      "APIとの通信に失敗しました",
    );

    apiRequestMock.mockRejectedValue(apiError);

    await expect(
      getUserGroups(1),
    ).rejects.toBe(apiError);
  });
});