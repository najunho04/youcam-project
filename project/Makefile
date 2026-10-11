# 실행 명령 고정. 세션은 이 타겟만 사용한다. (쓰기 X)
# 스택: backend = Python 3.13 · FastAPI · uv · pytest / front = React · Vite · Vitest / e2e = Playwright
# DB(PostgreSQL + pgvector)는 docker compose 로 띄운다. 환경변수는 project/.env (예시: .env.example)

.PHONY: setup dev test test-slice test-e2e lint ingest up down

BACKEND_RUN = cd backend && PYTHONPATH=src uv run
# 스캐폴딩(단계 0) 전에는 해당 쪽을 건너뛴다. 스캐폴딩 후에는 항상 실행된다.
HAS_BACKEND = [ -f backend/pyproject.toml ]
HAS_FRONT   = [ -f front/package.json ]

setup:            ## clone 직후 1회. 훅 연결 + 의존성 설치
	git config core.hooksPath "$$(git rev-parse --show-prefix).githooks"
	chmod +x .githooks/*
	@if $(HAS_BACKEND); then (cd backend && uv sync); fi
	@if $(HAS_FRONT); then (cd front && npm install) && (cd e2e && npm install && npx playwright install chromium); fi

dev:              ## DB 컨테이너 + 백엔드(:8000, reload) + 프론트(:5173, /api 프록시)
	docker compose up -d db
	@trap 'kill 0' INT TERM; \
	($(BACKEND_RUN) uvicorn main:app --app-dir src --reload --port 8000) & \
	(cd front && npm run dev) & \
	wait

DB_UP = docker compose up -d --wait db >/dev/null

test:             ## 단위 + 계약 테스트 전체 (백엔드 테스트는 DB 컨테이너 사용)
	@if $(HAS_BACKEND); then $(DB_UP) && ($(BACKEND_RUN) pytest test); fi
	@if $(HAS_FRONT); then (cd front && npx vitest run --passWithNoTests); fi

test-slice:       ## 자기 슬라이스 범위만. SLICE=personal_color make test-slice
	@test -n "$(SLICE)" || { echo "SLICE 를 지정하세요 (예: SLICE=auth make test-slice)"; exit 1; }
	@set -e; \
	backend_dirs=$$(for d in test/unit/$(SLICE) test/contract/$(SLICE); do [ -d backend/$$d ] && echo $$d; done; true); \
	if [ -n "$$backend_dirs" ]; then $(DB_UP) && (cd backend && uv run pytest $$backend_dirs); fi; \
	front_dirs=$$(for d in test/unit/$(SLICE) test/contract/$(SLICE) src/feature/$(SLICE); do [ -d front/$$d ] && echo $$d; done; true); \
	if [ -n "$$front_dirs" ]; then (cd front && npx vitest run --passWithNoTests $$front_dirs); fi; \
	if [ -z "$$backend_dirs$$front_dirs" ]; then echo "SLICE=$(SLICE) 에 해당하는 테스트 폴더가 없습니다"; exit 1; fi

test-e2e:         ## 슬라이스 완료 시에만. make dev 가 떠 있어야 한다
	cd e2e && npx playwright test

lint:             ## 슬라이스 간 import 차단 검사 (backend: import-linter / front: eslint no-restricted-imports)
	@if $(HAS_BACKEND); then ($(BACKEND_RUN) lint-imports); else echo "[lint] backend 미스캐폴딩 — 건너뜀"; fi
	@if $(HAS_FRONT); then (cd front && npx eslint src); else echo "[lint] front 미스캐폴딩 — 건너뜀"; fi

# ---- 아래는 사람용 (세션은 사용하지 않는다) ----

ingest:           ## 상품 수집 배치 (네이버 쇼핑 → 임베딩 → products upsert). 하루 1회
	docker compose up -d db
	$(BACKEND_RUN) python -m feature.product_ingest

up:               ## EC2 배포: 전체 컨테이너 빌드·기동 (db, backend, web)
	docker compose --profile prod up -d --build

down:
	docker compose --profile prod down
