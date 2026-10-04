import { LoadingState } from "@/src/components/async-state";

export default function Loading() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <LoadingState />
    </main>
  );
}
