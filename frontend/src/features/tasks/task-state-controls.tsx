import type { StateCount } from "../../lib/api/types";

function getStateColorClasses(
  stateName: string,
  selected: boolean,
): string {
  if (selected) {
    switch (stateName) {
      case "未着手":
        return "border-red-700 bg-red-600 text-white";
      case "完了":
        return "border-emerald-700 bg-emerald-600 text-white";
      case "付与予定ラベル":
        return "border-indigo-700 bg-indigo-600 text-white";
      default:
        return "border-amber-600 bg-amber-400 text-slate-950";
    }
  }

  switch (stateName) {
    case "未着手":
      return "border-red-300 bg-red-50 text-red-800 hover:bg-red-100";
    case "完了":
      return "border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100";
    case "付与予定ラベル":
      return "border-indigo-300 bg-indigo-50 text-indigo-800 hover:bg-indigo-100";
    default:
      return "border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100";
  }
}

export function TaskStateBadge({
  stateName,
}: {
  stateName: string;
}) {
  return (
    <span
      className={`inline-flex whitespace-nowrap rounded-full border px-3 py-1.5 text-base font-extrabold ${getStateColorClasses(
        stateName,
        false,
      )}`}
    >
      {stateName}
    </span>
  );
}

type TaskStateControlsProps = {
  states: StateCount[];
  currentStateId: number;
  disabled: boolean;
  onSelect: (state: StateCount) => void;
};

export function TaskStateControls({
  states,
  currentStateId,
  disabled,
  onSelect,
}: TaskStateControlsProps) {
  return (
    <>
      {states.map((state) => {
        const selected =
          currentStateId === state.state_id;

        return (
          <button
            key={state.state_id}
            type="button"
            aria-pressed={selected}
            disabled={disabled}
            onClick={() => {
              onSelect(state);
            }}
            className={`min-h-11 whitespace-nowrap rounded-lg border px-2 text-base font-extrabold shadow-sm disabled:cursor-wait disabled:opacity-50 xl:px-3 ${getStateColorClasses(
              state.state_name,
              selected,
            )} ${
              selected
                ? "scale-[1.03] ring-2 ring-slate-800 ring-offset-2"
                : ""
            }`}
          >
            {state.state_name}
          </button>
        );
      })}
    </>
  );
}
