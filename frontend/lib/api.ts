// Тонкий клиент к публичному REST API бэкенда.

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const API_V1 = `${API_BASE_URL}/api/v1`;

export interface HostPublic {
  id: string;
  name: string;
  slug: string;
  timezone: string;
}

export interface EventTypePublic {
  id: string;
  user_id: string;
  slug: string;
  title: string;
  description: string | null;
  duration_minutes: number;
  price: string | null;
  currency: string;
  requires_prepay: boolean;
  location_type: string;
}

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_V1}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    // Бэкенд может быть не запущен (например, при статической сборке) — отдаём null.
    return null;
  }
}

export function getPublicProfile(slug: string): Promise<HostPublic | null> {
  return getJson<HostPublic>(`/public/${encodeURIComponent(slug)}`);
}

export function getPublicEventTypes(
  slug: string,
): Promise<EventTypePublic[] | null> {
  return getJson<EventTypePublic[]>(
    `/public/${encodeURIComponent(slug)}/event-types`,
  );
}

// --- Детальная карточка типа встречи (с анкетой) ---

export interface QuestionPublic {
  id: string;
  label: string;
  field_type: "text" | "textarea" | "select" | "checkbox";
  required: boolean;
  options: string[] | null;
  position: number;
}

export interface EventTypeDetail extends EventTypePublic {
  questions: QuestionPublic[];
}

export function getPublicEventType(
  slug: string,
  eventSlug: string,
): Promise<EventTypeDetail | null> {
  return getJson<EventTypeDetail>(
    `/public/${encodeURIComponent(slug)}/event-types/${encodeURIComponent(eventSlug)}`,
  );
}

// --- Свободные слоты ---

export interface SlotRead {
  start_utc: string;
  end_utc: string;
  start_local: string; // в запрошенном поясе гостя
}

export interface SlotsResponse {
  event_type_slug: string;
  timezone: string;
  slots: SlotRead[];
}

export function getSlots(
  slug: string,
  eventSlug: string,
  from: string,
  to: string,
  tz?: string,
): Promise<SlotsResponse | null> {
  const params = new URLSearchParams({ from, to });
  if (tz) params.set("tz", tz);
  return getJson<SlotsResponse>(
    `/public/${encodeURIComponent(slug)}/event-types/${encodeURIComponent(eventSlug)}/slots?${params.toString()}`,
  );
}

// --- Создание брони ---

export interface BookingCreateRequest {
  start_utc: string;
  invitee_name: string;
  invitee_contact: string;
  invitee_email?: string;
  invitee_timezone?: string;
  answers: Record<string, unknown>;
}

export interface BookingRead {
  id: string;
  event_type_id: string;
  host_id: string;
  invitee_name: string;
  invitee_contact: string;
  invitee_email: string | null;
  invitee_timezone: string | null;
  start_utc: string;
  end_utc: string;
  status: string;
  location_url: string | null;
  answers: Record<string, unknown>;
  rescheduled_from_id: string | null;
  created_at: string;
}

export interface BookingCreateResponse {
  booking: BookingRead;
  management_token: string;
  manage_url: string;
}

export type MutationResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string };

/** Достаёт читаемое сообщение из тела ошибки FastAPI: {detail: string | [{msg}]}. */
function extractError(body: unknown): string | null {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const msgs = detail
        .map((d) =>
          d && typeof d === "object" && "msg" in d
            ? String((d as { msg: unknown }).msg)
            : null,
        )
        .filter((m): m is string => Boolean(m));
      if (msgs.length) return msgs.join("; ");
    }
  }
  return null;
}

export async function createBooking(
  slug: string,
  eventSlug: string,
  body: BookingCreateRequest,
): Promise<MutationResult<BookingCreateResponse>> {
  try {
    const res = await fetch(
      `${API_V1}/public/${encodeURIComponent(slug)}/event-types/${encodeURIComponent(eventSlug)}/bookings`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        cache: "no-store",
      },
    );
    const data = (await res.json().catch(() => null)) as unknown;
    if (!res.ok) {
      return {
        ok: false,
        error: extractError(data) ?? `Ошибка сервера (${res.status})`,
      };
    }
    return { ok: true, data: data as BookingCreateResponse };
  } catch {
    return {
      ok: false,
      error:
        "Не удалось связаться с сервером. Проверьте соединение и попробуйте снова.",
    };
  }
}
