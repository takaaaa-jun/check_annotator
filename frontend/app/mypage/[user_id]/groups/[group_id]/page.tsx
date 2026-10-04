import { notFound } from "next/navigation";

import { GroupTasksPageClient } from "./group-tasks-page-client";

type GroupTasksPageProps = {
  params: Promise<{
    user_id: string;
    group_id: string;
  }>;
};

function parsePositiveInteger(
  value: string,
): number | null {
  const parsedValue = Number(value);

  if (
    !Number.isSafeInteger(parsedValue) ||
    parsedValue <= 0 ||
    String(parsedValue) !== value
  ) {
    return null;
  }

  return parsedValue;
}

export default async function GroupTasksPage({
  params,
}: GroupTasksPageProps) {
  const {
    user_id: userIdText,
    group_id: groupIdText,
  } = await params;

  const userId =
    parsePositiveInteger(userIdText);

  const groupId =
    parsePositiveInteger(groupIdText);

  if (userId === null || groupId === null) {
    notFound();
  }

  return (
    <GroupTasksPageClient
      userId={userId}
      groupId={groupId}
    />
  );
}