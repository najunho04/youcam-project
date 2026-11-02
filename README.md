# ColorFit — Personal Color × Taste → Try It On → Buy It

> Find clothes that **suit you** and that **you actually like**, try them on your own photo, and buy them — in about three minutes.

Built for the **YouCam API Skin AI & eCommerce VTO Hackathon** (Perfect Corp).

- **Live demo:** <!-- TODO: replace with the Vercel production URL --> `https://<your-vercel-domain>`
- **Demo video:** <!-- TODO --> `https://youtu.be/<id>`
- **Test account for judges:** provided in the Devpost submission (Testing instructions). You can also sign up with any nickname — no email needed.

---

## The problem

Online fashion shopping asks two questions at once — *"does this suit me?"* and *"is this my style?"* — and gives you tools for neither. Personal color analysis lives in a beauty app, shopping lives in a store, and since you can't try anything on, you either hesitate or return it.

## What ColorFit does

| Step | What the user does | What happens |
|---|---|---|
| 1. Profile | Picks age group and gender | Selects the outfit pool for onboarding |
| 2. Personal color | Takes a guided selfie + upper-body photo | **YouCam Facial Color Tones Analyzer** returns skin, lip, eye, eyebrow and hair colors → our classifier decides one of **12 personal color types** and **shows the evidence** |
| 3. Swipe | Likes / dislikes ~20 outfit photos | Builds a taste vector with FashionCLIP embeddings |
| 4. Wardrobe (optional) | Uploads 3–4 outfit photos they love | Weighted more heavily in the taste vector |
| 5. Recommendations | Browses 6 real eBay tops | Ranked by taste similarity + color harmony, each with "why recommended" tags and a USD price |
| 6. Virtual try-on | Clicks **Try it on** | **YouCam AI Clothes (cloth-v4)** puts the actual product on the user's photo; before/after view and a **Buy on eBay** link |

**What makes it different**

- **Suitability and taste are scored separately**, then combined — and the reason is shown on every card.
- **Explainable personal color.** The result screen shows the five face colors YouCam detected, the scores on three axes (warmth, depth, clarity), skin lightness and contrast, and the sentence that led to the verdict — not just a label.
- **You try on the real product, not a look-alike.** Recommendation → virtual try-on → purchase link all point at the same eBay listing.

---

## YouCam APIs used

Both are called server-side through one client, [`shared/youcam`](project/backend/src/shared/youcam/__init__.py), as async tasks (`POST /s2s/v2.0/task/{feature}` → poll `GET .../{task_id}` until `success` / `error`). Images are passed by URL (short-lived S3 presigned URLs).

### 1. AI Facial Color Tones Analyzer — `skin-tone-analysis`

Used by the **personal color** feature, once per diagnosis.

We use **every color field** in the response — skin, lip, eye, eyebrow and hair hex values plus eye/hair color names — and classify in CIE Lab space ([`shared/color`](project/backend/src/shared/color/__init__.py)):

| Axis | Computed from | Meaning |
|---|---|---|
| Warmth | Skin hue (70%) + lip hue (30%) | yellow-leaning = warm, pink/red-leaning = cool |
| Depth | Skin L\* (60%) + contrast (40%), contrast = skin L\* − darkest of hair/eyebrow/eye | light (Spring/Summer) vs deep (Autumn/Winter) |
| Clarity | Skin chroma (60%) + lip chroma (40%) | bright vs soft |

- **Season** = warmth × depth → Spring / Summer / Autumn / Winter
- **Subtype** = the most pronounced axis within that season → 12 types (e.g. *Autumn Warm · Deep*, *Winter Cool · Bright*)
- Each type has an 8-color "best" palette; each season has a 6-color "avoid" palette.
- Face-detection failures (`error_no_face`, `error_face_*`, …) are surfaced to the user as a re-take guide.

### 2. AI Clothes Virtual Try-On — `cloth-v4`

Used by the **fitting** feature when the user clicks *Try it on*.

- Input: the user's upper-body photo (`src_file_url`) + the eBay product image (`ref_file_url`), `garment_category: "auto"`.
- `POST /api/fittings` starts the task and returns `202` immediately; a background worker polls YouCam to completion and stores the result in S3; the browser polls `GET /api/fittings/{id}`.
- Results are **cached per (user photo × product)**, so re-trying the same item costs no credits. Every started task is polled to completion (YouCam bills timed-out tasks too).

---

## How recommendations work

```
score = α · taste_similarity + (1 − α) · color_score        (α = 0.7)
```

- **Taste vector** `u = normalize(mean(liked) + w_c · mean(wardrobe) − β · mean(disliked))` over FashionCLIP image embeddings (L2-normalized, stored in pgvector).
- **Color score** — the product's dominant color vs. the user's 12-type palette, `max(0, 1 − ΔE/50)` with CIE76 ΔE to the nearest palette color; halved if it is close (ΔE < 15) to the season's avoid palette.
- **Dominant color** is extracted once at ingest time: estimate the background from border pixels, remove it, run K-means (k = 3) on the rest and keep the largest cluster's center.
- **Product data** — ~1,500 tops collected from the **eBay Browse API** (`item_summary/search`, EBAY_US), embedded with FashionCLIP, style-classified, and manually reviewed. Product images are not stored; only URLs.
- Fewer than 3 likes → fallback to color score only.

