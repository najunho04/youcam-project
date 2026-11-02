# Devpost 제출 로드맵

**마감: 2026-11-02 11:45 EST = 2026-11-03(화) 01:45 KST.** Devpost 는 마감 직전에 몰리니 먼저 Draft 로 저장해 두고 채운다.

## 체크리스트

| # | 항목 | 상태 | 결과물 / 위치 |
|---|---|---|---|
| 1 | 영어 README (소개·YouCam API·구조·실행 방법) | ✅ 완료 | [`/README.md`](../README.md) |
| 2 | 레포 공개 + LICENSE (MIT) | ✅ 완료 | https://github.com/najunho04/youcam-project · [`/LICENSE`](../LICENSE) |
| 3 | 운영 서버 점검 (YouCam 키 교체, 진단·피팅 버그 수정, 상품 이미지 고화질, 중복 상품 51개 제거) | ✅ 완료 | 커밋 `6017357` `e4c9526` `9e81ec6`, 운영 DB 상품 1,477개 |
| 4 | 심사위원용 테스트 계정 | ✅ 완료 | 계정 정보는 Devpost "Testing instructions" 칸에 직접 입력 (레포에 비밀번호 저장 안 함) |
| 5 | 스크린샷 (데스크톱 1440×900, 실제 운영 백엔드 데이터) | ✅ 완료 | [`screenshots/`](screenshots/) — 아래 표 |
| 6 | 썸네일 (3:2) | ✅ 완료 | [`screenshots/00-thumbnail-3x2.png`](screenshots/00-thumbnail-3x2.png) |
| 7 | Devpost 텍스트 (Tagline, About, Built with, YouCam API, 테스트 안내) | ✅ 완료 | [`devpost.md`](devpost.md) |
| 8 | 데모 영상 대본 | ✅ 완료 | [`devpost.md` → 데모 영상 대본](devpost.md#데모-영상-대본-영어-내레이션-약-2분-30초-음악-없음-또는-무료-음원) |
| 9 | SNS 공유 문구 | ✅ 완료 | [`devpost.md` → SNS 공유 문구](devpost.md#sns-공유-문구-보너스-폼용-선택) |
| 10 | 데모 영상 촬영·YouTube 업로드 | ✅ 완료 | https://youtu.be/BXzXxAc_a8Q |
| 11 | 데모 URL 확인 (Vercel 프로덕션 도메인) | ✅ 완료 | https://colorfit-topaz.vercel.app/ |
| 12 | README TODO 채우기 (데모 URL, 영상 링크) | ✅ 완료 | [`/README.md`](../README.md) 상단 |
| 13 | **Devpost 제출** — 7번 텍스트 붙여넣기, 스크린샷·썸네일 업로드, 영상·데모·레포 링크, **Rising Star(학생) 체크 + `najoonho@khu.ac.kr`** | ⬜ 직접 | 제출 후 상태가 **Submitted** 인지 확인 |

## 스크린샷

갤러리 업로드 순서 추천: 00 → 03 → 04 → 06 → 09 → 05 → 01. `02`·`08` 은 영상이나 보조용.

| 파일 | 화면 | 용도 |
|---|---|---|
| [`00-thumbnail-3x2.png`](screenshots/00-thumbnail-3x2.png) | 추천 화면 (3:2 크롭) | **썸네일** |
| [`01-landing.png`](screenshots/01-landing.png) | 랜딩 | 갤러리 |
| [`02-photo-upload.png`](screenshots/02-photo-upload.png) | 얼굴·상반신 사진 2장 업로드 | 보조 |
| [`03-personal-color-result.png`](screenshots/03-personal-color-result.png) | 퍼스널컬러 결과 (Soft Autumn, 팔레트) | 갤러리 (핵심) |
| [`04-personal-color-evidence-full.png`](screenshots/04-personal-color-evidence-full.png) | 결과 + 판정 근거 전체 (YouCam 얼굴 색 5개, 3개 축) | 갤러리 (핵심) |
| [`05-swipe.png`](screenshots/05-swipe.png) | 스와이프 온보딩 | 갤러리 |
| [`06-recommendations.png`](screenshots/06-recommendations.png) | 추천 상품 (eBay, 가격, 추천 이유) | 갤러리 (핵심) |
| [`07-recommendations-full.png`](screenshots/07-recommendations-full.png) | 추천 6개 전체 | 보조 |
| [`08-fitting-pending.png`](screenshots/08-fitting-pending.png) | 가상 피팅 진행 중 | 보조 |
| [`09-fitting-result.png`](screenshots/09-fitting-result.png) | YouCam 가상 피팅 결과 (원본 ↔ 결과 슬라이더, Buy now) | 갤러리 (핵심) |

- 로컬 프론트 + **운영 백엔드**로 실제 흐름을 돌려 찍었다 (목업 응답 아님). 진단·피팅 결과는 실제 YouCam 응답이다.
- 사진은 랜딩용 AI 생성 인물 이미지(`project/front/public/landing/hero-woman-photo.webp`)를 썼다. 실제 인물 사진이 아니다.
- 촬영용 계정 `demo6749`, `demo8346` 과 진단 테스트 계정 `diag23617`, `diag10651`, `diag947` 이 운영 DB 에 남아 있다. 필요 없으면 삭제.

## 제출 직전 확인

- [ ] 데모 URL 에서 가입 → 진단 → 스와이프 → 추천 → 피팅 한 번 통과
- [ ] 영상이 로그인 없이 재생되는지 (시크릿 창)
- [ ] 레포가 Public 이고 README 상단 링크가 채워졌는지
- [ ] Rising Star 체크, 학교 이메일
- [ ] Devpost 상태 **Submitted**
