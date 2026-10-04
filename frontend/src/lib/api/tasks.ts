import { apiRequest } from "./client";
import type {
  CreatedComment,
  TaskCommentsResponse,
  TaskStateResponse,
} from "./types";

export type TaskCommentsPageSize =
  | 10
  | 50
  | 100;

export type GetTaskCommentsOptions = {
  page?: number;
  pageSize?: TaskCommentsPageSize;
};

export type CreateTaskCommentInput = {
  content: string;
  parentId: number | null;
};

export function getTaskComments(
  taskId: number,
  options: GetTaskCommentsOptions = {},
): Promise<TaskCommentsResponse> {
  const {
    page = 1,
    pageSize = 50,
  } = options;

  const searchParams = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  return apiRequest<TaskCommentsResponse>(
    `/api/tasks/${taskId}/comments?${searchParams.toString()}`,
  );
}

export function createTaskComment(
  taskId: number,
  input: CreateTaskCommentInput,
): Promise<CreatedComment> {
  return apiRequest<CreatedComment>(
    `/api/tasks/${taskId}/comments`,
    {
      method: "POST",
      body: JSON.stringify({
        content: input.content,
        parent_id: input.parentId,
      }),
    },
  );
}

export function updateTaskState(
  taskId: number,
  stateId: number,
): Promise<TaskStateResponse> {
  return apiRequest<TaskStateResponse>(
    `/api/tasks/${taskId}/state`,
    {
      method: "PATCH",
      body: JSON.stringify({
        state_id: stateId,
      }),
    },
  );
}
