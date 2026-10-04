import { apiRequest } from "./client";
import type { TaskStateResponse } from "./types";

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
