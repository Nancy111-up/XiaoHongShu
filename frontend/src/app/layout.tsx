import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "体育品牌运营 Agent",
  description: "体育品牌运营工作区",
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  )
}
