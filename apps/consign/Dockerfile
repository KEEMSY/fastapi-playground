# 두 서비스가 한 이미지를 쓰고 실행 명령만 다르다(k8s/apps.yaml 의 args).
# ponytail: 연습용 단순화. 실제 MSA 는 서비스마다 저장소·이미지·배포 주기가 따로다
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.24 /uv /bin/uv
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
COPY settlement ./settlement
ENV PATH="/srv/.venv/bin:$PATH"
# 컨테이너 하나에 프로세스 하나. 늘릴 때는 워커가 아니라 replica 로
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
