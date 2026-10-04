import { ApiError } from "../../lib/api/client";

export type CommentsLoadError = {
  message: string;
  retryable: boolean;
  unauthorized: boolean;
};

export function getCommentsLoadError(
  error: unknown,
): CommentsLoadError {
  if (!(error instanceof ApiError)) {
    return {
      message: "予期しないエラーが発生しました",
      retryable: true,
      unauthorized: false,
    };
  }

  switch (error.status) {
    case 401:
      return {
        message: "ログインが必要です",
        retryable: false,
        unauthorized: true,
      };
    case 403:
      return {
        message: "このタスクのコメントを表示する権限がありません",
        retryable: false,
        unauthorized: false,
      };
    case 404:
      return {
        message: "対象のタスクが見つかりません",
        retryable: false,
        unauthorized: false,
      };
    case 422:
      return {
        message: "ページまたは表示件数が正しくありません",
        retryable: false,
        unauthorized: false,
      };
    case 500:
      return {
        message: "サーバーでエラーが発生しました。時間をおいて再度お試しください",
        retryable: true,
        unauthorized: false,
      };
    default:
      return {
        message: error.message || "コメントの取得に失敗しました",
        retryable: true,
        unauthorized: false,
      };
  }
}
