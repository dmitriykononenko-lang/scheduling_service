import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Созвон — запись на созвоны и встречи",
  description:
    "Созвон — SaaS планирования встреч для фрилансеров и консультантов: запись на созвоны с предоплатой, часовыми поясами и API.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
