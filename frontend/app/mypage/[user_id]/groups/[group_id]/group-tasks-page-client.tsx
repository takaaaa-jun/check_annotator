"use client";

import Link from "next/link";
import {
  Fragment,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser } from "@/src/lib/api/auth";
import { ApiError } from "@/src/lib/api/client";
import { updateTaskState } from "@/src/lib/api/tasks";
import type {
  CurrentUser,
  GroupProgress,
  GroupTasksResponse,
} from "@/src/lib/api/types";
import {
  getGroupTasks,
  getUserGroups,
  type GroupTasksPageSize,
} from "@/src/lib/api/users";
import { formatDateTime } from "@/src/lib/format/date-time";
import {
  getTaskStateUpdateError,
  replaceUpdatedTask,
} from "@/src/features/tasks/state-update";
import { TaskCommentsPanel } from "@/src/features/tasks/task-comments-panel";
import { FeedbackMessage } from "@/src/components/feedback-message";
import {
  EmptyState,
  LoadingState,
} from "@/src/components/async-state";

type GroupTasksPageClientProps = {
  userId: number;
  groupId: number;
};

type LoadError = {
  message: string;
  retryable: boolean;
};

function toLoadError(
  error: unknown,
): LoadError {
  if (!(error instanceof ApiError)) {
    return {
      message: "予期しないエラーが発生しました",
      retryable: true,
    };
  }

  switch (error.status) {
    case 403:
      return {
        message: "アクセス権限がありません",
        retryable: false,
      };

    case 404:
      return {
        message:
          "対象のグループまたは状態が見つかりません",
        retryable: false,
      };

    case 422:
      return {
        message:
          "ページまたは絞り込み条件が正しくありません",
        retryable: false,
      };

    case 500:
      return {
        message:
          "サーバーでエラーが発生しました。時間をおいて再度お試しください",
        retryable: true,
      };

    default:
      return {
        message:
          error.message ||
          "APIとの通信に失敗しました",
        retryable: true,
      };
  }
}

