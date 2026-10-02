import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "アノテーション作業進捗管理",
  description: "アノテーション作業の進捗、状態、コメントを管理します。",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ja" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
