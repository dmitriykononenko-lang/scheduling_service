import Link from "next/link";

import {
  getPublicEventTypes,
  getPublicProfile,
  type EventTypePublic,
} from "@/lib/api";

// Страница записи всегда рендерится на запрос (данные зависят от состояния БД).
export const dynamic = "force-dynamic";

function formatPrice(et: EventTypePublic): string {
  if (!et.price || Number(et.price) === 0) return "Бесплатно";
  const amount = new Intl.NumberFormat("ru-RU").format(Number(et.price));
  const suffix = et.requires_prepay ? " · предоплата" : "";
  return `${amount} ${et.currency}${suffix}`;
}

export default async function PublicBookingPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const profile = await getPublicProfile(slug);

  if (!profile) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-24 text-center">
        <h1 className="text-2xl font-semibold">Организатор не найден</h1>
        <p className="mt-3 text-slate-600">
          Проверьте ссылку или убедитесь, что бэкенд запущен и страница{" "}
          <code className="rounded bg-slate-100 px-1">/{slug}</code> существует.
        </p>
        <Link href="/" className="mt-6 inline-block text-brand hover:underline">
          ← На главную
        </Link>
      </main>
    );
  }

  const eventTypes = (await getPublicEventTypes(slug)) ?? [];

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <header className="border-b border-slate-200 pb-6">
        <h1 className="text-3xl font-bold">{profile.name}</h1>
        <p className="mt-1 text-sm text-slate-500">
          Часовой пояс: {profile.timezone}
        </p>
      </header>

      <h2 className="mt-8 text-lg font-semibold">Выберите тип встречи</h2>

      {eventTypes.length === 0 ? (
        <p className="mt-4 text-slate-600">
          У организатора пока нет доступных типов встреч.
        </p>
      ) : (
        <ul className="mt-4 space-y-3">
          {eventTypes.map((et) => (
            <li key={et.id}>
              <Link
                href={`/${slug}/${et.slug}`}
                className="block rounded-xl border border-slate-200 p-5 transition hover:border-brand hover:shadow-sm"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-medium">{et.title}</p>
                    {et.description && (
                      <p className="mt-1 text-sm text-slate-600">
                        {et.description}
                      </p>
                    )}
                  </div>
                  <span className="whitespace-nowrap text-sm text-slate-500">
                    {et.duration_minutes} мин
                  </span>
                </div>
                <p className="mt-3 text-sm font-medium text-brand">
                  {formatPrice(et)}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
