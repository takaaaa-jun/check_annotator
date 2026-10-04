import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto grid min-h-[calc(100vh-65px)] max-w-3xl place-items-center px-4 py-12 text-center sm:px-6">
      <div>
        <p className="text-sm font-bold uppercase tracking-widest text-blue-700">
          404
        </p>
        <h1 className="mt-2 text-3xl font-bold text-slate-950">
          ページが見つかりません
        </h1>
        <p className="mt-4 text-slate-600">
          URLが正しいか確認するか、ログイン画面から操作をやり直してください。
        </p>
        <Link
          href="/login"
          className="mt-6 inline-flex min-h-11 items-center rounded-xl bg-blue-600 px-5 font-semibold text-white hover:bg-blue-700"
        >
          ログイン画面へ
        </Link>
      </div>
    </main>
  );
}
