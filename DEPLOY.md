# Deployment Guide

## Prerequisites

- **Local**: Docker installed
- **Remote**: Docker + Docker Compose installed, SSH access (key-based recommended)
- **Config**: `.env` file with your Bybit API credentials

## Quick Start

```sh
# 1. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 2. Build and test locally
./scripts/docker-build.sh

# 3. Deploy to remote server
./scripts/deploy.sh user@your-server
```

## Configuration

All configuration is via environment variables in `.env`:

| Variable | Default | Description |
|---|---|---|
| `BYBIT_API_KEY` | (required) | Bybit API key |
| `BYBIT_API_SECRET` | (required) | Bybit API secret |
| `BYBIT_TESTNET` | `true` | Use testnet (`true`) or mainnet (`false`) |
| `TRADING_MODEL` | `glft` | Model: `glft` or `avellaneda_stoikov` |
| `FEE_TIER` | `regular` | Fee tier: `regular` or `market_maker` |
| `KAPPA_MODE` | `live` | Kappa source: `live` or `static` |
| `INITIAL_CAPITAL` | `1000` | Starting capital in USD |
| `ORDER_SIZE` | `0.003` | Order size in BTC |
| `QUOTE_INTERVAL` | `5.0` | Seconds between quote updates |

## Scripts

| Script | Description |
|---|---|
| `scripts/docker-build.sh` | Build image + run tests in container |
| `scripts/deploy.sh user@host` | Full deploy to remote server |
| `scripts/docker-logs.sh [user@host]` | Tail trader logs (local or remote) |

## What `deploy.sh` Does

1. Builds Docker image locally
2. Saves image to a tarball and SCPs it to the remote host
3. Loads the image on the remote host
4. Copies `docker-compose.yml` and `.env` to `/opt/algo-trader/`
5. Runs `docker compose up -d` on the remote host
6. Validates the container is running

## Troubleshooting

**Container won't start**
```sh
./scripts/docker-logs.sh user@host    # Check logs
ssh user@host "cd /opt/algo-trader && docker compose ps"
```

**Permission denied on remote**
```sh
# Ensure your user is in the docker group
ssh user@host "sudo usermod -aG docker \$USER"
```

**Image transfer is slow**
The image is ~200-400 MB compressed. Consider building directly on the remote host if bandwidth is limited.

**Tests fail in container**
```sh
# Run tests locally first
python -m pytest tests/ features/ -v
# Then try in container
docker run --rm --entrypoint python algo-trader -m pytest tests/ -v
```