---

## Architecture

```
Browser ──HTTPS──▶ Vercel (React SPA)
                    └─ /api/* rewrite ──HTTPS──▶ AWS EC2 (Caddy → FastAPI + FashionCLIP)
                                                   ├─▶ Neon Postgres + pgvector
                                                   ├─▶ S3 (private bucket, presigned URLs)
                                                   └─▶ YouCam API (skin-tone-analysis, cloth-v4)

Offline batch (make ingest): eBay Browse API → background removal + K-means color → FashionCLIP → products
```

| Layer | Stack |
|---|---|
| Frontend | React 19, TypeScript, Vite, React Router, MediaPipe Tasks Vision (face / upper-body capture guide), Vitest |
| Backend | Python 3.13, FastAPI, SQLAlchemy, uv, pytest |
| ML | FashionCLIP (PyTorch CPU) for image embeddings, CIE Lab / K-means for color |
| Data | PostgreSQL + pgvector (Neon in production, Docker locally), S3 |
| Infra | Vercel (front), EC2 + Caddy + Docker (back), GitHub Actions CI, OIDC → ECR → SSM deploy |

### Code structure — vertical feature slices

Each feature is one vertical slice (request → backend → UI) that may not import another slice; shared code lives in `common/` (types only) and `shared/` (infrastructure). Import boundaries are enforced by import-linter and ESLint.

```
project/
  backend/src/
    common/          entities, DTOs, enums, error codes (types only)
    shared/          youcam · color · embedding · storage · database · security · config
    feature/
      auth/          sign-up / login (JWT)
      profile/       age group, gender
      personal_color/  YouCam face colors → 12-type verdict + evidence
      swipe/         onboarding cards and answers
      wardrobe/      optional outfit-photo upload
      recommendation/  taste × color ranking
      fitting/       YouCam cloth-v4 virtual try-on (async + cache)
      product_ingest/  eBay batch: collect → color → embed → store
    main.py
  front/src/
    feature/         same slices as the backend (pages, API calls, styles)
    shared/ common/ app/
  e2e/               Playwright end-to-end tests
project-all-docs/    PRD, API spec, ERD, feature graph (design docs, Korean)
```

### API

| Method | Path | Slice |
|---|---|---|
| POST | `/api/auth/signup`, `/api/auth/login` | auth |
| GET | `/api/users/me` | auth |
| PUT | `/api/users/me/profile` | profile |
| POST | `/api/personal-color` | personal_color |
| GET / POST | `/api/swipe/cards`, `/api/swipe/answers` | swipe |
| POST | `/api/wardrobe-photos` | wardrobe |
| GET | `/api/recommendations` | recommendation |
| POST / GET | `/api/fittings`, `/api/fittings/{id}` | fitting |

Full spec: [`project-all-docs/api.md`](project-all-docs/api.md) · ERD: [`project-all-docs/erd.md`](project-all-docs/erd.md)

---

## Running locally

**Requirements:** Docker, Python 3.13 + [uv](https://docs.astral.sh/uv/), Node.js 20+.

```bash
cd project
cp .env.example .env      # defaults run fully offline (YouCam mock, local storage)
make setup                # git hooks + backend/frontend/e2e dependencies
make dev                  # Postgres (Docker) + FastAPI :8000 + Vite :5173
```

Open http://localhost:5173.

By default `YOUCAM_MODE=mock` returns canned YouCam responses, so no API key or credits are needed. To call the real APIs:

| Variable | Value |
|---|---|
| `YOUCAM_MODE` | `live` |
| `YOUCAM_API_KEY` | your YouCam API key |
| `STORAGE_MODE` | `s3` — YouCam downloads input images by URL, so they must be publicly reachable (presigned S3 URLs) |
| `S3_BUCKET`, `AWS_REGION` | your bucket; AWS credentials are picked up from `~/.aws` or an instance role |

Loading products (optional, needs eBay Production keys in `.env`):

```bash
make ingest               # eBay → dominant color + FashionCLIP embedding → products
```

`EMBEDDING_MODE=fashion_clip` downloads the model (~600 MB) on first run; `fake` is available for quick UI work.

### Tests

```bash
make test                 # backend unit + contract tests (pytest) and frontend tests (Vitest)
make lint                 # cross-slice import checks
make test-e2e             # Playwright, with `make dev` running
```

---

## Privacy

- User photos are stored in a private S3 bucket (encrypted, public access blocked) and only exposed through short-lived presigned URLs.
- YouCam deletes processed input data within 24 hours.
- No eBay user data is stored — not even seller IDs.

## Development process

This project was built with a vertical-slice harness for AI-assisted solo development (one context card per slice, frozen contract tests, boundary checks in git hooks). See [`README-HARNESS.md`](README-HARNESS.md) (Korean).

## License

[MIT](LICENSE) © 2026 najunho04
