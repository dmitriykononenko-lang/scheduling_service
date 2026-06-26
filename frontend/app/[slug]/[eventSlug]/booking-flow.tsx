"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  createBooking,
  getSlots,
  type BookingCreateResponse,
  type EventTypeDetail,
  type HostPublic,
  type QuestionPublic,
  type SlotRead,
} from "@/lib/api";

const HORIZON_DAYS = 30;

// --- Форматирование в поясе гостя (от UTC-инстанта, без зависимости от start_local) ---

function dayKey(iso: string, tz: string): string {
  // Стабильный ключ дня (YYYY-MM-DD) в поясе гостя.
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(iso));
}

function fmtDayLabel(iso: string, tz: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    timeZone: tz,
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date(iso));
}

function fmtTime(iso: string, tz: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

function priceLabel(et: EventTypeDetail): string {
  if (!et.price || Number(et.price) === 0) return "Бесплатно";
  const amount = new Intl.NumberFormat("ru-RU").format(Number(et.price));
  const suffix = et.requires_prepay ? " · предоплата" : "";
  return `${amount} ${et.currency}${suffix}`;
}

type SlotsState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; slots: SlotRead[] };

type AnswerValue = string | string[];

export function BookingFlow({
  slug,
  eventSlug,
  host,
  eventType,
}: {
  slug: string;
  eventSlug: string;
  host: HostPublic;
  eventType: EventTypeDetail;
}) {
  // Стартуем с пояса хоста (детерминированно для SSR), затем уточняем пояс браузера.
  const [tz, setTz] = useState(host.timezone);
  const [slotsState, setSlotsState] = useState<SlotsState>({ status: "loading" });
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<SlotRead | null>(null);

  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [email, setEmail] = useState("");
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<BookingCreateResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    // Пояс гостя доступен только на клиенте — определяем его и сразу грузим слоты в нём.
    // Слоты ключуются по start_utc (не зависит от пояса), поэтому пересчёта/сброса выбора не нужно.
    let effectiveTz = host.timezone;
    try {
      const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (browserTz) effectiveTz = browserTz;
    } catch {
      // оставляем пояс хоста
    }
    const now = new Date();
    const from = dayKey(now.toISOString(), effectiveTz);
    const to = dayKey(
      new Date(now.getTime() + HORIZON_DAYS * 86_400_000).toISOString(),
      effectiveTz,
    );
    getSlots(slug, eventSlug, from, to, effectiveTz).then((resp) => {
      if (cancelled) return;
      setTz(effectiveTz);
      setSlotsState(
        resp ? { status: "ready", slots: resp.slots } : { status: "error" },
      );
    });
    return () => {
      cancelled = true;
    };
  }, [slug, eventSlug, host.timezone]);

  // Группируем слоты по локальному дню гостя.
  const days = useMemo(() => {
    if (slotsState.status !== "ready") return [];
    const byDay = new Map<string, SlotRead[]>();
    for (const s of slotsState.slots) {
      const key = dayKey(s.start_utc, tz);
      const list = byDay.get(key);
      if (list) list.push(s);
      else byDay.set(key, [s]);
    }
    return [...byDay.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, slots]) => ({ key, slots }));
  }, [slotsState, tz]);

  const activeDay =
    selectedDay && days.some((d) => d.key === selectedDay)
      ? selectedDay
      : (days[0]?.key ?? null);
  const activeDaySlots =
    days.find((d) => d.key === activeDay)?.slots ?? [];

  function setAnswer(id: string, value: AnswerValue) {
    setAnswers((prev) => ({ ...prev, [id]: value }));
  }

  function validate(): string | null {
    if (!name.trim()) return "Укажите имя";
    if (!contact.trim()) return "Укажите контакт для связи";
    for (const q of eventType.questions) {
      if (!q.required) continue;
      const v = answers[q.id];
      const empty =
        v == null ||
        (typeof v === "string" && !v.trim()) ||
        (Array.isArray(v) && v.length === 0);
      if (empty) return `Ответьте на обязательный вопрос: «${q.label}»`;
    }
    return null;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedSlot) return;
    const err = validate();
    if (err) {
      setSubmitError(err);
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    const res = await createBooking(slug, eventSlug, {
      start_utc: selectedSlot.start_utc,
      invitee_name: name.trim(),
      invitee_contact: contact.trim(),
      invitee_email: email.trim() || undefined,
      invitee_timezone: tz,
      answers,
    });
    setSubmitting(false);
    if (res.ok) setResult(res.data);
    else setSubmitError(res.error);
  }

  // --- Экран подтверждения ---
  if (result) {
    const pending = result.booking.status === "pending_payment";
    return (
      <main className="mx-auto max-w-2xl px-6 py-16">
        <div className="rounded-xl border border-slate-200 p-8 text-center shadow-sm">
          <div
            className={`mx-auto flex h-12 w-12 items-center justify-center rounded-full text-2xl ${
              pending ? "bg-amber-50 text-amber-600" : "bg-green-50 text-green-600"
            }`}
          >
            {pending ? "⏳" : "✓"}
          </div>
          <h1 className="mt-4 text-2xl font-bold">
            {pending ? "Бронь создана, ожидает оплаты" : "Бронь подтверждена!"}
          </h1>
          <p className="mt-2 text-slate-600">
            {eventType.title} ·{" "}
            {fmtDayLabel(result.booking.start_utc, tz)},{" "}
            {fmtTime(result.booking.start_utc, tz)} ({tz})
          </p>
          {pending && (
            <p className="mt-3 text-sm text-amber-700">
              Для этой встречи нужна предоплата. Приём оплаты (ЮKassa / Т-Банк)
              подключается в следующем срезе — пока бронь висит в статусе ожидания.
            </p>
          )}
          <div className="mt-6 rounded-lg bg-slate-50 p-4 text-left text-sm">
            <p className="font-medium text-slate-700">
              Ссылка для управления бронью
            </p>
            <p className="mt-1 break-all text-slate-500">{result.manage_url}</p>
            <p className="mt-2 text-xs text-slate-400">
              Сохраните её, чтобы перенести или отменить встречу. Страница
              управления появится в ближайшем обновлении.
            </p>
          </div>
          <Link
            href={`/${slug}`}
            className="mt-6 inline-block text-brand hover:underline"
          >
            ← К другим встречам организатора
          </Link>
        </div>
      </main>
    );
  }

  // --- Основной поток: выбор слота + форма ---
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <Link
        href={`/${slug}`}
        className="text-sm text-slate-500 hover:text-brand"
      >
        ← {host.name}
      </Link>

      <header className="mt-4 border-b border-slate-200 pb-6">
        <h1 className="text-3xl font-bold">{eventType.title}</h1>
        {eventType.description && (
          <p className="mt-2 text-slate-600">{eventType.description}</p>
        )}
        <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
          <span>{eventType.duration_minutes} мин</span>
          <span className="font-medium text-brand">{priceLabel(eventType)}</span>
          <span>Пояс: {tz}</span>
        </p>
      </header>

      {/* Шаг 1 — выбор слота */}
      <section className="mt-8">
        <h2 className="text-lg font-semibold">1. Выберите время</h2>

        {slotsState.status === "loading" && (
          <p className="mt-4 text-slate-500">Загружаем свободные слоты…</p>
        )}

        {slotsState.status === "error" && (
          <p className="mt-4 text-red-600">
            Не удалось загрузить слоты. Обновите страницу или попробуйте позже.
          </p>
        )}

        {slotsState.status === "ready" && days.length === 0 && (
          <p className="mt-4 text-slate-600">
            На ближайшие {HORIZON_DAYS} дней свободных слотов нет.
          </p>
        )}

        {slotsState.status === "ready" && days.length > 0 && (
          <div className="mt-4">
            <div className="flex flex-wrap gap-2">
              {days.map((d) => (
                <button
                  key={d.key}
                  type="button"
                  onClick={() => {
                    setSelectedDay(d.key);
                    setSelectedSlot(null);
                  }}
                  className={`rounded-lg border px-3 py-2 text-sm transition ${
                    d.key === activeDay
                      ? "border-brand bg-brand text-white"
                      : "border-slate-200 hover:border-brand"
                  }`}
                >
                  {fmtDayLabel(d.slots[0].start_utc, tz)}
                </button>
              ))}
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-4">
              {activeDaySlots.map((s) => (
                <button
                  key={s.start_utc}
                  type="button"
                  onClick={() => setSelectedSlot(s)}
                  className={`rounded-lg border px-3 py-2 text-sm transition ${
                    selectedSlot?.start_utc === s.start_utc
                      ? "border-brand bg-brand text-white"
                      : "border-slate-200 hover:border-brand"
                  }`}
                >
                  {fmtTime(s.start_utc, tz)}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Шаг 2 — данные гостя */}
      {selectedSlot && (
        <form onSubmit={onSubmit} className="mt-10">
          <h2 className="text-lg font-semibold">2. Ваши данные</h2>
          <p className="mt-1 text-sm text-slate-500">
            Выбрано: {fmtDayLabel(selectedSlot.start_utc, tz)},{" "}
            {fmtTime(selectedSlot.start_utc, tz)}
          </p>

          <div className="mt-4 space-y-4">
            <Field label="Имя" required>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={inputClass}
                placeholder="Как к вам обращаться"
              />
            </Field>

            <Field label="Телефон или Telegram" required>
              <input
                type="text"
                value={contact}
                onChange={(e) => setContact(e.target.value)}
                className={inputClass}
                placeholder="+7… или @username"
              />
            </Field>

            <Field label="Email (для подтверждения)">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputClass}
                placeholder="you@example.com"
              />
            </Field>

            {eventType.questions.map((q) => (
              <Field key={q.id} label={q.label} required={q.required}>
                <QuestionField
                  question={q}
                  value={answers[q.id]}
                  onChange={(v) => setAnswer(q.id, v)}
                />
              </Field>
            ))}
          </div>

          {submitError && (
            <p className="mt-4 text-sm text-red-600">{submitError}</p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="mt-6 rounded-lg bg-brand px-5 py-3 font-medium text-white transition hover:bg-brand-dark disabled:opacity-60"
          >
            {submitting ? "Бронируем…" : "Забронировать"}
          </button>
        </form>
      )}
    </main>
  );
}

const inputClass =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand";

function Field({
  label,
  required = false,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-slate-700">
        {label}
        {required && <span className="text-red-500"> *</span>}
      </span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

function QuestionField({
  question,
  value,
  onChange,
}: {
  question: QuestionPublic;
  value: AnswerValue | undefined;
  onChange: (value: AnswerValue) => void;
}) {
  if (question.field_type === "textarea") {
    return (
      <textarea
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        className={inputClass}
      />
    );
  }

  if (question.field_type === "select") {
    return (
      <select
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
      >
        <option value="">— выберите —</option>
        {(question.options ?? []).map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );
  }

  if (question.field_type === "checkbox") {
    const selected = Array.isArray(value) ? value : [];
    return (
      <div className="space-y-1">
        {(question.options ?? []).map((opt) => {
          const checked = selected.includes(opt);
          return (
            <label key={opt} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={checked}
                onChange={(e) =>
                  onChange(
                    e.target.checked
                      ? [...selected, opt]
                      : selected.filter((o) => o !== opt),
                  )
                }
              />
              {opt}
            </label>
          );
        })}
      </div>
    );
  }

  // text (по умолчанию)
  return (
    <input
      type="text"
      value={(value as string) ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className={inputClass}
    />
  );
}
