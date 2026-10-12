import type { WardrobePhotosResponse } from '../../common/type'
import { apiRequest } from '../../shared/api'

export function uploadWardrobePhotos(images: File[]): Promise<WardrobePhotosResponse> {
  const formData = new FormData()
  for (const image of images) formData.append('images', image)
  return apiRequest<WardrobePhotosResponse>('POST', '/api/wardrobe-photos', formData)
}
