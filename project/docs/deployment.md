# 배포 가이드 (해커톤 규모)

## 구성

```
브라우저 ──HTTPS──> Vercel (front 정적 SPA)
                     └─ /api/* rewrite ──HTTPS──> EC2 t3.small (Caddy → FastAPI + FashionCLIP)
                                                    ├─> Neon (Postgres + pgvector)
                                                    ├─> S3 (사진, IAM 롤)
                                                    └─> YouCam API
```

| 영역 | 서비스 | 이유 |
|---|---|---|
| 프론트 | Vercel (Hobby, 무료) | Vite 정적 빌드라 설정 거의 없음 |
| 백엔드 | EC2 t3.small (2GB) | FashionCLIP(torch) 상주에 메모리 필요 |
| DB | Neon (무료) | pgvector 지원, EC2 메모리 절약. 현재 데이터 약 21MB |

- 프론트는 지금처럼 상대경로 `/api/...` 를 호출한다. Vercel 이 EC2 로 넘겨주므로 CORS·프론트 코드 변경이 필요 없다.
- 모든 리소스는 서울 리전(`ap-northeast-2`)에 둔다.

---

## 1. Neon (DB)

1. neon.tech 에서 프로젝트 생성. 리전은 서울(없으면 가장 가까운 곳)을 고른다.
2. 접속 문자열에서 **pooler 가 아닌 direct** 주소를 복사해 SQLAlchemy 형식으로 바꾼다.
   ```
   DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>/<db>?sslmode=require
   ```
3. 스키마는 따로 만들 필요 없다. 백엔드가 기동할 때 `CREATE EXTENSION vector` 와 `create_all` 을 실행한다.
4. (선택) 로컬에 적재한 상품을 옮기면 `make ingest` 를 다시 돌리지 않아도 된다.
   ```bash
   docker compose exec -T db pg_dump -U colorfit --no-owner --no-acl colorfit > dump.sql
   psql "<Neon direct 접속 문자열>" -f dump.sql
   ```

## 2. EC2 (백엔드) — 구축 완료

