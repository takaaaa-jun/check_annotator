"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  calculateProgress,
  getCompletedCount,
} from "@/src/features/groups/progress";
import { getCurrentUser } from "@/src/lib/api/auth";
import { ApiError } from "@/src/lib/api/client";
import type {
  CurrentUser,
  UserGroupsResponse,
} from "@/src/lib/api/types";
import { getUserGroups } from "@/src/lib/api/users";
import {
  EmptyState,
  LoadingState,
} from "@/src/components/async-state";

type GroupsPageClientProps = {
  userId: number;
};

type LoadError = {
  message: string;
  retryable: boolean;
};

function toLoadError(error: unknown): LoadError {
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
        message: "対象のユーザーが見つかりません",
        retryable: false,
      };

    case 422:
      return {
        message: "指定されたユーザーIDが正しくありません",
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
          error.message || "APIとの通信に失敗しました",
        retryable: true,
      };
  }
}

export function GroupsPageClient({
  userId,
}: GroupsPageClientProps) {
  const router = useRouter();

  const [currentUser, setCurrentUser] =
    useState<CurrentUser | null>(null);

  const [data, setData] =
    useState<UserGroupsResponse | null>(null);

  const [loading, setLoading] = useState(true);

  const [loadError, setLoadError] =
    useState<LoadError | null>(null);

  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;

    async function loadGroups() {
      setLoading(true);
      setLoadError(null);

      try {
        const authenticatedUser =
          await getCurrentUser();

        if (!active) {
          return;
        }

        setCurrentUser(authenticatedUser);

        const isAdmin =
          authenticatedUser.role_name === "admin";

        /*
         * 一般ユーザーがURL上のuser_idを書き換えた場合は、
         * グループAPIを呼び出す前に本人の画面へ戻す。
         *
         * 管理者の場合は、指定ユーザーの参照を許可する。
         */
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

        setData(groupsData);
        setLoading(false);
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

        setLoadError(toLoadError(error));
        setLoading(false);
      }
    }

    void loadGroups();

    return () => {
      active = false;
    };
  }, [reloadKey, router, userId]);

  if (loading) {
    return (
      <main className="mx-auto max-w-5xl p-8">
        <LoadingState />
      </main>
    );
  }

  if (loadError !== null) {
    return (
      <main className="mx-auto max-w-5xl p-8">
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-6"
        >
          <p className="text-red-700">
            {loadError.message}
          </p>

          <div className="mt-4 flex flex-wrap gap-4">
            {loadError.retryable && (
              <button
                type="button"
                onClick={() => {
                  setReloadKey(
                    (currentValue) =>
                      currentValue + 1,
                  );
                }}
                className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
              >
                再試行
              </button>
            )}

            {currentUser !== null && (
              <Link
                href={`/mypage/${currentUser.user_id}/groups`}
                className="rounded border border-gray-300 px-4 py-2 hover:bg-gray-50"
              >
                自分のグループ一覧へ戻る
              </Link>
            )}
          </div>
        </div>
      </main>
    );
  }

  if (data === null || currentUser === null) {
    return null;
  }

  return (
    <main className="mx-auto max-w-5xl p-8">
      <header className="mb-8">
        <p className="mb-2 text-sm text-gray-600">
          ログイン中: {currentUser.user_name}
        </p>

        <h1 className="text-2xl font-bold">
          {data.user.user_name} の担当グループ
        </h1>
      </header>

      {data.groups.length === 0 ? (
        <EmptyState message="担当グループはありません" />
      ) : (
        <div className="grid gap-6">
          {data.groups.map((group) => {
            const completedCount =
              getCompletedCount(
                group.state_counts,
              );

            const progress =
              calculateProgress(
                completedCount,
                group.total_count,
              );

            return (
              <section
                key={group.group_id}
                className="rounded-lg border bg-white p-6 shadow-sm"
              >
                <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
                  <h2 className="text-xl font-semibold">
                    {group.group_name}
                  </h2>

                  <Link
                    href={`/mypage/${userId}/groups/${group.group_id}`}
                    className="text-sm text-blue-700 hover:underline"
                  >
                    グループ詳細へ
                  </Link>
                </div>

                <dl className="mb-5 grid gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="font-medium text-gray-700">
                      画像ID範囲
                    </dt>

                    <dd className="text-gray-600">
                      {group.image_id_min ?? "-"} ～{" "}
                      {group.image_id_max ?? "-"}
                    </dd>
                  </div>

                  <div>
                    <dt className="font-medium text-gray-700">
                      総タスク数
                    </dt>

                    <dd className="text-gray-600">
                      {group.total_count}件
                    </dd>
                  </div>
                </dl>

                <div className="mb-5">
                  <div className="mb-2 flex justify-between text-sm text-gray-700">
                    <span>
                      進捗率: {progress}%
                    </span>

                    <span>
                      {completedCount} /{" "}
                      {group.total_count}件
                    </span>
                  </div>

                  <div
                    role="progressbar"
                    aria-label={`${group.group_name}の進捗率`}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={progress}
                    className="h-3 w-full overflow-hidden rounded-full bg-gray-200"
                  >
                    <div
                      className="h-full rounded-full bg-blue-600"
                      style={{
                        width: `${progress}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {group.state_counts.map(
                    (state) => (
                      <div
                        key={state.state_id}
                        className="rounded bg-gray-50 p-3 text-center"
                      >
                        <p className="text-xs text-gray-600">
                          {state.state_name}
                        </p>

                        <p className="mt-1 font-semibold">
                          {state.count}件
                        </p>
                      </div>
                    ),
                  )}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </main>
  );
}
