import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { apiRequest } from "./client";
import { updateTaskState } from "./tasks";

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