| 항목 | 값 |
|---|---|
| 인스턴스 | `i-0f2714f3bf31fbd5b` (`colorfit-backend`), t3.small, Ubuntu 24.04, gp3 10GB, 서울 |
| Elastic IP / 호스트 | `3.35.152.198` / `3-35-152-198.sslip.io` (Caddy 가 Let's Encrypt 인증서 자동 발급) |
| 보안 그룹 | `colorfit-backend` (`sg-0a692713d3dc81853`): 80·443 전체, 22 는 관리자 IP 만 |
| IAM 롤 | `colorfit-ec2-role`: S3 버킷 객체 읽기·쓰기·삭제 + ECR `colorfit-backend` pull + `AmazonSSMManagedInstanceCore` |
| SSH | `ssh -i ~/.ssh/colorfit-ec2.pem ubuntu@3.35.152.198` |
| 스왑 | 1GB. RAM(2GB)이 꽉 차면 디스크를 비상 메모리로 써서 OOM 강제 종료를 막는 보험 |

- 서버 경로: `/home/ubuntu/colorfit` (`backend/`, `docker-compose.yml`, `Caddyfile`, `.env`)
- 기동은 CD 가 한다 (ECR 이미지 pull → `docker compose --profile prod up -d --no-build backend caddy`). 로컬 DB 컨테이너(`db`)는 띄우지 않는다.
- 디스크 10GB 에 맞추려고 두 가지를 했다.
  - Docker 를 overlay2 저장소로 바꿨다(`/etc/docker/daemon.json` 의 `containerd-snapshotter: false`). 기본값인 containerd 저장소는 이미지를 두 벌 저장한다.
  - `uv sync --no-cache` 로 빌드해서 백엔드 이미지가 약 1.4GB 다. 빌드는 GitHub Actions 에서 하므로 EC2 에 빌드 캐시가 쌓이지 않는다.
- 공간이 모자라면 `docker builder prune -af && docker image prune -af` 를 실행한다.

### `.env` (EC2, 레포에 없음)

| 키 | 값 |
|---|---|
| `DATABASE_URL` | Neon direct 주소 (싱가포르, `?sslmode=require`) |
| `JWT_SECRET` | 새로 생성한 긴 랜덤 문자열 |
| `STORAGE_MODE` / `S3_BUCKET` / `AWS_REGION` | `s3` / `youcamapi-hackathon-1013` / `ap-northeast-2` |
| `YOUCAM_MODE` / `YOUCAM_API_KEY` | `live` / 발급 키 |
| `EMBEDDING_MODE` | `fashion_clip` |
| `PUBLIC_BASE_URL` / `API_HOST` | `https://3-35-152-198.sslip.io` / `3-35-152-198.sslip.io` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | 넣지 않는다 (IAM 롤 사용) |

## 3. Vercel (프론트) — 구축 완료

- 프로젝트 `colorfit`: GitHub `najunho04/youcam-project` 의 `main` 에 연동, Root Directory `project/front`, Vite.
- `main` 에 푸시하면 자동으로 배포된다. 환경변수는 없다.
- `project/front/vercel.json` 이 `/api/*` 를 EC2 로 넘기고, 나머지 경로는 `index.html` 로 보낸다(SPA).

## 4. CI / CD (`.github/workflows`)

| 워크플로 | 시점 | 내용 |
|---|---|---|
| `ci.yml` | push(main), PR | backend: pgvector 서비스 컨테이너 + import-linter + pytest / front: eslint + vitest + build |
| `deploy-backend.yml` | main 의 CI 통과 후, 수동 실행 | GitHub OIDC 로 AWS 임시 권한을 받는다 → Actions 러너에서 이미지를 빌드해 ECR 에 push 한다 (태그 = 커밋 SHA) → SSM Run Command 로 EC2 가 pull 해서 재기동한다 (인바운드 SSH 불필요) |

`deploy-backend.yml` 이 쓰는 저장소 Variables:

| 이름 | 값 |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::844669501605:role/colorfit-github-deploy` (이 레포 main 만 허용. ECR `colorfit-backend` push + 이 인스턴스에 SSM SendCommand) |
| `EC2_INSTANCE_ID` | `i-0f2714f3bf31fbd5b` |
| `ECR_REPOSITORY` | `colorfit-backend` (최근 이미지 5개만 유지) |

- OIDC 신뢰 조건의 `sub` 는 GitHub 의 immutable subject 형식이다: `repo:najunho04@239599953/youcam-project@1420341680:ref:refs/heads/main` (레포 이름만 쓰면 AssumeRole 이 거부된다).
- 롤백: Actions 에서 이전 커밋으로 `Deploy backend` 를 다시 실행하거나, EC2 에서 `BACKEND_IMAGE=<ECR 주소>:<이전 SHA> docker compose --profile prod up -d --no-build backend` 를 실행한다.

## 6. AWS 자원 정리 (해커톤 종료 후)

모든 자원에 태그 `Project=youcam-project` 가 붙어 있다. IAM 은 리전 밖이라 태그 검색에 안 나오니 이름(`colorfit-*`)으로 지운다.

| 자원 | 이름 / ID |
|---|---|
| EC2 인스턴스 (+ EBS, ENI) | `i-0f2714f3bf31fbd5b` |
| Elastic IP | `eipalloc-095b89bc229b39583` (인스턴스 삭제 후 반드시 release. 남겨 두면 과금) |
| 보안 그룹 | `sg-0a692713d3dc81853` |
| 키 페어 | `colorfit-ec2` |
| ECR | `colorfit-backend` |
| IAM 롤 / 인스턴스 프로파일 | `colorfit-ec2-role`, `colorfit-github-deploy` / `colorfit-ec2-profile` |
| S3 버킷 | `youcamapi-hackathon-1013` (사진 데이터 포함) |

GitHub OIDC 공급자(`token.actions.githubusercontent.com`)는 다른 프로젝트와 같이 쓰므로 지우지 않는다.

```bash
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=youcam-project --query 'ResourceTagMappingList[].ResourceARN'
```

## 5. 배포 후 확인

- [ ] 회원가입, 로그인
- [ ] 사진 업로드 (최대 10MB × 4장)가 Vercel rewrite 를 통과하는지
- [ ] 퍼스널컬러 분석이 시간 초과 없이 끝나는지 (YouCam 폴링은 최대 165초)
- [ ] 추천 목록이 뜨는지 (Neon + 임베딩)

> 업로드나 분석이 Vercel rewrite 에서 막히면 프론트가 EC2 HTTPS 주소를 직접 호출하도록 바꾼다. 이 경우 백엔드 CORS 설정(`main.py`)과 프론트 API 베이스 URL 이 필요하다. 둘 다 경계 파일이라 별도 승인이 필요하다.

## 예상 비용 (월)

| 항목 | 비용 |
|---|---|
| EC2 t3.small (상시) | 약 $19 |
| EBS 10GB | 약 $1 |
| Elastic IP (퍼블릭 IPv4) | 약 $3.6 |
| Vercel Hobby, Neon Free | $0 |
| S3, ECR (이미지 5개) | 거의 $0 |

해커톤이 끝나면 EC2 를 중지(stop)한다. 이때 디스크와 IP 요금만 나온다.
