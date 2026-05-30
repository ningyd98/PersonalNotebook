import type { Metadata } from "next";
import "./globals.css";
import AppLayout from "@/components/layout/AppLayout";

export const metadata: Metadata = {
  title: "PersonalNotebook",
  description: "个人知识库系统 — 本地私有化 RAG 知识管理",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body>
        <AppLayout>{children}</AppLayout>
      </body>
    </html>
  );
}
