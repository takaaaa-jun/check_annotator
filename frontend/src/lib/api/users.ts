import { apiRequest } from "./client";
import type { UserGroupsResponse } from "./types";

export function getUserGroups(
  userId: number,
): Promise<UserGroupsResponse> {
  return apiRequest<UserGroupsResponse>(
    `/api/users/${userId}/groups`,
  );
}