export function GroupTasksPageClient({
  userId,
  groupId,
}: GroupTasksPageClientProps) {
  const router = useRouter();

  const [currentUser, setCurrentUser] =
    useState<CurrentUser | null>(null);

  const [group, setGroup] =
    useState<GroupProgress | null>(null);

  const [taskData, setTaskData] =
    useState<GroupTasksResponse | null>(null);

  const [stateId, setStateId] =
    useState<number | undefined>(undefined);

  const [page, setPage] = useState(1);

  const [pageSize, setPageSize] =
    useState<GroupTasksPageSize>(50);

  const [metadataLoading, setMetadataLoading] =
    useState(true);

  const [tasksLoading, setTasksLoading] =
    useState(false);

  const [metadataError, setMetadataError] =
    useState<LoadError | null>(null);

  const [tasksError, setTasksError] =
    useState<LoadError | null>(null);

  const [updatingTaskIds, setUpdatingTaskIds] =
    useState<Set<number>>(() => new Set());

  const [taskUpdateErrors, setTaskUpdateErrors] =
    useState<Record<number, string>>({});

  const [openCommentsTaskId, setOpenCommentsTaskId] =
    useState<number | null>(null);

  const [activeTaskId, setActiveTaskId] =
    useState<number | null>(null);

  const [commentComposer, setCommentComposer] =
    useState<{
      taskId: number;
      initialContent: string;
      focusKey: number;
    } | null>(null);

  const [operationMessage, setOperationMessage] =
    useState<string | null>(null);

  const updatingTaskIdsRef =
    useRef(new Set<number>());

  const handleUnauthorized = useCallback(() => {
    router.replace("/login");
  }, [router]);

  const [
    metadataReloadKey,
    setMetadataReloadKey,
  ] = useState(0);

  const [
    tasksReloadKey,
    setTasksReloadKey,
  ] = useState(0);

  /*
   * 認証情報とグループ情報を取得する。
   *
   * グループ情報に含まれるstate_countsを、
   * 状態フィルターの選択肢として使用する。
   */
  useEffect(() => {
    let active = true;

    async function loadMetadata() {
      setMetadataLoading(true);
      setMetadataError(null);
      setGroup(null);
      setTaskData(null);

      try {
        const authenticatedUser =
          await getCurrentUser();

        if (!active) {
          return;
        }

        setCurrentUser(authenticatedUser);

        const isAdmin =
          authenticatedUser.role_name === "admin";

        if (
          !isAdmin &&
          authenticatedUser.user_id !== userId
        ) {
          router.replace(
            `/mypage/${authenticatedUser.user_id}/groups`,
          );
          return;
        }

        const groupsData =
          await getUserGroups(userId);

        if (!active) {
          return;
        }

        const selectedGroup =
          groupsData.groups.find(
            (item) =>
              item.group_id === groupId,
          );

        if (selectedGroup === undefined) {
          setMetadataError({
            message:
              "対象のグループが見つかりません",
            retryable: false,
          });
          setMetadataLoading(false);
          return;
        }

        setGroup(selectedGroup);
        setMetadataLoading(false);
      } catch (error: unknown) {
        if (!active) {
          return;
        }

        if (
          error instanceof ApiError &&
          error.status === 401
        ) {
          router.replace("/login");
          return;
        }

        setMetadataError(
          toLoadError(error),
        );
        setMetadataLoading(false);
      }
    }

    void loadMetadata();

    return () => {
      active = false;
    };
  }, [
    groupId,
    metadataReloadKey,
    router,
    userId,
  ]);

  /*
   * グループ情報の取得後に、タスク一覧を取得する。
   *
   * 状態、ページ、ページサイズを変更した場合は、
   * タスク一覧だけを再取得する。
   */
  useEffect(() => {
    if (group === null) {
      return;
    }

    let active = true;

    async function loadTasks() {
      setTasksLoading(true);
      setTasksError(null);

      try {
        const result = await getGroupTasks(
          userId,
          groupId,
          {
            stateId,
            page,
            pageSize,
          },
        );

        if (!active) {
          return;
        }

        setTaskData(result);
        setActiveTaskId(
          result.tasks[0]?.task_id ?? null,
        );
        setOpenCommentsTaskId(null);
        setCommentComposer(null);
        setTaskUpdateErrors({});
        setTasksLoading(false);
      } catch (error: unknown) {
        if (!active) {
          return;
        }

        if (
          error instanceof ApiError &&
          error.status === 401
        ) {
          router.replace("/login");
          return;
        }

        setTasksError(toLoadError(error));
        setTasksLoading(false);
      }
    }

    void loadTasks();

    return () => {
      active = false;
    };
  }, [
    group,
    groupId,
    page,
    pageSize,
    router,
    stateId,
    tasksReloadKey,
    userId,
  ]);

  function handleStateChange(
    event: React.ChangeEvent<HTMLSelectElement>,
  ) {
    const value = event.target.value;

    setStateId(
      value === ""
        ? undefined
        : Number(value),
    );

    setPage(1);
  }

  function handlePageSizeChange(
    event: React.ChangeEvent<HTMLSelectElement>,
  ) {
    setPageSize(
      Number(
        event.target.value,
      ) as GroupTasksPageSize,
    );

    setPage(1);
  }

  async function handleTaskStateUpdate(
    taskId: number,
    nextStateId: number,
    nextStateName: string,
  ) {
    const opensCommentComposer =
      nextStateName === "コメント" ||
      nextStateName === "付与予定ラベル";

    if (opensCommentComposer) {
      setOpenCommentsTaskId(taskId);
      setCommentComposer((currentValue) => ({
        taskId,
        initialContent:
          nextStateName === "付与予定ラベル"
            ? "付与予定ラベル："
            : "",
        focusKey:
          (currentValue?.focusKey ?? 0) + 1,
      }));
    }

    if (updatingTaskIdsRef.current.has(taskId)) {
      return;
    }

    const currentTask = taskData?.tasks.find(
      (task) => task.task_id === taskId,
    );

    if (
      currentTask === undefined ||
      currentTask.state_id === nextStateId
    ) {
      return;
    }

    updatingTaskIdsRef.current.add(taskId);
    setUpdatingTaskIds(
      new Set(updatingTaskIdsRef.current),
    );
    setTaskUpdateErrors((currentErrors) => {
      const nextErrors = { ...currentErrors };
      delete nextErrors[taskId];
      return nextErrors;
    });
    setOperationMessage(null);

    try {
      const updatedTask =
        await updateTaskState(
          taskId,
          nextStateId,
        );

      setTaskData((currentTaskData) =>
        currentTaskData === null
          ? null
          : replaceUpdatedTask(
              currentTaskData,
              updatedTask,
            ),
      );
      setOperationMessage(
        `画像${updatedTask.image_id}の状態を「${updatedTask.state_name}」へ更新しました`,
      );
      if (!opensCommentComposer) {
        moveToNextTask(taskId);
      }
    } catch (error: unknown) {
      setTaskUpdateErrors((currentErrors) => ({
        ...currentErrors,
        [taskId]: getTaskStateUpdateError(error),
      }));
    } finally {
      updatingTaskIdsRef.current.delete(taskId);
      setUpdatingTaskIds(
        new Set(updatingTaskIdsRef.current),
      );
    }
  }

  function moveToNextTask(taskId: number) {
    const tasks = taskData?.tasks ?? [];
    const currentIndex = tasks.findIndex(
      (task) => task.task_id === taskId,
    );
    const nextTask = tasks[currentIndex + 1];

    setActiveTaskId(
      nextTask?.task_id ?? taskId,
    );
  }

  function getStateButtonClass(
    stateName: string,
    selected: boolean,
  ): string {
    const colorClass =
      stateName === "未着手"
        ? "border-red-300 bg-red-50 text-red-800 hover:bg-red-100"
        : stateName === "完了"
          ? "border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100"
          : stateName === "付与予定ラベル"
            ? "border-indigo-300 bg-indigo-50 text-indigo-800 hover:bg-indigo-100"
            : "border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100";

    return `min-h-10 whitespace-nowrap rounded-lg border px-3 text-sm font-bold shadow-sm disabled:cursor-wait disabled:opacity-50 ${colorClass} ${
      selected
        ? "ring-2 ring-slate-700 ring-offset-2"
        : ""
    }`;
  }

  if (metadataLoading) {
    return (
      <main className="mx-auto max-w-6xl p-8">
        <LoadingState message="グループ情報を読み込み中..." />
      </main>
    );
  }

  if (metadataError !== null) {
    return (
      <main className="mx-auto max-w-6xl p-8">
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-6"
        >
          <p className="text-red-700">
            {metadataError.message}
          </p>

          <div className="mt-4 flex flex-wrap gap-4">
            {metadataError.retryable && (
              <button
                type="button"
                onClick={() => {
                  setMetadataReloadKey(
                    (currentValue) =>
                      currentValue + 1,
                  );
                }}
                className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
              >
                再試行
              </button>
            )}

            <Link
              href={`/mypage/${userId}/groups`}
              className="rounded border border-gray-300 px-4 py-2 hover:bg-gray-50"
            >
              グループ一覧へ戻る
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (
    currentUser === null ||
    group === null
  ) {
    return null;
  }

  const pagination = taskData?.pagination;

  const totalPages =
    pagination === undefined ||
    pagination.total_pages === 0
      ? 1
      : pagination.total_pages;

  const canMoveToPreviousPage =
    page > 1 && !tasksLoading;

  const canMoveToNextPage =
    pagination !== undefined &&
    pagination.total_pages > 0 &&
    page < pagination.total_pages &&
    !tasksLoading;

  return (
    <main className="mx-auto min-h-[calc(100vh-65px)] max-w-6xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
      <div className="mb-4">
        <Link
          href={`/mypage/${userId}/groups`}
          className="inline-flex items-center rounded-lg px-2 py-1 text-sm font-semibold text-blue-700 hover:bg-blue-50"
        >
          ← グループ一覧へ戻る
        </Link>
      </div>

      <header className="mb-8">
        <p className="mb-2 text-sm font-medium text-blue-700">
          ログイン中: {currentUser.user_name}
        </p>

        <h1 className="text-3xl font-bold tracking-tight text-slate-950">
          {group.group_name}
        </h1>

        <p className="mt-2 text-slate-500">
          {currentUser.role_name === "admin"
            ? `${userId}番ユーザーのタスク一覧`
            : "担当タスク一覧"}
        </p>
      </header>

      {operationMessage !== null && (
        <div className="mb-6">
          <FeedbackMessage message={operationMessage} />
        </div>
      )}

      <section
        aria-labelledby="task-filter-heading"
        className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_30px_rgba(15,23,42,0.04)] sm:p-6"
      >
        <h2
          id="task-filter-heading"
          className="mb-5 text-lg font-bold text-slate-900"
        >
          表示条件
        </h2>

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="grid gap-2">
            <label
              htmlFor="state-filter"
              className="block text-sm font-semibold text-slate-700"
            >
              状態
            </label>

            <select
              id="state-filter"
              value={stateId ?? ""}
              onChange={handleStateChange}
              disabled={tasksLoading}
              className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-800 shadow-sm hover:border-slate-400 disabled:cursor-wait disabled:bg-slate-50"
            >
              <option value="">
                すべて
              </option>

              {group.state_counts.map(
                (state) => (
                  <option
                    key={state.state_id}
                    value={state.state_id}
                  >
                    {state.state_name}
                    （{state.count}件）
                  </option>
                ),
              )}
            </select>
          </div>

          <div className="grid gap-2">
            <label
              htmlFor="page-size"
              className="block text-sm font-semibold text-slate-700"
            >
              1ページの表示件数
            </label>

            <select
              id="page-size"
              value={pageSize}
              onChange={handlePageSizeChange}
              disabled={tasksLoading}
              className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-800 shadow-sm hover:border-slate-400 disabled:cursor-wait disabled:bg-slate-50"
            >
              <option value={10}>
                10件
              </option>

              <option value={50}>
                50件
              </option>

              <option value={100}>
                100件
              </option>
            </select>
          </div>
        </div>
      </section>

      {tasksError !== null && (
        <div
          role="alert"
          className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4"
        >
          <p className="text-red-700">
            {tasksError.message}
          </p>

          {tasksError.retryable && (
            <button
              type="button"
              onClick={() => {
                setTasksReloadKey(
                  (currentValue) =>
                    currentValue + 1,
                );
              }}
              className="mt-4 rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
            >
              再試行
            </button>
          )}
        </div>
      )}

      <section
        aria-labelledby="task-list-heading"
        className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_8px_30px_rgba(15,23,42,0.05)]"
      >
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 px-5 py-4 sm:px-6">
          <h2
            id="task-list-heading"
            className="text-lg font-bold text-slate-900"
          >
            タスク一覧
          </h2>

          <p className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-600">
            全{pagination?.total ?? 0}件
          </p>
        </div>

        {tasksLoading ? (
          <LoadingState message="タスクを読み込み中..." />
        ) : taskData === null ||
          taskData.tasks.length === 0 ? (
          <div className="p-5">
            <EmptyState message="該当するタスクはありません" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead className="bg-slate-50">
                <tr>
                  <th
                    scope="col"
                    className="border-b border-slate-200 px-5 py-3.5 text-left text-xs font-bold uppercase tracking-wide text-slate-500 sm:px-6"
                  >
                    画像ID
                  </th>

                  <th
                    scope="col"
                    className="border-b border-slate-200 px-5 py-3.5 text-left text-xs font-bold uppercase tracking-wide text-slate-500 sm:px-6"
                  >
                    状態
                  </th>

                  <th
                    scope="col"
                    className="border-b border-slate-200 px-5 py-3.5 text-left text-xs font-bold uppercase tracking-wide text-slate-500 sm:px-6"
                  >
                    最終更新日時
                  </th>

                  <th
                    scope="col"
                    className="border-b border-slate-200 px-5 py-3.5 text-left text-xs font-bold uppercase tracking-wide text-slate-500 sm:px-6"
                  >
                    操作
                  </th>
                </tr>
              </thead>

              <tbody>
                {taskData.tasks.map(
                  (task) => (
                    <Fragment key={task.task_id}>
                    <tr
                      className={
                        activeTaskId === task.task_id
                          ? "bg-blue-100/80 ring-2 ring-inset ring-blue-400"
                          : "hover:bg-blue-50/50"
                      }
                    >
                      <td className="border-b border-slate-100 px-5 py-4 font-semibold text-slate-900 sm:px-6">
                        {task.image_id}
                      </td>

                      <td className="border-b border-slate-100 px-5 py-4 sm:px-6">
                        <span className="inline-flex rounded-full bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-700">
                          {task.state_name}
                        </span>
                      </td>

                      <td className="border-b border-slate-100 px-5 py-4 text-sm text-slate-600 sm:px-6">
                        {formatDateTime(
                          task.updated_at,
                        )}
                      </td>

                      <td className="border-b border-slate-100 px-5 py-4 sm:px-6">
                        <div className="flex min-w-[32rem] flex-wrap items-center gap-2">
                          {group.state_counts.map((state) => (
                          <button
                            key={state.state_id}
                            type="button"
                            aria-pressed={task.state_id === state.state_id}
                            disabled={updatingTaskIds.has(task.task_id)}
                            onClick={() => {
                              void handleTaskStateUpdate(
                                task.task_id,
                                state.state_id,
                                state.state_name,
                              );
                            }}
                            className={getStateButtonClass(
                              state.state_name,
                              task.state_id === state.state_id,
                            )}
                          >
                            {updatingTaskIds.has(task.task_id)
                              ? "更新中..."
                              : state.state_name}
                          </button>
                          ))}

                          <button
                            type="button"
                            aria-expanded={openCommentsTaskId === task.task_id}
                            aria-controls={`task-comments-${task.task_id}`}
                            onClick={() => {
                              setOpenCommentsTaskId((currentTaskId) =>
                                currentTaskId === task.task_id
                                  ? null
                                  : task.task_id,
                              );
                              setCommentComposer(null);
                            }}
                            className="min-h-10 whitespace-nowrap rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                          >
                            {openCommentsTaskId === task.task_id
                              ? "詳細を閉じる"
                              : "履歴を見る"}
                          </button>
                        </div>

                        {taskUpdateErrors[task.task_id] !== undefined && (
                          <p
                            role="alert"
                            className="mt-2 max-w-80 text-sm font-medium text-red-700"
                          >
                            {taskUpdateErrors[task.task_id]}
                          </p>
                        )}
                      </td>

                    </tr>

                    {openCommentsTaskId === task.task_id && (
                      <tr id={`task-comments-${task.task_id}`}>
                        <td colSpan={4} className="p-0">
                          <TaskCommentsPanel
                            key={`${task.task_id}-${
                              commentComposer?.taskId === task.task_id
                                ? commentComposer.focusKey
                                : 0
                            }`}
                            taskId={task.task_id}
                            imageId={task.image_id}
                            onUnauthorized={handleUnauthorized}
                            initialContent={
                              commentComposer?.taskId === task.task_id
                                ? commentComposer.initialContent
                                : ""
                            }
                            focusKey={
                              commentComposer?.taskId === task.task_id
                                ? commentComposer.focusKey
                                : 0
                            }
                            onCompleted={() => {
                              moveToNextTask(task.task_id);
                            }}
                          />
                        </td>
                      </tr>
                    )}
                    </Fragment>
                  ),
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <nav
        aria-label="タスク一覧のページ移動"
        className="mt-6 flex items-center justify-center gap-4"
      >
        <button
          type="button"
          disabled={!canMoveToPreviousPage}
          onClick={() => {
            setPage(
              (currentPage) =>
                currentPage - 1,
            );
          }}
          className="min-h-10 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm hover:border-blue-300 hover:text-blue-700 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
        >
          前へ
        </button>

        <span className="min-w-24 text-center text-sm font-semibold text-slate-600">
          {page} / {totalPages}ページ
        </span>

        <button
          type="button"
          disabled={!canMoveToNextPage}
          onClick={() => {
            setPage(
              (currentPage) =>
                currentPage + 1,
            );
          }}
          className="min-h-10 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm hover:border-blue-300 hover:text-blue-700 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
        >
          次へ
        </button>
      </nav>
    </main>
  );
}
