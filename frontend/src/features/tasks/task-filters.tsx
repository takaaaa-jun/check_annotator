import type { GroupProgress } from "../../lib/api/types";
import type { GroupTasksPageSize } from "../../lib/api/users";

type TaskFiltersProps = {
  group: GroupProgress;
  stateId: number | undefined;
  pageSize: GroupTasksPageSize;
  disabled: boolean;
  onStateChange: (stateId: number | undefined) => void;
  onPageSizeChange: (pageSize: GroupTasksPageSize) => void;
};

export function TaskFilters({
  group,
  stateId,
  pageSize,
  disabled,
  onStateChange,
  onPageSizeChange,
}: TaskFiltersProps) {
  return (
    <section
      aria-labelledby="task-filter-heading"
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_8px_30px_rgba(15,23,42,0.04)]"
    >
      <h2
        id="task-filter-heading"
        className="mb-5 text-xl font-extrabold text-slate-950"
      >
        表示条件
      </h2>

      <div className="grid gap-5">
        <div className="grid gap-2">
          <label
            htmlFor="state-filter"
            className="block text-base font-bold text-slate-800"
          >
            状態
          </label>
          <select
            id="state-filter"
            value={stateId ?? ""}
            disabled={disabled}
            onChange={(event) => {
              onStateChange(
                event.target.value === ""
                  ? undefined
                  : Number(event.target.value),
              );
            }}
            className="min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base font-semibold text-slate-900 shadow-sm hover:border-slate-400 disabled:cursor-wait disabled:bg-slate-50"
          >
            <option value="">すべて</option>
            {group.state_counts.map((state) => (
              <option
                key={state.state_id}
                value={state.state_id}
              >
                {state.state_name}（{state.count}件）
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-2">
          <label
            htmlFor="page-size"
            className="block text-base font-bold text-slate-800"
          >
            1ページの表示件数
          </label>
          <select
            id="page-size"
            value={pageSize}
            disabled={disabled}
            onChange={(event) => {
              onPageSizeChange(
                Number(event.target.value) as GroupTasksPageSize,
              );
            }}
            className="min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-base font-semibold text-slate-900 shadow-sm hover:border-slate-400 disabled:cursor-wait disabled:bg-slate-50"
          >
            <option value={10}>10件</option>
            <option value={50}>50件</option>
            <option value={100}>100件</option>
          </select>
        </div>
      </div>
    </section>
  );
}
