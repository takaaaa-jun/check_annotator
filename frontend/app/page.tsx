"use client";

import { useEffect, useState } from "react";

import { getTasks, type Task } from "@/src/lib/api/tasks";

export default function Home() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTasks()
      .then(setTasks)
      .catch((err: unknown) => {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("予期しないエラーが発生しました");
        }
      });
  }, []);

  if (error !== null) {
    return <main>{error}</main>;
  }

  return (
    <main>
      <h1>タスク一覧</h1>

      <ul>
        {tasks.map((task) => (
          <li key={task.id}>{task.title}</li>
        ))}
      </ul>
    </main>
  );
}