import {
  useEffect,
  useState,
} from "react";

import type { TaskCommentsResponse } from "../../lib/api/types";
import {
  getTaskComments,
  type TaskCommentsPageSize,
} from "../../lib/api/tasks";
import { formatDateTime } from "../../lib/format/date-time";
import {
  getCommentsLoadError,
  type CommentsLoadError,
} from "./comments";

type TaskCommentsPanelProps = {
  taskId: number;
  imageId: number;
  refreshKey?: number;
  onUnauthorized: () => void;
};

export function TaskCommentsPanel({
  taskId,
  imageId,
  refreshKey = 0,
  onUnauthorized,
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

      {loading ? (
        <p
          role="status"
          aria-live="polite"
          className="py-6 text-center text-sm text-slate-600"
        >
          コメントを読み込み中...
        </p>
      ) : loadError !== null ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4"
        >
          <p className="text-sm font-medium text-red-700">
            {loadError.message}
          </p>
          {loadError.retryable && (
            <button
              type="button"
              onClick={() => {
                setReloadKey((value) => value + 1);
              }}
              className="mt-3 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
            >
              再試行
            </button>
          )}
        </div>
      ) : commentData === null ||
        commentData.comments.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-600">
          コメントはまだありません
        </p>
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
