import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ReviewDrawer } from "@/components/review/ReviewDrawer";
import { ToastContainer } from "@/components/ui/Toast";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "L'Atelier Luna — XHS Brand Agent",
  description: "小红书自主品牌运营专家 — AI Agent 后端服务",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="h-full flex">
        <Providers>
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <Header title="内容看板" agentStatus="idle" />
            <main className="flex-1 overflow-hidden p-4">{children}</main>
          </div>
          <ReviewDrawer />
          <ToastContainer />
        </Providers>
      </body>
    </html>
  );
}
