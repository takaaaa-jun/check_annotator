import {
  describe,
  expect,
  it,
} from "vitest";

import {
  calculateProgress,
  getCompletedCount,
} from "./progress";

describe("getCompletedCount", () => {
  it("完了状態の件数を返す", () => {
    const result = getCompletedCount([
      {
        state_id: 1,
        state_name: "未着手",
        count: 2,
      },
      {
        state_id: 2,
        state_name: "完了",
        count: 1,
      },
      {
        state_id: 3,
        state_name: "付与予定ラベル",
        count: 0,
      },
      {
        state_id: 4,
        state_name: "コメント",
        count: 0,
      },
    ]);

    expect(result).toBe(1);
  });

  it("完了状態が存在しない場合は0を返す", () => {
    const result = getCompletedCount([
      {
        state_id: 1,
        state_name: "未着手",
        count: 3,
      },
    ]);

    expect(result).toBe(0);
  });

  it("状態一覧が空の場合は0を返す", () => {
    expect(getCompletedCount([])).toBe(0);
  });
});

describe("calculateProgress", () => {
  it("完了件数と総タスク数から進捗率を計算する", () => {
    expect(calculateProgress(1, 3)).toBe(33);
  });

  it("全タスクが完了している場合は100を返す", () => {
    expect(calculateProgress(3, 3)).toBe(100);
  });

  it("完了件数が0の場合は0を返す", () => {
    expect(calculateProgress(0, 3)).toBe(0);
  });

  it("総タスク数が0の場合は0を返す", () => {
    expect(calculateProgress(0, 0)).toBe(0);
  });

  it("100を超える計算結果を100に補正する", () => {
    expect(calculateProgress(4, 3)).toBe(100);
  });

  it("負数になる計算結果を0に補正する", () => {
    expect(calculateProgress(-1, 3)).toBe(0);
  });

  it("総タスク数が負数の場合は0を返す", () => {
    expect(calculateProgress(1, -1)).toBe(0);
  });
});