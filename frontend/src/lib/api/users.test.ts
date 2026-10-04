import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./client";
import {
  getGroupTasks,
  getUserGroups,
} from "./users";

vi.mock("./client", () => ({
  apiRequest: vi.fn(),
}));

const apiRequestMock =
  vi.mocked(apiRequest);

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

    const result =
      await getUserGroups(1);

    expect(
      apiRequestMock,
    ).toHaveBeenCalledTimes(1);

    expect(
      apiRequestMock,
    ).toHaveBeenCalledWith(
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

    expect(
      apiRequestMock,
    ).toHaveBeenCalledWith(
      "/api/users/25/groups",
    );
  });

  it("APIエラーを呼び出し元へ伝える", async () => {
    const apiError = new Error(
      "APIとの通信に失敗しました",
    );

    apiRequestMock.mockRejectedValue(
      apiError,
    );

    await expect(
      getUserGroups(1),
    ).rejects.toBe(apiError);
  });
});

describe("getGroupTasks", () => {
  const response = {
    group: {
      group_id: 2,
      group_name: "グループ2",
      user_id: 1,
      user_name: "takahashi",
    },
    tasks: [
      {
        task_id: 10,
        image_id: 100,
        state_id: 1,
        state_name: "未着手",
        updated_at:
          "2026-10-04T03:00:00Z",
      },
    ],
    pagination: {
      page: 1,
      page_size: 50,
      total: 1,
      total_pages: 1,
    },
  };

  it("初期条件でタスク一覧APIを呼び出す", async () => {
    apiRequestMock.mockResolvedValue(
      response,
    );

    const result =
      await getGroupTasks(1, 2);

    expect(
      apiRequestMock,
    ).toHaveBeenCalledTimes(1);

    expect(
      apiRequestMock,
    ).toHaveBeenCalledWith(
      "/api/users/1/groups/2/tasks?page=1&page_size=50",
    );

    expect(result).toEqual(response);
  });

  it("状態IDをクエリへ追加する", async () => {
    apiRequestMock.mockResolvedValue(
      response,
    );

    await getGroupTasks(1, 2, {
      stateId: 3,
    });

    expect(
      apiRequestMock,
    ).toHaveBeenCalledWith(
      "/api/users/1/groups/2/tasks?state_id=3&page=1&page_size=50",
    );
  });

  it("ページ番号とページサイズをクエリへ追加する", async () => {
    apiRequestMock.mockResolvedValue({
      ...response,
      pagination: {
        page: 2,
        page_size: 10,
        total: 15,
        total_pages: 2,
      },
    });

    await getGroupTasks(1, 2, {
      page: 2,
      pageSize: 10,
    });

    expect(
      apiRequestMock,
    ).toHaveBeenCalledWith(
      "/api/users/1/groups/2/tasks?page=2&page_size=10",
    );
  });

  it("状態・ページ・ページサイズを同時に指定できる", async () => {
    apiRequestMock.mockResolvedValue(
      response,
    );

    await getGroupTasks(3, 4, {
      stateId: 2,
      page: 3,
      pageSize: 100,
    });

    expect(
      apiRequestMock,
    ).toHaveBeenCalledWith(
      "/api/users/3/groups/4/tasks?state_id=2&page=3&page_size=100",
    );
  });

  it("APIエラーを呼び出し元へ伝える", async () => {
    const apiError = new Error(
      "APIとの通信に失敗しました",
    );

    apiRequestMock.mockRejectedValue(
      apiError,
    );

    await expect(
      getGroupTasks(1, 2),
    ).rejects.toBe(apiError);
  });
});