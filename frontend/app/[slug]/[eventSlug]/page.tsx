import Link from "next/link";

import { getPublicEventType, getPublicProfile } from "@/lib/api";

import { BookingFlow } from "./booking-flow";

// Данные зависят от состояния БД — рендерим на каждый запрос.
export const dynamic = "force-dynamic";

export default async function EventBookingPage({
  params,
}: {
  params: Promise<{ slug: string; eventSlug: string }>;
}) {
  const { slug, eventSlug } = await params;
  const [profile, eventType] = await Promise.all([
    getPublicProfile(slug),
    getPublicEventType(slug, eventSlug),
  ]);

  if (!profile || !eventType) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-24 text-center">
        <h1 className="text-2xl font-semibold">Страница записи не найдена</h1>
        <p className="mt-3 text-slate-600">
          Проверьте ссылку или убедитесь, что бэкенд запущен и тип встречи{" "}
          <code className="rounded bg-slate-100 px-1">
            /{slug}/{eventSlug}
          </code>{" "}
          существует.
        </p>
        <Link
          href={`/${slug}`}
          className="mt-6 inline-block text-brand hover:underline"
        >
          ← К профилю организатора
        </Link>
      </main>
    );
  }

  return (
    <BookingFlow
      slug={slug}
      eventSlug={eventSlug}
      host={profile}
      eventType={eventType}
    />
  );
}
