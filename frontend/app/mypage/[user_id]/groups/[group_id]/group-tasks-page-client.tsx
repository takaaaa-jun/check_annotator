"use client";

import Link from "next/link";
import {
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
import {
  getTaskStateUpdateError,
  replaceUpdatedTask,
} from "@/src/features/tasks/state-update";
import { TaskFilters } from "@/src/features/tasks/task-filters";
import {
  TaskTable,
  type CommentComposer,
} from "@/src/features/tasks/task-table";
import { FeedbackMessage } from "@/src/components/feedback-message";
import { LoadingState } from "@/src/components/async-state";

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

  const groupReady = group !== null;

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
    useState<CommentComposer | null>(null);

  const [operationMessage, setOperationMessage] =
    useState<string | null>(null);

  const updatingTaskIdsRef =
    useRef(new Set<number>());

  const taskScrollRef =
    useRef<HTMLDivElement | null>(null);

  const taskRowRefs =
    useRef(new Map<number, HTMLTableRowElement>());

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
    if (!groupReady) {
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
        setActiveTaskId(null);
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
    groupReady,
    groupId,
    page,
    pageSize,
    router,
    stateId,
    tasksReloadKey,
    userId,
  ]);

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
      scrollCommentEditorIntoView(taskId);
    } else {
      setOpenCommentsTaskId(null);
      setCommentComposer(null);
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
      setGroup((currentGroup) =>
        currentGroup === null
          ? null
          : {
              ...currentGroup,
              state_counts:
                currentGroup.state_counts.map((state) => ({
                  ...state,
                  count:
                    state.state_id === currentTask.state_id
                      ? Math.max(0, state.count - 1)
                      : state.state_id === updatedTask.state_id
                        ? state.count + 1
                        : state.count,
                })),
            },
      );
      if (opensCommentComposer) {
        setActiveTaskId(taskId);
        scrollCommentEditorIntoView(taskId);
      } else if (updatedTask.state_name === "完了") {
        highlightTaskAndAdvance(taskId);
      } else {
        setActiveTaskId(taskId);
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

  function highlightTaskAndAdvance(taskId: number) {
    setActiveTaskId(taskId);

    requestAnimationFrame(() => {
      const container = taskScrollRef.current;
      const tasks = taskData?.tasks ?? [];
      const taskIndex = tasks.findIndex(
        (task) => task.task_id === taskId,
      );
      const nextTaskId =
        tasks[taskIndex + 1]?.task_id ?? taskId;
      const row = taskRowRefs.current.get(nextTaskId);

      if (container === null || row === undefined) {
        return;
      }

      container.scrollTo({
        top: row.offsetTop - row.clientHeight,
        behavior: "smooth",
      });
    });
  }

  function scrollCommentEditorIntoView(taskId: number) {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const container = taskScrollRef.current;
        const commentRow = document.getElementById(
          `task-comments-${taskId}`,
        );

        if (container === null || commentRow === null) {
          return;
        }

        container.scrollTo({
          top: commentRow.offsetTop - 64,
          behavior: "smooth",
        });
      });
    });
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
    <main className="h-[calc(100vh-65px)] overflow-hidden px-4 sm:px-6 lg:px-8">
      <div className="mx-auto grid h-full max-w-[1600px] grid-cols-[15rem_minmax(0,1fr)] gap-5 xl:grid-cols-[18rem_minmax(0,1fr)]">
      <aside className="min-h-0 overflow-y-auto py-5">
      <div className="mb-4">
        <Link
          href={`/mypage/${userId}/groups`}
          className="inline-flex items-center rounded-lg px-2 py-1 text-base font-bold text-blue-700 hover:bg-blue-50"
        >
          ← グループ一覧へ戻る
        </Link>
      </div>

      <header className="mb-5">
        <p className="mb-2 text-base font-semibold text-blue-700">
          ログイン中: {" "}
          <span className="text-lg font-extrabold text-blue-950">
            {currentUser.user_name}
          </span>
        </p>

        <h1 className="text-4xl font-extrabold tracking-tight text-slate-950">
          {group.group_name}
        </h1>

        <p className="mt-2 text-lg font-bold text-slate-700">
          {currentUser.role_name === "admin"
            ? `${userId}番ユーザーのタスク一覧`
            : "担当タスク一覧"}
        </p>
      </header>

      <div className="mb-5 min-h-20">
        {operationMessage !== null && (
          <FeedbackMessage message={operationMessage} />
        )}
      </div>

      <TaskFilters
        group={group}
        stateId={stateId}
        pageSize={pageSize}
        disabled={tasksLoading}
        onStateChange={(nextStateId) => {
          setStateId(nextStateId);
          setPage(1);
        }}
        onPageSizeChange={(nextPageSize) => {
          setPageSize(nextPageSize);
          setPage(1);
        }}
      />
      </aside>

      <div className="flex min-h-0 flex-col py-5">

      {tasksError !== null && (
        <div
          role="alert"
          className="mb-3 shrink-0 rounded-lg border border-red-200 bg-red-50 p-4"
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

      <TaskTable
        taskData={taskData}
        stateCounts={group.state_counts}
        loading={tasksLoading}
        activeTaskId={activeTaskId}
        openCommentsTaskId={openCommentsTaskId}
        commentComposer={commentComposer}
        updatingTaskIds={updatingTaskIds}
        taskUpdateErrors={taskUpdateErrors}
        scrollRef={taskScrollRef}
        onTaskRowRef={(taskId, element) => {
          if (element === null) {
            taskRowRefs.current.delete(taskId);
          } else {
            taskRowRefs.current.set(taskId, element);
          }
        }}
        onStateSelect={(task, state) => {
          void handleTaskStateUpdate(
            task.task_id,
            state.state_id,
            state.state_name,
          );
        }}
        onToggleComments={(taskId) => {
          setOpenCommentsTaskId((currentTaskId) =>
            currentTaskId === taskId ? null : taskId,
          );
          setCommentComposer(null);
        }}
        onUnauthorized={handleUnauthorized}
        onCommentCompleted={highlightTaskAndAdvance}
      />

      <nav
        aria-label="タスク一覧のページ移動"
        className="mt-3 flex shrink-0 items-center justify-center gap-4"
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
      </div>
      </div>
    </main>
  );
}
