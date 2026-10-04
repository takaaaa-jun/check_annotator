import {
  describe,
  expect,
  it,
} from "vitest";

import { ApiError } from "../../lib/api/client";
import type { GroupTasksResponse } from "../../lib/api/types";
import {
  getTaskStateUpdateError,
  replaceUpdatedTask,
} from "./state-update";

const taskData: GroupTasksResponse = {
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
      updated_at: "2026-10-04T03:00:00Z",
    },
  ],
  pagination: {
    page: 1,
    page_size: 50,
    total: 1,
    total_pages: 1,
  },
};

describe("replaceUpdatedTask", () => {
  it("更新されたタスクだけをAPIの結果で置き換える", () => {
    const result = replaceUpdatedTask(
      taskData,
      {
        task_id: 10,
        group_id: 2,
        image_id: 100,
        state_id: 2,
        state_name: "完了",
        updated_at: "2026-10-04T04:00:00Z",
      },
    );

    expect(result.tasks[0]).toEqual({
      task_id: 10,
      image_id: 100,
      state_id: 2,
      state_name: "完了",
      updated_at: "2026-10-04T04:00:00Z",
    });
    expect(taskData.tasks[0].state_id).toBe(1);
  });
});

describe("getTaskStateUpdateError", () => {
  it.each([
    [403, "このタスクの状態を変更する権限がありません"],
    [404, "対象のタスクまたは状態が見つかりません"],
    [422, "選択した状態が正しくありません"],
    [500, "サーバーでエラーが発生しました。時間をおいて再度お試しください"],
  ])("%iエラーを案内文へ変換する", (status, message) => {
    expect(
      getTaskStateUpdateError(
        new ApiError(status, "ERROR", "API error"),
      ),
    ).toBe(message);
  });
});
