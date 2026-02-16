###############################################################################
# Stage 1: Builder — compile TA-Lib C library and install Python dependencies
###############################################################################
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        wget \
    && rm -rf /var/lib/apt/lists/*

# Build TA-Lib C library from source
ARG TALIB_VERSION=0.6.4
RUN wget -q https://github.com/TA-Lib/ta-lib/releases/download/v${TALIB_VERSION}/ta-lib-${TALIB_VERSION}-src.tar.gz \
    && tar xzf ta-lib-${TALIB_VERSION}-src.tar.gz \
    && cd ta-lib-${TALIB_VERSION} \
    && ./configure --prefix=/usr/local \
    && make -j"$(nproc)" \
    && make install \
    && cd .. \
    && rm -rf ta-lib-${TALIB_VERSION} ta-lib-${TALIB_VERSION}-src.tar.gz

# Install Python dependencies into a virtual-env so we can copy it cleanly
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

###############################################################################
# Stage 2: Runtime — lean image with only what we need
###############################################################################
FROM python:3.11-slim AS runtime

# Copy TA-Lib shared libraries
COPY --from=builder /usr/local/lib/libta_lib* /usr/local/lib/
RUN ldconfig

# Copy pre-built virtual-env
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN groupadd --gid 1000 trader \
    && useradd --uid 1000 --gid trader --create-home trader

WORKDIR /app

# Copy project source code
COPY strategies/ strategies/
COPY scripts/ scripts/
COPY config/ config/

# Ensure the non-root user owns everything
RUN chown -R trader:trader /app

USER trader

# Healthcheck: verify the main Python process is alive
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD pgrep -f "python scripts/run_paper_trader.py" > /dev/null || exit 1

STOPSIGNAL SIGTERM

ENTRYPOINT ["python", "scripts/run_paper_trader.py"]
CMD []
