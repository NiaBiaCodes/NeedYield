import type { FoodLocation, PublicResource, Reservation } from '../types'

const configuredApiUrl = String(import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const API_URL = configuredApiUrl.endsWith('/api') ? configuredApiUrl : `${configuredApiUrl}/api`

export class ApiRequestError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

type ApiLocation = {
  id: string; name: string; address: string; borough: string; neighborhood: string
  latitude: number; longitude: number; opening_time: string; closing_time: string
  accepted_categories: string[]; saturday_needs: Record<string, string>; inventory: Record<string, number>
  verified_partner: boolean; participating: boolean; accepts_saturday: boolean; demo: boolean; community_need_score: number; community_need_source: string
}

export type AnalysisResult = {
  items: { name: string; estimated_quantity: number; confidence: number }[]
  source: 'gemini' | 'mock_fallback'
  review_recommended: boolean
  message: string
}

export type Allocation = {
  location_id: string; location_name: string; produce: string; quantity: number
  score: number; distance_miles: number; preferred: boolean; reasons: string[]
}

export type MatchResult = {
  preferred_allocations: Allocation[]
  recommended_allocations: Allocation[]
  remaining_surplus: Record<string, number>
  surplus_alert: boolean
  data_source: string
}

export type MatchInput = {
  gardener_latitude: number; gardener_longitude: number; preferred_location_id: string
  preferred_radius_miles: number; items: { name: string; quantity: number; unit: string }[]
}

export type RagResult = {
  answer: string
  recommendations: { resource_id: string; name: string; address: string; neighborhood: string; borough: string; hours: string; available_inventory: Record<string, number>; distance_miles: number | null; reasons: string[] }[]
  sources: { resource_id: string; name: string; source: string; source_url?: string }[]
  retrieved_count: number
  retrieval_mode: string
  generation_mode: string
  fallback: boolean
}

function displayProduce(key: string) {
  const lower = key.toLowerCase()
  const names: Record<string, string> = { tomato: 'Tomatoes', tomatoes: 'Tomatoes', cucumber: 'Cucumbers', cucumbers: 'Cucumbers', zucchini: 'Zucchini', kale: 'Kale', spinach: 'Spinach', pepper: 'Peppers', peppers: 'Peppers', carrot: 'Carrots', carrots: 'Carrots', herb: 'Herbs', herbs: 'Herbs' }
  return names[lower] || key.charAt(0).toUpperCase() + key.slice(1)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let authHeaders: Record<string, string> = {}
  try {
    const stored = JSON.parse(localStorage.getItem('needyield-auth') || 'null')
    if (stored?.accessToken) authHeaders.Authorization = `Bearer ${stored.accessToken}`
    else if (stored?.user?.demo) authHeaders = { 'X-Demo-User': stored.user.id, 'X-Demo-Role': stored.user.role, 'X-Demo-Admin': String(Boolean(stored.user.isAdmin)) }
  } catch { /* An invalid local session is treated as signed out. */ }
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers: { ...authHeaders, ...Object.fromEntries(new Headers(init?.headers).entries()) }, signal: init?.signal || AbortSignal.timeout(5000) })
  } catch (error) {
    if (error instanceof DOMException && (error.name === 'AbortError' || error.name === 'TimeoutError')) {
      throw new ApiRequestError('The request took too long. Please try again.', 408)
    }
    throw error
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiRequestError(body?.detail || `Request failed (${response.status})`, response.status)
  }
  return response.json()
}

export async function getLocations(): Promise<FoodLocation[]> {
  const locations = await request<ApiLocation[]>('/locations')
  return mapLocations(locations)
}

function mapLocations(locations: ApiLocation[]): FoodLocation[] {
  return locations.map((location) => ({
    id: location.id, name: location.name, address: location.address, borough: location.borough,
    neighborhood: location.neighborhood, latitude: location.latitude, longitude: location.longitude,
    openingTime: location.opening_time, closingTime: location.closing_time,
    inventory: Object.entries(location.inventory).map(([produce, quantity]) => ({ produce: displayProduce(produce), quantity })),
    acceptedCategories: location.accepted_categories, saturdayNeeds: location.saturday_needs,
    verifiedPartner: location.verified_partner, participating: location.participating,
    acceptsSaturday: location.accepts_saturday, demo: location.demo,
    communityNeedScore: location.community_need_score, communityNeedSource: location.community_need_source,
  }))
}

export async function getDonationDestinations(): Promise<FoodLocation[]> {
  return mapLocations(await request<ApiLocation[]>('/locations/donation-destinations'))
}

