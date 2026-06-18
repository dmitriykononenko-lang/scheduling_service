import Link from "next/link";

const features = [
  {
    title: "Запись без переписки",
    text: "Гость выбирает свободный слот сам — с учётом вашего часового пояса и его собственного.",
  },
  {
    title: "Предоплата в рублях",
    text: "ЮKassa и Т-Банк: бронь подтверждается только после оплаты, чек по 54-ФЗ через эквайер.",
  },
  {
    title: "API и webhooks",
    text: "То, чего нет у конкурентов: события booking.created/payment.succeeded и REST-доступ к данным.",
  },
];

export default function HomePage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      <span className="inline-block rounded-full bg-blue-50 px-3 py-1 text-sm font-medium text-brand">
        MVP · черновик
      </span>
      <h1 className="mt-6 text-4xl font-bold tracking-tight sm:text-5xl">
        Calendly для русскоязычных консультантов
      </h1>
      <p className="mt-4 max-w-2xl text-lg text-slate-600">
        Запись на созвоны с предоплатой в рублях, корректными часовыми поясами и
        API, который встраивается в ваш рабочий стек.
      </p>

      <div className="mt-8 flex flex-wrap gap-4">
        <Link
          href="/demo"
          className="rounded-lg bg-brand px-5 py-3 font-medium text-white transition hover:bg-brand-dark"
        >
          Открыть демо-страницу записи
        </Link>
        <a
          href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/docs`}
          className="rounded-lg border border-slate-300 px-5 py-3 font-medium text-slate-700 transition hover:border-slate-400"
        >
          API-документация
        </a>
      </div>

      <section className="mt-16 grid gap-6 sm:grid-cols-3">
        {features.map((f) => (
          <div
            key={f.title}
            className="rounded-xl border border-slate-200 p-6 shadow-sm"
          >
            <h2 className="text-lg font-semibold">{f.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{f.text}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
