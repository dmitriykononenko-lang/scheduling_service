"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { SlotPicker } from "@/components/slot-picker";
import {
  cancelBooking,
  rescheduleBooking,
  type BookingManageRead,
  type SlotRead,
} from "@/lib/api";
import { fmtDayLabel, fmtTime } from "@/lib/datetime";

const STATUS_BADGES: Record<string, { label: string; cls: string }> = {
  confirmed: { label: "Подтверждена", cls: "bg-green-50 text-green-700" },
  pending_payment: { label: "Ожидает оплаты", cls: "bg-amber-50 text-amber-700" },
  canceled: { label: "Отменена", cls: "bg-red-50 text-red-700" },
  rescheduled: { label: "Перенесена", cls: "bg-slate-100 text-slate-600" },
  completed: { label: "Завершена", cls: "bg-slate-100 text-slate-600" },
  no_show: { label: "Не состоялась", cls: "bg-slate-100 text-slate-600" },
};

// Изменять (отменять/переносить) можно только активные брони (ТЗ §4.5).
const MODIFIABLE = new Set(["confirmed", "pending_payment"]);

const inputClass =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand";
const primaryBtn =
  "rounded-lg bg-brand px-5 py-3 font-medium text-white transition hover:bg-brand-dark disabled:opacity-60";
const secondaryBtn =
  "rounded-lg border border-slate-300 px-5 py-3 font-medium text-slate-700 transition hover:border-brand disabled:opacity-60";

type Mode = "view" | "cancel" | "reschedule";

export function ManageFlow({
  token,
  booking,
}: {
  token: string;
  booking: BookingManageRead;
}) {
  const router = useRouter();
  // Детерминированный пояс (без обращения к браузеру при рендере) — пояс гостя при записи,
  // иначе пояс организатора. Так избегаем рассинхрона гидрации.
  const tz = booking.invitee_timezone || booking.host_timezone;

  const [status, setStatus] = useState(booking.status);
  const [mode, setMode] = useState<Mode>("view");
  const [reason, setReason] = useState("");
  const [newSlot, setNewSlot] = useState<SlotRead | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const modifiable = MODIFIABLE.has(status);
  const badge = STATUS_BADGES[status] ?? {
    label: status,
    cls: "bg-slate-100 text-slate-600",
  };

  function open(next: Mode) {
    setError(null);
    setMode(next);
  }

  async function onCancel() {
    setBusy(true);
    setError(null);
    const res = await cancelBooking(token, reason.trim() || undefined);
    setBusy(false);
    if (res.ok) {
      setStatus(res.data.status);
      setMode("view");
    } else {
      setError(res.error);
    }
  }

  async function onReschedule() {
    if (!newSlot) return;
    setBusy(true);
    setError(null);
    const res = await rescheduleBooking(token, newSlot.start_utc);
    setBusy(false);
    if (res.ok) {
      // Перенос создаёт НОВУЮ бронь с новым токеном — переходим на её страницу.
      router.push(`/manage/${res.data.management_token}`);
    } else {
      setError(res.error);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <Link
        href={`/${booking.host_slug}`}
        className="text-sm text-slate-500 hover:text-brand"
      >
        ← {booking.host_name}
      </Link>

      <header className="mt-4 border-b border-slate-200 pb-6">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-3xl font-bold">{booking.event_title}</h1>
          <span
            className={`mt-1 whitespace-nowrap rounded-full px-3 py-1 text-xs font-medium ${badge.cls}`}
          >
            {badge.label}
          </span>
        </div>
        <p className="mt-3 text-slate-600">
          {fmtDayLabel(booking.start_utc, tz)}, {fmtTime(booking.start_utc, tz)}{" "}
          ({tz})
        </p>
        <p className="mt-1 text-sm text-slate-500">
          {booking.event_duration_minutes} мин · {booking.host_name}
        </p>
      </header>

      {!modifiable ? (
        <p className="mt-8 text-slate-600">
          {status === "canceled"
            ? "Бронь отменена. Если нужно встретиться — создайте новую запись."
            : status === "rescheduled"
              ? "Бронь перенесена — действует новая встреча по обновлённой ссылке."
              : "Эту бронь уже нельзя изменить."}
        </p>
      ) : mode === "view" ? (
        <div className="mt-8 flex flex-wrap gap-3">
          <button type="button" onClick={() => open("reschedule")} className={primaryBtn}>
            Перенести
          </button>
          <button
            type="button"
            onClick={() => open("cancel")}
            className="rounded-lg border border-slate-300 px-5 py-3 font-medium text-slate-700 transition hover:border-red-400 hover:text-red-600"
          >
            Отменить
          </button>
        </div>
      ) : mode === "cancel" ? (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">Отменить бронь</h2>
          <p className="mt-1 text-sm text-slate-500">
            Слот освободится для других гостей. Действие необратимо.
          </p>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder="Причина отмены (необязательно)"
            className={`mt-3 ${inputClass}`}
          />
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={busy}
              className="rounded-lg bg-red-600 px-5 py-3 font-medium text-white transition hover:bg-red-700 disabled:opacity-60"
            >
              {busy ? "Отменяем…" : "Подтвердить отмену"}
            </button>
            <button
              type="button"
              onClick={() => open("view")}
              disabled={busy}
              className={secondaryBtn}
            >
              Назад
            </button>
          </div>
        </section>
      ) : (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">Перенести на другое время</h2>
          <SlotPicker
            slug={booking.host_slug}
            eventSlug={booking.event_slug}
            fallbackTz={tz}
            selectedStartUtc={newSlot?.start_utc ?? null}
            onSelect={setNewSlot}
          />
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          <div className="mt-6 flex gap-3">
            <button
              type="button"
              onClick={onReschedule}
              disabled={busy || !newSlot}
              className={primaryBtn}
            >
              {busy ? "Переносим…" : "Подтвердить перенос"}
            </button>
            <button
              type="button"
              onClick={() => {
                setNewSlot(null);
                open("view");
              }}
              disabled={busy}
              className={secondaryBtn}
            >
              Назад
            </button>
          </div>
        </section>
      )}
    </main>
  );
}
