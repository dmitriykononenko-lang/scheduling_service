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
