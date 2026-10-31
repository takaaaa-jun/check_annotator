// @vitest-environment jsdom
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GroupTasksPageClient } from "@/app/mypage/[user_id]/groups/[group_id]/group-tasks-page-client";
import { getCurrentUser } from "@/src/lib/api/auth";
import { getGroupTasks, getUserGroups } from "@/src/lib/api/users";
import { createTaskComment, getTaskComments, updateTaskState } from "@/src/lib/api/tasks";

const router = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/src/lib/api/auth", () => ({ getCurrentUser: vi.fn() }));
vi.mock("@/src/lib/api/users", () => ({ getGroupTasks: vi.fn(), getUserGroups: vi.fn() }));
vi.mock("@/src/lib/api/tasks", () => ({ createTaskComment: vi.fn(), getTaskComments: vi.fn(), updateTaskState: vi.fn() }));
vi.mock("@/src/features/categories/category-workbench", () => ({
  CategoryWorkbench: ({ imageId, embedded }: { imageId: number; embedded: boolean }) => <section aria-label={`画像${imageId}のカテゴリ確認`}>{embedded ? "行内の付与済みカテゴリ" : "ページ"}</section>,
}));

const states = [{ state_id: 1, state_name: "未着手", count: 2 }, { state_id: 2, state_name: "完了", count: 0 }, { state_id: 3, state_name: "コメント", count: 0 }];
const pagination = { page: 1, page_size: 50, total: 2, total_pages: 1 };
beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("requestAnimationFrame", vi.fn());
  vi.mocked(getCurrentUser).mockResolvedValue({ user_id: 6, user_name: "sato", role_id: 1, role_name: "user", login_at: null });
  vi.mocked(getUserGroups).mockResolvedValue({ user: { user_id: 6, user_name: "sato" }, groups: [{ group_id: 24, group_name: "04001-05000", image_id_min: 4001, image_id_max: 4002, total_count: 2, state_counts: states }] });
  vi.mocked(getGroupTasks).mockResolvedValue({ group: { group_id: 24, group_name: "04001-05000", user_id: 6, user_name: "sato" }, pagination, tasks: [4001, 4002].map((id) => ({ task_id: id, image_id: id, state_id: 1, state_name: "未着手", updated_at: "2026-10-31T00:00:00Z" })) });
  vi.mocked(getTaskComments).mockResolvedValue({ task_id: 4001, pagination: { ...pagination, total: 0 }, comments: [] });
  vi.mocked(updateTaskState).mockResolvedValue({ task_id: 4001, group_id: 24, image_id: 4001, state_id: 2, state_name: "完了", updated_at: "2026-10-31T01:00:00Z" });
  vi.mocked(createTaskComment).mockResolvedValue({ comment_id: 1, task_id: 4001, user_id: 6, user_name: "sato", parent_id: null, content: "確認しました", created_at: "2026-10-31T01:00:00Z", updated_at: "2026-10-31T01:00:00Z" });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

async function openCategories() {
  const user = userEvent.setup();
  render(<GroupTasksPageClient userId={6} groupId={24} />);
  await user.click(await screen.findByRole("button", { name: "画像4001のカテゴリを確認" }));
  return user;
}

describe("画像行でのカテゴリ確認", () => {
  it("ページ遷移せず対象行に展開し、別の画像では表示内容を切り替える", async () => {
    const user = await openCategories();
    expect(screen.getByRole("region", { name: "画像4001のカテゴリ確認" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "画像4001のカテゴリを確認" })).toHaveAttribute("aria-expanded", "true");
    expect(router.replace).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "画像4002のカテゴリを確認" }));
    expect(screen.queryByRole("region", { name: "画像4001のカテゴリ確認" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "画像4002のカテゴリ確認" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "画像4002のカテゴリを確認" }));
    expect(screen.queryByRole("region", { name: "画像4002のカテゴリ確認" })).not.toBeInTheDocument();
  });
  it("完了の更新成功後にカテゴリ欄を閉じる", async () => {
    const user = await openCategories();
    const row = screen.getByRole("button", { name: "画像4001のカテゴリを確認" }).closest("tr")!;
    await user.click(within(row).getByRole("button", { name: "完了" }));
    await waitFor(() => expect(screen.queryByRole("region", { name: "画像4001のカテゴリ確認" })).not.toBeInTheDocument());
    expect(updateTaskState).toHaveBeenCalledWith(4001, 2);
  });
  it("完了の更新失敗時には閉じない", async () => {
    vi.mocked(updateTaskState).mockRejectedValueOnce(new Error("failed"));
    const user = await openCategories();
    const row = screen.getByRole("button", { name: "画像4001のカテゴリを確認" }).closest("tr")!;
    await user.click(within(row).getByRole("button", { name: "完了" }));
    await screen.findByRole("alert");
    expect(screen.getByRole("region", { name: "画像4001のカテゴリ確認" })).toBeInTheDocument();
  });
  it("コメント送信成功後にカテゴリ欄とコメント欄を閉じる", async () => {
    const user = await openCategories();
    const row = screen.getByRole("button", { name: "画像4001のカテゴリを確認" }).closest("tr")!;
    await user.click(within(row).getByRole("button", { name: "コメント一覧" }));
    await user.type(await screen.findByLabelText("新しいコメント"), "確認しました");
    await user.click(screen.getByRole("button", { name: "投稿する" }));
    await user.click(screen.getByRole("button", { name: "この内容で投稿する" }));
    await waitFor(() => expect(screen.queryByRole("region", { name: "画像4001のカテゴリ確認" })).not.toBeInTheDocument());
    expect(screen.queryByLabelText("新しいコメント")).not.toBeInTheDocument();
  });
  it("コメント送信失敗時にはカテゴリ欄を閉じない", async () => {
    vi.mocked(createTaskComment).mockRejectedValueOnce(new Error("failed"));
    const user = await openCategories();
    const row = screen.getByRole("button", { name: "画像4001のカテゴリを確認" }).closest("tr")!;
    await user.click(within(row).getByRole("button", { name: "コメント一覧" }));
    await user.type(await screen.findByLabelText("新しいコメント"), "確認しました");
    await user.click(screen.getByRole("button", { name: "投稿する" }));
    await user.click(screen.getByRole("button", { name: "この内容で投稿する" }));
    await screen.findByRole("alert");
    expect(screen.getByRole("region", { name: "画像4001のカテゴリ確認" })).toBeInTheDocument();
  });
});
