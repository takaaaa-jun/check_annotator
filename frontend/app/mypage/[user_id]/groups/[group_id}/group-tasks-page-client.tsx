"use client";

import Link from "next/link";
import {
  useEffect,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser } from "@/src/lib/api/auth";
import { ApiError } from "@/src/lib/api/client";
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

  if (metadataLoading) {
    return (
      <main className="mx-auto max-w-6xl p-8">
        <p
          role="status"
          aria-live="polite"
          className="text-center text-gray-600"
        >
          グループ情報を読み込み中...
        </p>
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
    <main className="mx-auto max-w-6xl p-8">
      <div className="mb-4">
        <Link
          href={`/mypage/${userId}/groups`}
          className="text-sm text-blue-700 hover:underline"
        >
          ← グループ一覧へ戻る
        </Link>
      </div>

      <header className="mb-8">
        <p className="mb-2 text-sm text-gray-600">
          ログイン中: {currentUser.user_name}
        </p>

        <h1 className="text-2xl font-bold">
          {group.group_name}
        </h1>

        <p className="mt-2 text-gray-600">
          {currentUser.role_name === "admin"
            ? `${userId}番ユーザーのタスク一覧`
            : "担当タスク一覧"}
        </p>
      </header>

      <section
        aria-labelledby="task-filter-heading"
        className="mb-6 rounded-lg border bg-white p-4"
      >
        <h2
          id="task-filter-heading"
          className="mb-4 text-lg font-semibold"
        >
          表示条件
        </h2>

        <div className="flex flex-wrap gap-6">
          <div>
            <label
              htmlFor="state-filter"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              状態
            </label>

            <select
              id="state-filter"
              value={stateId ?? ""}
              onChange={handleStateChange}
              disabled={tasksLoading}
              className="rounded border border-gray-300 bg-white px-3 py-2"
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

          <div>
            <label
              htmlFor="page-size"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              1ページの表示件数
            </label>

            <select
              id="page-size"
              value={pageSize}
              onChange={handlePageSizeChange}
              disabled={tasksLoading}
              className="rounded border border-gray-300 bg-white px-3 py-2"
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
        className="overflow-hidden rounded-lg border bg-white"
      >
        <div className="flex flex-wrap items-center justify-between gap-4 border-b p-4">
          <h2
            id="task-list-heading"
            className="text-lg font-semibold"
          >
            タスク一覧
          </h2>

          <p className="text-sm text-gray-600">
            全{pagination?.total ?? 0}件
          </p>
        </div>

        {tasksLoading ? (
          <p
            role="status"
            aria-live="polite"
            className="p-8 text-center text-gray-600"
          >
            タスクを読み込み中...
          </p>
        ) : taskData === null ||
          taskData.tasks.length === 0 ? (
          <p className="p-8 text-center text-gray-600">
            該当するタスクはありません
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead className="bg-gray-50">
                <tr>
                  <th
                    scope="col"
                    className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700"
                  >
                    画像ID
                  </th>

                  <th
                    scope="col"
                    className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700"
                  >
                    状態
                  </th>

                  <th
                    scope="col"
                    className="border-b px-4 py-3 text-left text-sm font-semibold text-gray-700"
                  >
                    最終更新日時
                  </th>
                </tr>
              </thead>

              <tbody>
                {taskData.tasks.map(
                  (task) => (
                    <tr
                      key={task.task_id}
                      className="hover:bg-gray-50"
                    >
                      <td className="border-b px-4 py-3">
                        {task.image_id}
                      </td>

                      <td className="border-b px-4 py-3">
                        <span className="inline-block rounded bg-gray-100 px-2 py-1 text-sm">
                          {task.state_name}
                        </span>
                      </td>

                      <td className="border-b px-4 py-3 text-sm text-gray-600">
                        {formatDateTime(
                          task.updated_at,
                        )}
                      </td>
                    </tr>
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
          className="rounded border border-gray-300 px-4 py-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          前へ
        </button>

        <span className="text-sm text-gray-700">
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
          className="rounded border border-gray-300 px-4 py-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          次へ
        </button>
      </nav>
    </main>
  );
}