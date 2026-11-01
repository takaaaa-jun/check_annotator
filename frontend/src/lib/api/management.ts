import { apiRequest } from "./client";
import type { Comment, Pagination, StateCount } from "./types";

export type WorkerProgress = {
  user_id: number; user_name: string; group_count: number; total_count: number;
  completed_count: number; pending_comments: number; state_counts: StateCount[];
};
export type AdminOverview = { workers: WorkerProgress[]; total_tasks: number; completed_tasks: number; pending_comments: number };
export type CommentActivity = Comment & {
  task_id: number; image_id: number; group_id: number; group_name: string;
  worker_id: number; worker_name: string; author_role: string;
  parent_content: string | null; has_admin_reply: boolean;
};
export type CommentActivityPage = { comments: CommentActivity[]; pagination: Pagination };
export function getAdminOverview() { return apiRequest<AdminOverview>("/api/admin/overview"); }
export function getCommentActivity(kind: "admin" | "replies", page: number, workerId: string, unanswered: boolean) {
  const query = new URLSearchParams({ page: String(page), page_size: "20" });
  if (kind === "admin") {
    if (workerId) query.set("worker_id", workerId);
    query.set("unanswered", String(unanswered));
  }
  return apiRequest<CommentActivityPage>(kind === "admin" ? `/api/admin/comments?${query}` : `/api/users/me/replies?${query}`);
}
