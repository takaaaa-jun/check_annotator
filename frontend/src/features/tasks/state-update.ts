import { ApiError } from "../../lib/api/client";
import type {
  GroupTasksResponse,
  TaskStateResponse,
} from "../../lib/api/types";

export function getTaskStateUpdateError(
  error: unknown,
): string {
  if (!(error instanceof ApiError)) {
    return "予期しないエラーが発生しました";
  }

  switch (error.status) {
    case 403:
      return "このタスクの状態を変更する権限がありません";
    case 404:
      return "対象のタスクまたは状態が見つかりません";
    case 422:
      return "選択した状態が正しくありません";
    case 500:
      return "サーバーでエラーが発生しました。時間をおいて再度お試しください";
    default:
      return error.message || "状態の更新に失敗しました";
  }
}

export function replaceUpdatedTask(
  taskData: GroupTasksResponse,
  updatedTask: TaskStateResponse,
): GroupTasksResponse {
  return {
    ...taskData,
    tasks: taskData.tasks.map((task) =>
      task.task_id === updatedTask.task_id
        ? {
            task_id: updatedTask.task_id,
            image_id: updatedTask.image_id,
            state_id: updatedTask.state_id,
            state_name: updatedTask.state_name,
            updated_at: updatedTask.updated_at,
          }
        : task,
    ),
  };
}
