import {
  describe,
  expect,
  it,
} from "vitest";

import { ApiError } from "../../lib/api/client";
import {
  COMMENT_MAX_LENGTH,
  getCommentSubmitError,
  validateCommentContent,
} from "./comment-form";

describe("validateCommentContent", () => {
  it.each(["", "   ", "\n\t"])(
    "空文字または空白のみを拒否する",
    (content) => {
      expect(validateCommentContent(content)).not.toBeNull();
    },
  );

  it("前後空白を除いて2000文字まで許可する", () => {
    expect(
      validateCommentContent(
        `  ${"x".repeat(COMMENT_MAX_LENGTH)}  `,
      ),
    ).toBeNull();
  });

  it("前後空白を除いて2001文字以上を拒否する", () => {
    expect(
      validateCommentContent(
        "x".repeat(COMMENT_MAX_LENGTH + 1),
      ),
    ).not.toBeNull();
  });
});

describe("getCommentSubmitError", () => {
  it.each([
    [403, "このタスクへコメントする権限がありません"],
    [404, "対象のタスクまたは返信先コメントが見つかりません"],
    [422, "入力内容が正しくありません"],
    [500, "サーバーでエラーが発生しました。時間をおいて再度お試しください"],
  ])("%iエラーを案内文へ変換する", (status, message) => {
    expect(
      getCommentSubmitError(
        new ApiError(status, "ERROR", "API error"),
      ).message,
    ).toBe(message);
  });

  it("401を再ログインが必要なエラーとして扱う", () => {
    expect(
      getCommentSubmitError(
        new ApiError(401, "UNAUTHORIZED", "Unauthorized"),
      ).unauthorized,
    ).toBe(true);
  });
});
