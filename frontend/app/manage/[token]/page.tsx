import Link from "next/link";

import { getManageBooking } from "@/lib/api";

import { ManageFlow } from "./manage-flow";

// Состояние брони зависит от БД — рендерим на каждый запрос.
export const dynamic = "force-dynamic";

export default async function ManageBookingPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  const booking = await getManageBooking(token);

  if (!booking) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-24 text-center">
        <h1 className="text-2xl font-semibold">Бронь не найдена</h1>
        <p className="mt-3 text-slate-600">
          Проверьте ссылку для управления — возможно, она устарела или бэкенд
          недоступен.
        </p>
        <Link href="/" className="mt-6 inline-block text-brand hover:underline">
          ← На главную
        </Link>
      </main>
    );
  }

  return <ManageFlow token={token} booking={booking} />;
}
