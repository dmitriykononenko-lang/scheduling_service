"use client";

import Link from "next/link";
import { useState } from "react";

import { SlotPicker } from "@/components/slot-picker";
import {
  createBooking,
  type BookingCreateResponse,
  type EventTypeDetail,
  type HostPublic,
  type QuestionPublic,
  type SlotRead,
} from "@/lib/api";
import { fmtDayLabel, fmtTime } from "@/lib/datetime";

function priceLabel(et: EventTypeDetail): string {
  if (!et.price || Number(et.price) === 0) return "Бесплатно";
  const amount = new Intl.NumberFormat("ru-RU").format(Number(et.price));
  const suffix = et.requires_prepay ? " · предоплата" : "";
  return `${amount} ${et.currency}${suffix}`;
}

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
  // Пояс хоста — детерминированный старт для SSR; SlotPicker уточнит браузерный.
  const [tz, setTz] = useState(host.timezone);
  const [selectedSlot, setSelectedSlot] = useState<SlotRead | null>(null);

  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [email, setEmail] = useState("");
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<BookingCreateResponse | null>(null);

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
            <p className="font-medium text-slate-700">Управление бронью</p>
            <p className="mt-1 text-slate-500">
              Перенести или отменить встречу можно на{" "}
              <Link
                href={`/manage/${result.management_token}`}
                className="text-brand underline"
              >
                странице управления
              </Link>
              . Сохраните ссылку — она привязана к вашей брони.
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
        <SlotPicker
          slug={slug}
          eventSlug={eventSlug}
          fallbackTz={host.timezone}
          selectedStartUtc={selectedSlot?.start_utc ?? null}
          onSelect={setSelectedSlot}
          onTzResolved={setTz}
        />
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
