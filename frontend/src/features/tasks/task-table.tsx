import {
  Fragment,
  type RefObject,
} from "react";

import {
  EmptyState,
  LoadingState,
} from "../../components/async-state";
import type {
  GroupTasksResponse,
  StateCount,
  Task,
} from "../../lib/api/types";
import { formatDateTime } from "../../lib/format/date-time";
import { TaskCommentsPanel } from "./task-comments-panel";
import {
  TaskStateBadge,
  TaskStateControls,
} from "./task-state-controls";

export type CommentComposer = {
  taskId: number;
  initialContent: string;
  focusKey: number;
};

type TaskTableProps = {
  taskData: GroupTasksResponse | null;
  stateCounts: StateCount[];
  loading: boolean;
  activeTaskId: number | null;
  openCommentsTaskId: number | null;
  commentComposer: CommentComposer | null;
  updatingTaskIds: Set<number>;
  taskUpdateErrors: Record<number, string>;
  scrollRef: RefObject<HTMLDivElement | null>;
  onTaskRowRef: (
    taskId: number,
    element: HTMLTableRowElement | null,
  ) => void;
  onStateSelect: (
    task: Task,
    state: StateCount,
  ) => void;
  onToggleComments: (taskId: number) => void;
  onUnauthorized: () => void;
  onCommentCompleted: (taskId: number) => void;
};

export function TaskTable({
  taskData,
  stateCounts,
  loading,
  activeTaskId,
  openCommentsTaskId,
  commentComposer,
  updatingTaskIds,
  taskUpdateErrors,
  scrollRef,
  onTaskRowRef,
  onStateSelect,
  onToggleComments,
  onUnauthorized,
  onCommentCompleted,
}: TaskTableProps) {
  return (
    <section
      aria-labelledby="task-list-heading"
      className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_8px_30px_rgba(15,23,42,0.05)]"
    >
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 px-5 py-4 sm:px-6">
        <h2
          id="task-list-heading"
          className="text-xl font-extrabold text-slate-950"
        >
          タスク一覧
        </h2>
        <p className="rounded-full bg-slate-200 px-3 py-1.5 text-base font-bold text-slate-800">
          全{taskData?.pagination.total ?? 0}件
        </p>
      </div>

      {loading ? (
        <LoadingState message="タスクを読み込み中..." />
      ) : taskData === null || taskData.tasks.length === 0 ? (
        <div className="p-5">
          <EmptyState message="該当するタスクはありません" />
        </div>
      ) : (
        <div
          ref={scrollRef}
          className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden"
        >
          <table className="w-full table-fixed border-collapse">
            <colgroup>
              <col className="w-[12%]" />
              <col className="w-[18%]" />
              <col className="w-[22%]" />
              <col className="w-[48%]" />
            </colgroup>
            <thead className="sticky top-0 z-10 bg-slate-50 shadow-sm">
              <tr>
                {[
                  "画像ID",
                  "状態",
                  "最終更新日時",
                  "操作",
                ].map((heading) => (
                  <th
                    key={heading}
                    scope="col"
                    className="whitespace-nowrap border-b border-slate-300 px-2 py-3.5 text-center text-sm font-extrabold tracking-wide text-slate-700 xl:px-4"
                  >
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {taskData.tasks.map((task) => (
                <Fragment key={task.task_id}>
                  <tr
                    ref={(element) => {
                      onTaskRowRef(task.task_id, element);
                    }}
                    className={
                      activeTaskId === task.task_id
                        ? "bg-blue-100/80 ring-2 ring-inset ring-blue-400"
                        : "hover:bg-blue-50/50"
                    }
                  >
                    <td className="break-words border-b border-slate-100 px-2 py-4 text-center text-lg font-extrabold text-slate-950 xl:px-4">
                      {task.image_id}
                    </td>
                    <td className="border-b border-slate-100 px-2 py-4 text-center xl:px-4">
                      <TaskStateBadge stateName={task.state_name} />
                    </td>
                    <td className="border-b border-slate-100 px-2 py-4 text-center text-base font-semibold text-slate-700 xl:px-4">
                      {formatDateTime(task.updated_at)}
                    </td>
                    <td className="border-b border-slate-100 px-2 py-4 text-center xl:px-4">
                      <div className="flex w-full flex-wrap items-center justify-center gap-2">
                        <TaskStateControls
                          states={stateCounts}
                          currentStateId={task.state_id}
                          disabled={updatingTaskIds.has(task.task_id)}
                          onSelect={(state) => {
                            onStateSelect(task, state);
                          }}
                        />
                        <button
                          type="button"
                          aria-expanded={openCommentsTaskId === task.task_id}
                          aria-controls={`task-comments-${task.task_id}`}
                          onClick={() => {
                            onToggleComments(task.task_id);
                          }}
                          className="min-h-11 whitespace-nowrap rounded-lg border border-slate-400 bg-white px-2 text-base font-bold text-slate-800 hover:bg-slate-100 xl:px-3"
                        >
                          {openCommentsTaskId === task.task_id
                            ? "コメント一覧を閉じる"
                            : "コメント一覧"}
                        </button>
                      </div>
                      {taskUpdateErrors[task.task_id] !== undefined && (
                        <p
                          role="alert"
                          className="mx-auto mt-2 max-w-80 text-base font-semibold text-red-700"
                        >
                          {taskUpdateErrors[task.task_id]}
                        </p>
                      )}
                    </td>
                  </tr>

                  {openCommentsTaskId === task.task_id && (
                    <tr id={`task-comments-${task.task_id}`}>
                      <td colSpan={4} className="p-0">
                        <TaskCommentsPanel
                          key={`${task.task_id}-${
                            commentComposer?.taskId === task.task_id
                              ? commentComposer.focusKey
                              : 0
                          }`}
                          taskId={task.task_id}
                          imageId={task.image_id}
                          onUnauthorized={onUnauthorized}
                          initialContent={
                            commentComposer?.taskId === task.task_id
                              ? commentComposer.initialContent
                              : ""
                          }
                          focusKey={
                            commentComposer?.taskId === task.task_id
                              ? commentComposer.focusKey
                              : 0
                          }
                          onCompleted={() => {
                            onCommentCompleted(task.task_id);
                          }}
                        />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
