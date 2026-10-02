export type Task = {
  id: number;
  title: string;
};

export async function getTasks(): Promise<Task[]> {
  const response = await fetch("/api/tasks");

  if (!response.ok) {
    throw new Error("タスクの取得に失敗しました");
  }

  return response.json();
}