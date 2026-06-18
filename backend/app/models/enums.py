"""Перечисления предметной области."""

from enum import StrEnum


class UserRole(StrEnum):
    host = "host"  # организатор
    team_member = "team_member"  # член команды (Ф3)
    account_admin = "account_admin"  # администратор аккаунта (Ф3)
    system_admin = "system_admin"  # внутренний системный администратор


class EventVisibility(StrEnum):
    public = "public"  # виден в общем профиле
    unlisted = "unlisted"  # только по прямой ссылке (скрытый)


class LocationType(StrEnum):
    video = "video"  # видеозвонок (Zoom/Meet/Телемост/Jitsi)
    phone = "phone"
    address = "address"  # офлайн-адрес
    custom = "custom"


class QuestionFieldType(StrEnum):
    text = "text"
    textarea = "textarea"
    select = "select"
    checkbox = "checkbox"


class BookingStatus(StrEnum):
    pending_payment = "pending_payment"  # ждёт оплаты (предоплатный тип)
    confirmed = "confirmed"
    canceled = "canceled"
    rescheduled = "rescheduled"
    completed = "completed"
    no_show = "no_show"  # неявка


class PaymentStatus(StrEnum):
    pending = "pending"  # ожидание
    succeeded = "succeeded"  # оплачено
    failed = "failed"
    refunded = "refunded"  # возврат
    partially_refunded = "partially_refunded"


class PaymentProvider(StrEnum):
    yookassa = "yookassa"  # ЮKassa
    tbank = "tbank"  # Т-Банк


class CalendarProvider(StrEnum):
    google = "google"
    microsoft = "microsoft"  # Outlook / Microsoft Graph
    apple = "apple"  # CalDAV
    yandex = "yandex"  # Яндекс.Календарь (CalDAV)


class NotificationChannel(StrEnum):
    email = "email"
    telegram = "telegram"
    sms = "sms"  # Ф2, опц.


class NotificationType(StrEnum):
    confirmation = "confirmation"
    reminder = "reminder"
    cancellation = "cancellation"
    reschedule = "reschedule"


class NotificationStatus(StrEnum):
    scheduled = "scheduled"
    sent = "sent"
    failed = "failed"
    canceled = "canceled"


class SubscriptionPlan(StrEnum):
    free = "free"
    pro = "pro"
    team = "team"  # Ф3


class SubscriptionStatus(StrEnum):
    trialing = "trialing"
    active = "active"
    past_due = "past_due"
    canceled = "canceled"


class SubscriptionPeriod(StrEnum):
    monthly = "monthly"
    yearly = "yearly"
