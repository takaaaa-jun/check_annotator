import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./client";
import {
  createTaskComment,
  getTaskComments,
  updateTaskState,
} from "./tasks";

vi.mock("./client", () => ({
  apiRequest: vi.fn(),
}));

const apiRequestMock =
  vi.mocked(apiRequest);

beforeEach(() => {
  apiRequestMock.mockReset();
});

describe("updateTaskState", () => {
  it("指定タスクの状態更新APIを呼び出す", async () => {
    const response = {
      task_id: 10,
      group_id: 2,
      image_id: 100,
      state_id: 2,
      state_name: "完了",
      updated_at: "2026-10-04T03:00:00Z",
    };

    apiRequestMock.mockResolvedValue(
      response,
    );

    const result = await updateTaskState(
      10,
      2,
    );

    expect(
      apiRequestMock,
    ).toHaveBeenCalledWith(
      "/api/tasks/10/state",
      {
        method: "PATCH",
        body: JSON.stringify({
          state_id: 2,
        }),
      },
    );

    expect(result).toEqual(response);
  });

  it("APIエラーを呼び出し元へ伝える", async () => {
    const apiError = new Error(
      "更新に失敗しました",
    );

    apiRequestMock.mockRejectedValue(
      apiError,
    );

    await expect(
      updateTaskState(10, 2),
    ).rejects.toBe(apiError);
  });
});

describe("getTaskComments", () => {
  const response = {
    task_id: 10,
    comments: [],
    pagination: {
      page: 1,
      page_size: 50,
      total: 0,
      total_pages: 0,
    },
  };

  it("初期条件でコメント一覧APIを呼び出す", async () => {
    apiRequestMock.mockResolvedValue(response);

    const result = await getTaskComments(10);

    expect(apiRequestMock).toHaveBeenCalledWith(
      "/api/tasks/10/comments?page=1&page_size=50",
    );
    expect(result).toEqual(response);
  });

  it("ページ番号と表示件数を指定できる", async () => {
    apiRequestMock.mockResolvedValue(response);

    await getTaskComments(10, {
      page: 2,
      pageSize: 10,
    });

    expect(apiRequestMock).toHaveBeenCalledWith(
      "/api/tasks/10/comments?page=2&page_size=10",
    );
  });
});

describe("createTaskComment", () => {
  const response = {
    comment_id: 3,
    task_id: 10,
    user_id: 1,
    user_name: "takahashi",
    parent_id: null,
    content: "確認しました",
    created_at: "2026-10-04T03:00:00Z",
    updated_at: "2026-10-04T03:00:00Z",
  };

  it("通常コメントを投稿する", async () => {
    apiRequestMock.mockResolvedValue(response);

    const result = await createTaskComment(10, {
      content: "確認しました",
      parentId: null,
    });

    expect(apiRequestMock).toHaveBeenCalledWith(
      "/api/tasks/10/comments",
      {
        method: "POST",
        body: JSON.stringify({
          content: "確認しました",
          parent_id: null,
        }),
      },
    );
    expect(result).toEqual(response);
  });

  it("返信先コメントIDを送信する", async () => {
    apiRequestMock.mockResolvedValue({
      ...response,
      parent_id: 2,
    });

    await createTaskComment(10, {
      content: "返信です",
      parentId: 2,
    });

    expect(apiRequestMock).toHaveBeenCalledWith(
      "/api/tasks/10/comments",
      expect.objectContaining({
        body: JSON.stringify({
          content: "返信です",
          parent_id: 2,
        }),
      }),
    );
  });
});
