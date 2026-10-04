import { ApiError } from "../../lib/api/client";

export const COMMENT_MAX_LENGTH = 2000;

export function validateCommentContent(
  content: string,
): string | null {
  const trimmedContent = content.trim();

  if (trimmedContent.length === 0) {
    return "コメントを入力してください";
  }

  if (trimmedContent.length > COMMENT_MAX_LENGTH) {
    return `コメントは${COMMENT_MAX_LENGTH}文字以内で入力してください`;
  }

  return null;
}

export type CommentSubmitError = {
  message: string;
  unauthorized: boolean;
};

export function getCommentSubmitError(
  error: unknown,
): CommentSubmitError {
  if (!(error instanceof ApiError)) {
    return {
      message: "予期しないエラーが発生しました。入力内容を確認して再度お試しください",
      unauthorized: false,
    };
  }

  switch (error.status) {
    case 401:
      return {
        message: "ログインが必要です",
        unauthorized: true,
      };
    case 403:
      return {
        message: "このタスクへコメントする権限がありません",
        unauthorized: false,
      };
    case 404:
      return {
        message: "対象のタスクまたは返信先コメントが見つかりません",
        unauthorized: false,
      };
    case 422:
      return {
        message: "入力内容が正しくありません",
        unauthorized: false,
      };
    case 500:
      return {
        message: "サーバーでエラーが発生しました。時間をおいて再度お試しください",
        unauthorized: false,
      };
    default:
      return {
        message: error.message || "コメントの投稿に失敗しました",
        unauthorized: false,
      };
  }
}
