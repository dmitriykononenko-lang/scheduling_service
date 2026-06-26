// Форматирование дат в поясе гостя (от UTC-инстанта, без зависимости от start_local).

/** Стабильный ключ дня (YYYY-MM-DD) в поясе гостя. */
export function dayKey(iso: string, tz: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(iso));
}

export function fmtDayLabel(iso: string, tz: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    timeZone: tz,
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date(iso));
}

export function fmtTime(iso: string, tz: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}
