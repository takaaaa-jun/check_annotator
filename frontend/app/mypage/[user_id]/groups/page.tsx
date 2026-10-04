import { notFound } from "next/navigation";

import { GroupsPageClient } from "./groups-page-client";

export default async function GroupsPage({
  params,
}: PageProps<"/mypage/[user_id]/groups">) {
  const { user_id: userIdText } = await params;
  const userId = Number(userIdText);

  if (
    !Number.isSafeInteger(userId) ||
    userId <= 0 ||
    String(userId) !== userIdText
  ) {
    notFound();
  }

  return <GroupsPageClient userId={userId} />;
}