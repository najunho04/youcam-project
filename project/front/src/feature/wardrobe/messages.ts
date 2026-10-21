// wardrobe 슬라이스 문구 (영어 · 한국어)

const ENGLISH = {
  title: 'Clothes you love to wear',
  guide: (limit: number) => `Upload up to ${limit} photos of outfits or clothes you like and we'll factor them into your style.`,
  tooManyPhotos: (limit: number) => `You can choose up to ${limit} photos.`,
  wrongImageType: 'Only JPG or PNG photos can be uploaded.',
  upload: 'Upload',
  skip: 'Skip',
  optional: 'Optional',
  selectedPhoto: (number: number) => `Selected photo ${number}`,
  choosePhotos: 'Choose photos',
  imageTypeNote: 'JPG or PNG only',
  uploading: 'Uploading…',
}

const KOREAN: typeof ENGLISH = {
  title: '평소 즐겨 입는 옷',
  guide: (limit: number) => `좋아하는 착용 사진이나 옷 사진을 최대 ${limit}장 올리면 취향 분석에 반영돼요`,
  tooManyPhotos: (limit: number) => `사진은 최대 ${limit}장까지 선택할 수 있습니다`,
  wrongImageType: 'jpg 또는 png 사진만 올릴 수 있습니다',
  upload: '업로드',
  skip: '건너뛰기',
  optional: '선택 사항이에요',
  selectedPhoto: (number: number) => `선택한 사진 ${number}`,
  choosePhotos: '사진 선택',
  imageTypeNote: 'jpg 또는 png 사진만 올릴 수 있어요',
  uploading: '업로드 중…',
}

export const WARDROBE_MESSAGES = { en: ENGLISH, ko: KOREAN }
