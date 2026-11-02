# Devpost 제출 텍스트 (복사해서 붙여넣기)

각 블록을 Devpost 양식의 같은 이름 칸에 그대로 붙여넣는다. `<!-- -->` 안은 직접 채울 값.

---

## Project name

```
ColorFit
```

## Elevator pitch / Tagline (200자 이내)

```
A selfie and 20 swipes find real eBay tops that suit your personal color and match your taste — then YouCam AI lets you try them on before you buy.
```

(대안, 더 짧게)

```
Personal color × your taste → virtual try-on → buy. Powered by YouCam AI.
```

---

## About the project (Markdown)

```markdown
## Inspiration

Online fashion shopping asks two questions at once — *"does this suit me?"* and *"is this my style?"* — and gives you tools for neither. Personal color analysis lives in beauty apps, shopping lives in stores, and because you can't try anything on, you either hesitate or send it back. We wanted one flow that answers both questions and ends with a real product on your own photo.

## What it does

1. **Personal color, with evidence.** Upload a face photo and an upper-body photo. The YouCam **AI Facial Color Tones Analyzer** returns your skin, lip, eye, eyebrow and hair colors; ColorFit classifies you into one of **12 personal color types** (e.g. *Soft Autumn*) and shows *why* — the five detected colors, scores on three axes (warmth, depth, clarity), skin lightness and contrast.
2. **Taste in 20 swipes.** Like or dislike outfit photos; a FashionCLIP taste vector is built from your answers (optional: upload outfit photos you love).
3. **Recommendations you can explain.** ~1,500 real eBay tops are ranked by `0.7 × taste similarity + 0.3 × color harmony` against your 12-type palette, with "avoid" colors penalized. Every card shows why it was picked and its USD price.
4. **Try it on, then buy it.** One click sends your upper-body photo and the actual product image to YouCam **AI Clothes Virtual Try-On (cloth-v4)**. Drag a slider to compare original vs. try-on, then **Buy now** opens the same eBay listing.

The item you try on is the item you buy — not a look-alike.

## How we built it

- **YouCam APIs (server-side, async task + polling)**
  - `skin-tone-analysis` — every color field is used. Classification runs in CIE Lab: warmth = skin hue (70%) + lip hue (30%); depth = skin L* (60%) + contrast (40%); clarity = skin chroma (60%) + lip chroma (40%). Warmth × depth gives the season; the most pronounced axis gives the subtype → 12 types.
  - `cloth-v4` — `POST /api/fittings` returns 202 immediately, a background worker polls YouCam to completion and stores the result in S3, the browser polls for status. Results are cached per (user photo × product), so re-trying an item costs no credits.
- **Recommendation engine** — FashionCLIP image embeddings in PostgreSQL + pgvector. Taste vector `u = normalize(mean(liked) + w·mean(wardrobe) − β·mean(disliked))`. Each product's dominant color is extracted once at ingest (border-pixel background removal + K-means, k=3) and scored by ΔE to the user's palette.
- **Product data** — eBay Browse API batch: tops for women and men, embedded, style-classified with FashionCLIP, deduplicated and manually reviewed. Only image URLs are stored, never the images.
- **Frontend** — React 19 + TypeScript + Vite, MediaPipe face / upper-body guides for capture, English and Korean UI.
- **Backend & infra** — Python 3.13 + FastAPI on AWS EC2 (Caddy, Docker), Neon Postgres, private S3 with presigned URLs, Vercel for the SPA, GitHub Actions CI → ECR → SSM deploy.
- **Process** — built solo with "vertical feature slices": each feature (auth, profile, personal_color, swipe, wardrobe, recommendation, fitting, product_ingest) is an isolated slice with frozen contract tests and import-boundary checks, which let AI-assisted sessions work in parallel without breaking each other.

## Challenges we ran into

- **Turning five colors into a trustworthy verdict.** A season label alone feels like magic; we designed three measurable axes and surface every number so users can see the reasoning.
- **Dominant color of messy product photos.** eBay images have random backgrounds and models; estimating the background from border pixels before K-means made colors far more accurate.
- **Real-world API edge cases.** YouCam omits `hair_color` when it can't find hair, and rejects photos over 4096 px. We fill missing hair/eyebrow colors from each other, normalize uploads (EXIF rotation, resize), and log the upstream error code.
- **Credits.** Try-on is async and expensive, so every started task is polled to completion (timed-out tasks are still billed) and results are cached.

## Accomplishments that we're proud of

- An **explainable** personal color result instead of a black-box label.
- A complete loop from selfie to purchase link in about three minutes, on real products.
- 300+ backend and 120+ frontend tests, with contract tests frozen before implementation.

## What we learned

- Showing the evidence matters as much as the answer — users trust a result they can check.
- Async-first design (202 + polling + cache) is essential when an AI call takes tens of seconds and costs credits.
- Small, isolated slices with machine-enforced boundaries make solo + AI development much more reliable.

## What's next

- Skin analysis (YouCam Skin AI) for skincare and makeup recommendations that match the same personal color.
- Bottoms, outerwear and full-outfit try-on.
- Learning from feedback on recommendations, and more marketplaces (e.g. Naver Shopping for Korean users).
```

