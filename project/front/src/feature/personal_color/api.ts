import type { PersonalColorDto } from '../../common/type'
import { apiRequest } from '../../shared/api'

export function analyzePersonalColor(selfie: File, bodyImage: File): Promise<PersonalColorDto> {
  const formData = new FormData()
  formData.append('selfie', selfie)
  formData.append('bodyImage', bodyImage)
  return apiRequest<PersonalColorDto>('POST', '/api/personal-color', formData)
}
