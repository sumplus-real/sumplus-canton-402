# Canton 402 live demo: real Daml/Canton ledger + JSON API + x402 gateway,
# all in one container. Boots a Canton sandbox, seeds the world, serves the
# dashboard. Built for Railway (binds the gateway to $PORT).
FROM eclipse-temurin:17-jdk-jammy

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates python3 netcat-openbsd \
 && rm -rf /var/lib/apt/lists/*

# Daml SDK 2.10.4 (Linux). Cached as its own layer so app changes don't refetch.
RUN curl -fsSL -o /tmp/daml.tar.gz \
      "https://github.com/digital-asset/daml/releases/download/v2.10.4/daml-sdk-2.10.4-linux.tar.gz" \
 && mkdir -p /tmp/damlsdk \
 && tar xzf /tmp/daml.tar.gz -C /tmp/damlsdk \
 && /tmp/damlsdk/sdk-2.10.4/install.sh \
 && rm -rf /tmp/daml.tar.gz /tmp/damlsdk
ENV PATH="/root/.daml/bin:${PATH}"

WORKDIR /app

# Build the DAR (depends only on the Daml sources, so it caches well).
COPY daml.yaml ./
COPY daml ./daml
RUN daml build

# App code + entrypoint.
COPY gateway ./gateway
COPY deploy/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# Canton heap. Keep modest so the container fits a small instance.
ENV CANTON_JVM_OPTS="-Xmx1536m"
ENV CANTON402_GATEWAY_PORT=8402
EXPOSE 8402

CMD ["./entrypoint.sh"]
