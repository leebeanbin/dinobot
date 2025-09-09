# DinoBot 도커 이미지
# Python 3.11 기반의 최적화된 프로덕션 이미지

FROM python:3.11-slim as builder

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Poetry 설치
RUN pip install poetry==1.7.1

# Poetry 설정 (가상환경 생성 안함, 의존성을 전역에 설치)
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=0 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# 작업 디렉토리 설정
WORKDIR /app

# Poetry 파일들 복사
COPY pyproject.toml poetry.lock ./

# 의존성 설치 (개발 의존성 제외)
RUN poetry install --only=main && rm -rf $POETRY_CACHE_DIR

# 프로덕션 스테이지
FROM python:3.11-slim as runtime

# 시스템 패키지 업데이트 (런타임에 필요한 최소한만)
RUN apt-get update && apt-get install -y \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 애플리케이션 사용자 생성 (보안 강화)
RUN groupadd -r dinobot && useradd -r -g dinobot dinobot

# 작업 디렉토리 설정
WORKDIR /app

# Python 패키지들을 전역에 설치했으므로 PATH 설정만 필요
ENV PATH="/usr/local/bin:$PATH"

# 애플리케이션 코드 복사
COPY . ./

# 로그 디렉토리 생성
RUN mkdir -p logs && chown -R dinobot:dinobot /app

# 사용자 권한으로 실행
USER dinobot

# 포트 노출 (환경변수로 설정 가능)
EXPOSE 8888

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8888}/health || exit 1

# 애플리케이션 실행
CMD ["python", "run.py"]
