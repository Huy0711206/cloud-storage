# Native Mailpit source and both upstream lockfiles are pinned to v1.32.0.
FROM node:24-alpine AS ui
WORKDIR /app
COPY upstream/package.json upstream/package-lock.json ./
RUN npm ci
COPY upstream/ ./
RUN npm run package && npm test

FROM golang:1.27.3-alpine AS build
WORKDIR /app
COPY upstream/go.mod upstream/go.sum ./
RUN go mod download
COPY upstream/ ./
COPY --from=ui /app/server/ui ./server/ui
ARG UI_VERSION=v1.32.0-cloudbox.3
RUN --mount=type=cache,target=/root/.cache/go-build CGO_ENABLED=0 go build -trimpath -ldflags "-s -w -X github.com/axllent/mailpit/config.Version=${UI_VERSION}" -o /mailpit

# Reuse the existing vendor runtime (no automatic Mailpit upgrade).
FROM axllent/mailpit@sha256:0790692be935ea4420d085694f7985b1f692ca6a8771ab0e0bd8ba75ac180498
COPY --from=build /mailpit /mailpit
