# Docker helpers

**Compose & Dockerfile:** repo root (`docker-compose.yml`, `Dockerfile`).

## Run (Hub image + Redis)

From repo root:

```bash
docker compose up -d
```

## Build & push (optional)

From anywhere:

```bash
./dockerization/build.sh
```

Uses repo root as context. Override: `IMAGE_NAME`, `VERSION`, `PLATFORMS`, `BUILDER` (e.g. `BUILDER=imusica-builder ./dockerization/build.sh`).
