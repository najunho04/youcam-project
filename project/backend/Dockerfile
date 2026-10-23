FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy HF_HOME=/app/.cache/huggingface
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache  # 이미지에 uv 캐시(torch 사본)를 남기지 않는다
COPY src ./src
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
