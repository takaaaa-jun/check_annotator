import {
  describe,
  expect,
  it,
} from "vitest";

import { ApiError } from "../../lib/api/client";
import { getCommentsLoadError } from "./comments";

describe("getCommentsLoadError", () => {
  it.each([
    [403, "このタスクのコメントを表示する権限がありません", false],
    [404, "対象のタスクが見つかりません", false],
    [422, "ページまたは表示件数が正しくありません", false],
    [500, "サーバーでエラーが発生しました。時間をおいて再度お試しください", true],
  ])(
    "%iエラーを案内文へ変換する",
    (status, message, retryable) => {
      expect(
        getCommentsLoadError(
          new ApiError(status, "ERROR", "API error"),
        ),
      ).toMatchObject({
        message,
        retryable,
        unauthorized: false,
      });
    },
  );

  it("401を再ログインが必要なエラーとして扱う", () => {
    expect(
      getCommentsLoadError(
        new ApiError(401, "UNAUTHORIZED", "Unauthorized"),
      ).unauthorized,
    ).toBe(true);
  });
});
