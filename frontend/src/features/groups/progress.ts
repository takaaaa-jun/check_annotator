import type { StateCount } from "../../lib/api/types";

export function getCompletedCount(
  stateCounts: StateCount[],
): number {
  const completedState = stateCounts.find(
    (state) => state.state_name === "完了",
  );

  return completedState?.count ?? 0;
}

export function calculateProgress(
  completedCount: number,
  totalCount: number,
): number {
  if (totalCount <= 0) {
    return 0;
  }

  const progress = Math.round(
    (completedCount / totalCount) * 100,
  );

  return Math.min(
    100,
    Math.max(0, progress),
  );
}