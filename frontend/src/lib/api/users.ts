import { apiRequest } from "./client";
import type {
  GroupTasksResponse,
  UserGroupsResponse,
} from "./types";

export type GroupTasksPageSize =
  | 10
  | 50
  | 100;

export type GetGroupTasksOptions = {
  stateId?: number;
  page?: number;
  pageSize?: GroupTasksPageSize;
};

export function getUserGroups(
  userId: number,
): Promise<UserGroupsResponse> {
  return apiRequest<UserGroupsResponse>(
    `/api/users/${userId}/groups`,
  );
}

export function getGroupTasks(
  userId: number,
  groupId: number,
  options: GetGroupTasksOptions = {},
): Promise<GroupTasksResponse> {
  const {
    stateId,
    page = 1,
    pageSize = 50,
  } = options;

  const searchParams =
    new URLSearchParams();

  if (stateId !== undefined) {
    searchParams.set(
      "state_id",
      String(stateId),
    );
  }

  searchParams.set(
    "page",
    String(page),
  );

  searchParams.set(
    "page_size",
    String(pageSize),
  );

  return apiRequest<GroupTasksResponse>(
    `/api/users/${userId}/groups/${groupId}/tasks?${searchParams.toString()}`,
  );
}