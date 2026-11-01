// @vitest-environment jsdom
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ManagementPage } from "./management-page";
import { getCurrentUser } from "@/src/lib/api/auth";
import { getAdminOverview, getCommentActivity, type CommentActivity } from "@/src/lib/api/management";
import { createTaskComment, getTaskComments } from "@/src/lib/api/tasks";

const router = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/src/lib/api/auth", () => ({ getCurrentUser: vi.fn() }));
vi.mock("@/src/lib/api/management", () => ({ getAdminOverview: vi.fn(), getCommentActivity: vi.fn() }));
vi.mock("@/src/lib/api/tasks", () => ({ getTaskComments: vi.fn(), createTaskComment: vi.fn() }));
const pagination = { page: 1, page_size: 20, total: 1, total_pages: 1 };
const comment: CommentActivity = { comment_id: 21, task_id: 5, image_id: 105, group_id: 2, group_name: "00101-00200", worker_id: 6, worker_name: "sato", user_id: 6, user_name: "sato", author_role: "worker", parent_id: null, parent_content: null, content: "パンのカテゴリについて質問です", created_at: "2026-11-02T00:00:00Z", updated_at: "2026-11-02T00:00:00Z", has_admin_reply: false };
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getCurrentUser).mockResolvedValue({ user_id: 4, user_name: "admin-user", role_id: 2, role_name: "admin", login_at: null });
  vi.mocked(getAdminOverview).mockResolvedValue({ total_tasks: 100, completed_tasks: 40, pending_comments: 1, workers: [{ user_id: 6, user_name: "sato", group_count: 1, total_count: 100, completed_count: 40, pending_comments: 1, state_counts: [{ state_id: 2, state_name: "完了", count: 40 }] }] });
  vi.mocked(getCommentActivity).mockResolvedValue({ comments: [comment], pagination });
  vi.mocked(getTaskComments).mockResolvedValue({ task_id: 5, comments: [comment], pagination });
  vi.mocked(createTaskComment).mockResolvedValue({ ...comment, comment_id: 22, user_id: 4, user_name: "admin-user", parent_id: 21, content: "クロワッサンを選択してください" });
});
afterEach(() => cleanup());

describe("管理者と作業者のコメント確認", () => {
  it("管理者に作業者の進捗・未返信コメントを表示し、元コメントへ返信する", async () => {
    const user = userEvent.setup();
    render(<ManagementPage admin />);
    expect(await screen.findByRole("heading", { name: "作業進捗とコメント管理" })).toBeInTheDocument();
    await screen.findByText("パンのカテゴリについて質問です");
    expect(screen.getByRole("progressbar", { name: "satoの進捗率" })).toHaveAttribute("value", "40");
    await user.click(screen.getByRole("button", { name: "このコメントに返信" }));
    await screen.findByRole("button", { name: "返信する" });
    expect(screen.queryByRole("button", { name: "返信を取り消す" })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("コメント #21 へ返信"), "クロワッサンを選択してください");
    await user.click(screen.getByRole("button", { name: "返信する" }));
    const dialog = screen.getByRole("dialog", { name: "入力内容を確認してください" });
    expect(dialog).toHaveTextContent("コメント #21 への返信");
    await user.click(within(dialog).getByRole("button", { name: "この内容で投稿する" }));
    await waitFor(() => expect(createTaskComment).toHaveBeenCalledWith(5, { content: "クロワッサンを選択してください", parentId: 21 }));
    expect(await screen.findByText("画像105のコメント #21 に返信を送信しました。")).toBeInTheDocument();
  });
  it("一般作業者は管理者ページで拒否し、管理者APIを呼ばない", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({ user_id: 6, user_name: "sato", role_id: 1, role_name: "worker", login_at: null });
    render(<ManagementPage admin />);
    expect(await screen.findByRole("alert")).toHaveTextContent("管理者権限が必要");
    expect(getAdminOverview).not.toHaveBeenCalled();
    expect(getCommentActivity).not.toHaveBeenCalled();
  });
  it("作業者の返信一覧に管理者名・返信元・返信本文を表示する", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue({ user_id: 6, user_name: "sato", role_id: 1, role_name: "worker", login_at: null });
    vi.mocked(getCommentActivity).mockResolvedValue({ comments: [{ ...comment, comment_id: 22, parent_id: 21, user_id: 4, user_name: "admin-user", author_role: "admin", parent_content: comment.content, content: "クロワッサンを選択してください" }], pagination });
    render(<ManagementPage />);
    expect(await screen.findByText("クロワッサンを選択してください")).toBeInTheDocument();
    expect(screen.getByText("返信元 #21")).toBeInTheDocument();
    expect(screen.getByText("admin-user")).toBeInTheDocument();
    expect(getCommentActivity).toHaveBeenCalledWith("replies", 1, "", false);
    expect(getAdminOverview).not.toHaveBeenCalled();
  });
  it("返信失敗時は入力を保持し、送信済みと表示しない", async () => {
    vi.mocked(createTaskComment).mockRejectedValueOnce(new Error("failed"));
    const user = userEvent.setup();
    render(<ManagementPage admin />);
    await user.click(await screen.findByRole("button", { name: "このコメントに返信" }));
    await screen.findByRole("button", { name: "返信する" });
    await user.type(screen.getByLabelText("コメント #21 へ返信"), "入力を保持する");
    await user.click(screen.getByRole("button", { name: "返信する" }));
    await user.click(screen.getByRole("button", { name: "この内容で投稿する" }));
    await screen.findByRole("alert");
    expect(screen.getByLabelText("コメント #21 へ返信")).toHaveValue("入力を保持する");
    expect(screen.queryByText("画像105のコメント #21 に返信を送信しました。")).not.toBeInTheDocument();
  });
});