export async function getFoodMutualAidResources(audience: 'neighbor' | 'gardener' = 'neighbor'): Promise<{ resources: PublicResource[]; source: string; fallback: boolean }> {
  const payload = await request<{ resources: { id: string; name: string; resource_type: string; address: string; borough: string; neighborhood: string; latitude: number; longitude: number; website?: string; description?: string; source: string; source_dataset_id: string; verified_partner: false; donation_acceptance_verified: boolean; matched_terms: string[]; food_relevance_score: number; acceptance_note: string; operating_information?: string }[]; source: string; fallback: boolean }>(`/resources/food-mutual-aid?limit=40&audience=${audience}`)
  return { source: payload.source, fallback: payload.fallback, resources: payload.resources.map((item) => ({ id: item.id, name: item.name, resourceType: item.resource_type, address: item.address, borough: item.borough, neighborhood: item.neighborhood, latitude: item.latitude, longitude: item.longitude, website: item.website, description: item.description, source: item.source, sourceDatasetId: item.source_dataset_id, verifiedPartner: false, donationAcceptanceVerified: item.donation_acceptance_verified, matchedTerms: item.matched_terms, foodRelevanceScore: item.food_relevance_score, acceptanceNote: item.acceptance_note, operatingInformation: item.operating_information })) }
}

export async function createReservation(input: { locationId: string; produce: string; quantity: number }): Promise<Reservation> {
  const payload = await request<{ id: string; location_id: string; location_name: string; location_address: string; produce: string; quantity: number; created_at: string; expires_at: string; status: Reservation['status'] }>('/reservations', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ location_id: input.locationId, produce: input.produce.toLowerCase(), quantity: input.quantity }),
  })
  return { id: payload.id, locationId: payload.location_id, locationName: payload.location_name, locationAddress: payload.location_address, produce: displayProduce(payload.produce), quantity: payload.quantity, reservedAt: payload.created_at, expiresAt: payload.expires_at, status: payload.status }
}

export async function getReservations(): Promise<Reservation[]> {
  const rows = await request<{ id: string; location_id: string; location_name: string; location_address: string; produce: string; quantity: number; created_at: string; expires_at: string; status: Reservation['status'] }[]>('/reservations')
  return rows.map((row) => ({ id: row.id, locationId: row.location_id, locationName: row.location_name, locationAddress: row.location_address, produce: displayProduce(row.produce), quantity: row.quantity, reservedAt: row.created_at, expiresAt: row.expires_at, status: row.status }))
}

export async function expireReservation(id: string): Promise<void> {
  await request(`/demo/expire-reservation/${id}`, { method: 'POST' })
}

export async function analyzeProduce(file: File): Promise<AnalysisResult> {
  const body = new FormData(); body.append('image', file)
  return request('/analyze-produce', { method: 'POST', body, signal: AbortSignal.timeout(60_000) })
}

export async function matchDistribution(input: MatchInput): Promise<MatchResult> {
  return request('/match-distribution', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) })
}

export async function confirmDonation(input: MatchInput, allocations: Allocation[]): Promise<void> {
  await request('/donations/confirm', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ gardener_id: 'demo-gardener', preferred_location_id: input.preferred_location_id, preferred_radius_miles: input.preferred_radius_miles, items: input.items, allocations }) })
}

export async function queryRag(input: { query: string; latitude?: number; longitude?: number }): Promise<RagResult> {
  return request('/rag/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input), signal: AbortSignal.timeout(60_000) })
}

export type OrganizationApplication = {
  id: string; user_id: string; email: string; organization_name: string; organization_type: string
  address: string; borough: string; neighborhood: string; contact_name: string; phone: string
  accepted_categories: string[]; opening_time: string; closing_time: string; notes: string
  status: 'PENDING' | 'APPROVED' | 'REJECTED'; created_at: string; location_id?: string; review_note: string
}

export type WeeklyNeeds = { distribution_date: string; accepting_donations: boolean; dropoff_start: string; dropoff_end: string; notes: string; items: { produce_name: string; need_level: string; requested_quantity: number }[]; location_id: string; submitted_at: string }

export const getOrganizationApplication = () => request<OrganizationApplication | null>('/organizations/application')
export const submitOrganizationApplication = (payload: Omit<OrganizationApplication, 'id' | 'user_id' | 'email' | 'status' | 'created_at' | 'location_id' | 'review_note'>) => request<OrganizationApplication>('/organizations/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
export const getOrganizationApplications = () => request<OrganizationApplication[]>('/admin/organization-applications')
export const approveOrganization = (id: string, latitude: number, longitude: number) => request<OrganizationApplication>(`/admin/organization-applications/${id}/approve`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ latitude, longitude, review_note: 'Identity and location verified for participation' }) })
export const rejectOrganization = (id: string, review_note: string) => request<OrganizationApplication>(`/admin/organization-applications/${id}/reject`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ review_note }) })
export const submitWeeklyNeeds = (payload: Omit<WeeklyNeeds, 'location_id' | 'submitted_at'>) => request<WeeklyNeeds>('/organizations/weekly-needs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