---

## Built with (태그)

```
react, typescript, vite, python, fastapi, postgresql, pgvector, pytorch, fashionclip, mediapipe, youcam-api, ebay-api, amazon-web-services, amazon-ec2, amazon-s3, neon, vercel, docker, github-actions
```

## Try it out (링크)

| 라벨 | URL |
|---|---|
| Live demo | https://colorfit-topaz.vercel.app/ |
| Source code | https://github.com/najunho04/youcam-project |

## Video demo link

```
<!-- https://youtu.be/... (공개 또는 일부 공개) -->
```

## 사용한 YouCam API (대회 질문 칸이 있으면)

```
1) AI Facial Color Tones Analyzer (skin-tone-analysis) — personal color diagnosis. We use all returned fields (skin, lip, eye, eyebrow, hair colors and eye/hair color names) to classify 12 personal color types and show the evidence.
2) AI Clothes Virtual Try-On (cloth-v4) — tries the recommended eBay product on the user's upper-body photo; async with polling and per-(photo, product) caching.
```

## 심사위원용 테스트 접근 (Testing instructions)

```
Live demo: https://colorfit-topaz.vercel.app/
Test account — nickname: <!-- --> / password: <!-- -->
This account has already completed personal color and swipes, so it opens straight to recommendations. You can also sign up with any nickname (no email needed) and go through the full flow in about 3 minutes.
Tip: for the face photo, face the camera directly in even light with your face filling most of the frame.
```

---

## 데모 영상 대본 (영어 내레이션, 약 2분 30초, 음악 없음 또는 무료 음원)

| 시간 | 화면 | 내레이션 |
|---|---|---|
| 0:00–0:15 | 랜딩 | "Shopping online, you're always asking two questions: does this suit me, and is it my style? ColorFit answers both — and lets you try it on before you buy." |
| 0:15–0:45 | 사진 2장 업로드 → Analyze → 결과 | "I upload a face photo and an upper-body photo. ColorFit sends the face to YouCam's AI Facial Color Tones Analyzer, which returns my skin, lip, eye, eyebrow and hair colors. From those, we classify one of twelve personal color types — here, Soft Autumn." |
| 0:45–1:10 | 판정 근거(Why this result) 스크롤 | "And it shows why. These are the five colors YouCam found. We score warmth, depth and clarity in CIE Lab space — every number behind the verdict is right here, plus the colors that suit me and the ones to avoid." |
| 1:10–1:30 | 스와이프 | "Next, twenty quick swipes. Each outfit is embedded with FashionCLIP, so my likes and dislikes become a taste vector." |
| 1:30–1:55 | 추천 화면 | "Now real eBay tops, ranked by taste similarity and color harmony with my palette. Each card says why it was picked." |
| 1:55–2:25 | Try it on → 결과 슬라이더 → Buy now | "Try it on sends my photo and the actual product image to YouCam's AI Clothes Virtual Try-On. I can drag to compare — and Buy now takes me to the very same listing." |
| 2:25–2:35 | 로고/레포 URL | "ColorFit: personal color plus your taste, tried on, then bought. Built with YouCam AI." |

---

## SNS 공유 문구 (보너스 폼용, 선택)

```
I built ColorFit for the #YouCamAPI Hackathon by @PerfectCorp 🎨👕
A selfie → 12-type personal color with the evidence (YouCam AI Facial Color Tones Analyzer)
20 swipes → real eBay tops that match your taste and your colors
One click → virtual try-on (YouCam AI Clothes) → buy
Code: https://github.com/najunho04/youcam-project
#hackathon #AI #fashiontech #personalcolor
```
