import type { Reservation } from '../types'

export function getTodayDeadline(now = new Date()): Date {
  const dateInNewYork = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now)

  const noonUtc = new Date(`${dateInNewYork}T12:00:00Z`)
  const timeParts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    timeZoneName: 'longOffset',
  }).formatToParts(noonUtc)
  const offset = timeParts.find((part) => part.type === 'timeZoneName')?.value.replace('GMT', '') || '-04:00'
  return new Date(`${dateInNewYork}T17:00:00${offset}`)
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(new Date(value))
}

export function expireReservations(reservations: Reservation[], now = new Date(), forceReservationId?: string) {
  const released: Reservation[] = []
  const updated = reservations.map((reservation) => {
    if (reservation.status === 'RESERVED' && (reservation.id === forceReservationId || new Date(reservation.expiresAt) <= now)) {
      const expired = { ...reservation, status: 'EXPIRED' as const }
      released.push(expired)
      return expired
    }
    return reservation
  })
  return { updated, released }
}
