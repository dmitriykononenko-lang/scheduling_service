"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { getSlots, type SlotRead } from "@/lib/api";
import { dayKey, fmtDayLabel, fmtTime } from "@/lib/datetime";

const HORIZON_DAYS = 30;

type SlotsState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; slots: SlotRead[] };

/**
 * Выбор свободного слота в поясе гостя. Сам определяет пояс браузера и грузит слоты;
 * выбор хранит родитель (через `onSelect`). Используется и в записи, и в переносе брони.
 */
export function SlotPicker({
  slug,
  eventSlug,
  fallbackTz,
  selectedStartUtc,
  onSelect,
  onTzResolved,
}: {
  slug: string;
  eventSlug: string;
  /** Детерминированный пояс для SSR/первой отрисовки до определения браузерного. */
  fallbackTz: string;
  selectedStartUtc: string | null;
  /** Выбор слота; null — сброс (например, при смене дня). */
  onSelect: (slot: SlotRead | null) => void;
  onTzResolved?: (tz: string) => void;
}) {
  const [tz, setTz] = useState(fallbackTz);
  const [slotsState, setSlotsState] = useState<SlotsState>({ status: "loading" });
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  // «Свежий» колбэк пояса без перезапуска эффекта загрузки слотов.
  const onTzResolvedRef = useRef(onTzResolved);
  useEffect(() => {
    onTzResolvedRef.current = onTzResolved;
  });

  useEffect(() => {
    let cancelled = false;
    // Пояс гостя доступен только на клиенте — определяем и сразу грузим слоты в нём.
    let effectiveTz = fallbackTz;
    try {
      const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (browserTz) effectiveTz = browserTz;
    } catch {
      // оставляем запасной пояс
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
      onTzResolvedRef.current?.(effectiveTz);
      setSlotsState(
        resp ? { status: "ready", slots: resp.slots } : { status: "error" },
      );
    });
    return () => {
      cancelled = true;
    };
  }, [slug, eventSlug, fallbackTz]);

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
  const activeDaySlots = days.find((d) => d.key === activeDay)?.slots ?? [];

  if (slotsState.status === "loading") {
    return <p className="mt-4 text-slate-500">Загружаем свободные слоты…</p>;
  }
  if (slotsState.status === "error") {
    return (
      <p className="mt-4 text-red-600">
        Не удалось загрузить слоты. Обновите страницу или попробуйте позже.
      </p>
    );
  }
  if (days.length === 0) {
    return (
      <p className="mt-4 text-slate-600">
        На ближайшие {HORIZON_DAYS} дней свободных слотов нет.
      </p>
    );
  }

  return (
    <div className="mt-4">
      <div className="flex flex-wrap gap-2">
        {days.map((d) => (
          <button
            key={d.key}
            type="button"
            onClick={() => {
              setSelectedDay(d.key);
              onSelect(null);
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
            onClick={() => onSelect(s)}
            className={`rounded-lg border px-3 py-2 text-sm transition ${
              selectedStartUtc === s.start_utc
                ? "border-brand bg-brand text-white"
                : "border-slate-200 hover:border-brand"
            }`}
          >
            {fmtTime(s.start_utc, tz)}
          </button>
        ))}
      </div>
    </div>
  );
}
