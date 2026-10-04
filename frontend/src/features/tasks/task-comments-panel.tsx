import {
  useEffect,
  useRef,
  useState,
} from "react";

import type {
  Comment,
  TaskCommentsResponse,
} from "../../lib/api/types";
import {
  createTaskComment,
  getTaskComments,
  type TaskCommentsPageSize,
} from "../../lib/api/tasks";
import { formatDateTime } from "../../lib/format/date-time";
import {
  getCommentsLoadError,
  type CommentsLoadError,
} from "./comments";
import {
  COMMENT_MAX_LENGTH,
  getCommentSubmitError,
  validateCommentContent,
} from "./comment-form";
import { FeedbackMessage } from "../../components/feedback-message";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/async-state";

type TaskCommentsPanelProps = {
  taskId: number;
  imageId: number;
  refreshKey?: number;
  initialContent?: string;
  focusKey?: number;
  onUnauthorized: () => void;
  onCompleted?: () => void;
};

export function TaskCommentsPanel({
  taskId,
  imageId,
  refreshKey = 0,
  initialContent = "",
  focusKey = 0,
  onUnauthorized,
  onCompleted,
}: TaskCommentsPanelProps) {
  const [commentData, setCommentData] =
    useState<TaskCommentsResponse | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] =
    useState<TaskCommentsPageSize>(50);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] =
    useState<CommentsLoadError | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [content, setContent] =
    useState(initialContent);
  const [replyTarget, setReplyTarget] =
    useState<Comment | null>(null);
  const [submitting, setSubmitting] =
    useState(false);
  const [submitError, setSubmitError] =
    useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] =
    useState<string | null>(null);
  const submittingRef = useRef(false);

  useEffect(() => {
    let active = true;

    async function loadComments() {
      setLoading(true);
      setLoadError(null);

      try {
        const result = await getTaskComments(
          taskId,
          { page, pageSize },
        );

        if (!active) {
          return;
        }

        setCommentData(result);
        setLoading(false);
      } catch (error: unknown) {
        if (!active) {
          return;
        }

        const nextError =
          getCommentsLoadError(error);

        if (nextError.unauthorized) {
          onUnauthorized();
          return;
        }

        setLoadError(nextError);
        setLoading(false);
      }
    }

    void loadComments();

    return () => {
      active = false;
    };
  }, [
    onUnauthorized,
    page,
    pageSize,
    refreshKey,
    reloadKey,
    taskId,
  ]);

  const pagination = commentData?.pagination;
  const totalPages =
    pagination === undefined ||
    pagination.total_pages === 0
      ? 1
      : pagination.total_pages;

  const trimmedContentLength =
    content.trim().length;

  async function handleSubmit(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (submittingRef.current) {
      return;
    }

    const validationError =
      validateCommentContent(content);

    if (validationError !== null) {
      setSubmitError(validationError);
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      const createdComment =
        await createTaskComment(taskId, {
          content: content.trim(),
          parentId:
            replyTarget?.comment_id ?? null,
        });

      const previousTotal =
        commentData?.pagination.total ?? 0;
      const nextTotal = previousTotal + 1;
      const nextTotalPages = Math.max(
        1,
        Math.ceil(nextTotal / pageSize),
      );

      if (
        commentData !== null &&
        page === nextTotalPages
      ) {
        setCommentData({
          ...commentData,
          comments: [
            ...commentData.comments,
            createdComment,
          ],
          pagination: {
            ...commentData.pagination,
            total: nextTotal,
            total_pages: nextTotalPages,
          },
        });
      } else if (page !== nextTotalPages) {
        setPage(nextTotalPages);
      } else {
        setReloadKey((value) => value + 1);
      }

      setContent("");
      setReplyTarget(null);
      setSubmitSuccess(
        createdComment.parent_id === null
          ? "コメントを投稿しました"
          : "返信を投稿しました",
      );
      onCompleted?.();
    } catch (error: unknown) {
      const nextError =
        getCommentSubmitError(error);

      if (nextError.unauthorized) {
        onUnauthorized();
        return;
      }

      setSubmitError(nextError.message);
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  return (
    <section
      aria-label={`画像${imageId}のコメント`}
      className="border-b border-slate-200 bg-slate-50 px-5 py-5 sm:px-8"
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-bold text-slate-900">
            コメント
          </h3>
          <p className="text-sm text-slate-500">
            全{pagination?.total ?? 0}件
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label
            htmlFor={`comment-page-size-${taskId}`}
            className="text-sm font-semibold text-slate-600"
          >
            表示件数
          </label>
          <select
            id={`comment-page-size-${taskId}`}
            value={pageSize}
            disabled={loading}
            onChange={(event) => {
              setPageSize(
                Number(event.target.value) as TaskCommentsPageSize,
              );
              setPage(1);
            }}
            className="min-h-9 rounded-lg border border-slate-300 bg-white px-2 text-sm disabled:cursor-wait disabled:bg-slate-100"
          >
            <option value={10}>10件</option>
            <option value={50}>50件</option>
            <option value={100}>100件</option>
          </select>
        </div>
      </div>

      <form
        onSubmit={(event) => {
          void handleSubmit(event);
        }}
        className="mb-5 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
      >
        {submitSuccess !== null && (
          <div className="mb-3">
            <FeedbackMessage message={submitSuccess} />
          </div>
        )}
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <label
            htmlFor={`comment-content-${taskId}`}
            className="font-semibold text-slate-900"
          >
            {replyTarget === null
              ? "新しいコメント"
              : `コメント #${replyTarget.comment_id} へ返信`}
          </label>

          {replyTarget !== null && (
            <button
              type="button"
              disabled={submitting}
              onClick={() => {
                setReplyTarget(null);
                setSubmitError(null);
              }}
              className="text-sm font-semibold text-blue-700 hover:text-blue-900 disabled:cursor-not-allowed disabled:text-slate-400"
            >
              返信を取り消す
            </button>
          )}
        </div>

        {replyTarget !== null && (
          <p className="mb-3 line-clamp-2 rounded-lg bg-violet-50 px-3 py-2 text-sm text-violet-800">
            {replyTarget.user_name}: {replyTarget.content}
          </p>
        )}

        <textarea
          id={`comment-content-${taskId}`}
          value={content}
          rows={4}
          autoFocus={focusKey > 0}
          disabled={submitting}
          aria-describedby={`comment-content-help-${taskId}`}
          aria-invalid={submitError !== null}
          onChange={(event) => {
            setContent(event.target.value);
            setSubmitError(null);
          }}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              (event.shiftKey || event.ctrlKey)
            ) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder="コメントを入力してください"
          className="w-full resize-y rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-inner placeholder:text-slate-400 disabled:cursor-wait disabled:bg-slate-100"
        />

        <p className="mt-1 text-xs text-slate-500">
          Shift+Enter または Ctrl+Enter で送信
        </p>

        <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p
              id={`comment-content-help-${taskId}`}
              className={`text-xs ${
                trimmedContentLength > COMMENT_MAX_LENGTH
                  ? "font-semibold text-red-700"
                  : "text-slate-500"
              }`}
            >
              前後の空白を除いて{trimmedContentLength} / {COMMENT_MAX_LENGTH}文字
            </p>

            {submitError !== null && (
              <p
                role="alert"
                className="mt-1 text-sm font-medium text-red-700"
              >
                {submitError}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="min-h-10 rounded-lg bg-blue-600 px-5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-wait disabled:bg-slate-400"
          >
            {submitting
              ? "送信中..."
              : replyTarget === null
                ? "投稿する"
                : "返信する"}
          </button>
        </div>
      </form>

      {loading ? (
        <LoadingState
          message="コメントを読み込み中..."
          compact
        />
      ) : loadError !== null ? (
        <ErrorState
          message={loadError.message}
          compact
          onRetry={
            loadError.retryable
              ? () => {
                  setReloadKey((value) => value + 1);
                }
              : undefined
          }
        />
      ) : commentData === null ||
        commentData.comments.length === 0 ? (
        <EmptyState
          message="コメントはまだありません"
          compact
        />
      ) : (
        <ol className="grid gap-3">
          {commentData.comments.map((comment) => (
            <li
              key={comment.comment_id}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold text-slate-900">
                  {comment.user_name}
                </p>
                <p className="text-xs text-slate-500">
                  コメント #{comment.comment_id}
                </p>
              </div>

              {comment.parent_id !== null && (
                <p className="mt-2 inline-flex rounded-full bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700">
                  コメント #{comment.parent_id} への返信
                </p>
              )}

              <p className="mt-3 whitespace-pre-wrap break-words text-sm text-slate-800">
                {comment.content}
              </p>

              <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500">
                <div className="flex gap-1">
                  <dt>作成:</dt>
                  <dd>{formatDateTime(comment.created_at)}</dd>
                </div>
                <div className="flex gap-1">
                  <dt>更新:</dt>
                  <dd>{formatDateTime(comment.updated_at)}</dd>
                </div>
              </dl>

              <button
                type="button"
                disabled={submitting}
                onClick={() => {
                  setReplyTarget(comment);
                  setSubmitError(null);
                }}
                className="mt-3 rounded-lg px-3 py-1.5 text-sm font-semibold text-blue-700 hover:bg-blue-50 disabled:cursor-not-allowed disabled:text-slate-400"
              >
                このコメントに返信
              </button>
            </li>
          ))}
        </ol>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          disabled={loading}
          onClick={() => {
            setReloadKey((value) => value + 1);
          }}
          className="min-h-9 rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 hover:border-blue-300 hover:text-blue-700 disabled:cursor-wait disabled:bg-slate-100"
        >
          再読み込み
        </button>

        <nav
          aria-label={`画像${imageId}のコメントページ移動`}
          className="flex items-center gap-3"
        >
          <button
            type="button"
            disabled={page <= 1 || loading}
            onClick={() => {
              setPage((value) => value - 1);
            }}
            className="min-h-9 rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
          >
            前へ
          </button>
          <span className="min-w-20 text-center text-sm font-semibold text-slate-600">
            {page} / {totalPages}
          </span>
          <button
            type="button"
            disabled={
              pagination === undefined ||
              pagination.total_pages === 0 ||
              page >= pagination.total_pages ||
              loading
            }
            onClick={() => {
              setPage((value) => value + 1);
            }}
            className="min-h-9 rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
          >
            次へ
          </button>
        </nav>
      </div>
    </section>
  );
}
