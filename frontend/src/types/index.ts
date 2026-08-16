export type InventoryItem = {
  produce: string
  quantity: number
}

export type FoodLocation = {
  id: string
  name: string
  address: string
  borough: string
  neighborhood: string
  latitude: number
  longitude: number
  openingTime: string
  closingTime: string
  inventory: InventoryItem[]
  acceptedCategories?: string[]
  saturdayNeeds?: Record<string, string>
  verifiedPartner?: boolean
  participating?: boolean
  acceptsSaturday?: boolean
  demo?: boolean
  communityNeedScore?: number
  communityNeedSource?: string
}

export type PublicResource = {
  id: string
  name: string
  resourceType: string
  address: string
  borough: string
  neighborhood: string
  latitude: number
  longitude: number
  website?: string
  description?: string
  source: string
  sourceDatasetId: string
  verifiedPartner: false
  donationAcceptanceVerified: boolean
  matchedTerms: string[]
  foodRelevanceScore: number
  acceptanceNote: string
  operatingInformation?: string
}

export type ReservationStatus = 'RESERVED' | 'PICKED_UP' | 'EXPIRED' | 'RELEASED'

export type Reservation = {
  id: string
  locationId: string
  locationName: string
  locationAddress: string
  produce: string
  quantity: number
  reservedAt: string
  expiresAt: string
  status: ReservationStatus
}
