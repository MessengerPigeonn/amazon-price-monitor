# Amazon Price Monitor

A Python tool that monitors Amazon product prices using **PA-API 5.0** (real-time) and **Keepa** (historical data), automatically detects deals and price drops, and exposes everything through a REST API, CLI, and file exports.

## Features

- **Real-time price tracking** via Amazon Product Advertising API 5.0
- **Historical price data** via Keepa API (30/90/180-day averages, all-time low/high)
- **Automatic deal detection** with 5 strategies:
  - Price drops vs. previous checks and historical averages
  - Clearance/liquidation keyword matching + high savings %
  - Below-average pricing (vs. Keepa 30d/90d/180d averages)
  - All-time low detection
  - Margin opportunities with ROI estimation (after FBA + referral fees)
- **REST API** (FastAPI) with full CRUD, search, deal filtering, and export endpoints
- **CLI** for one-shot checks, searches, deal viewing, and exports
- **Scheduled monitoring** with configurable intervals (APScheduler)
- **SQLite persistence** for products, price history, deals, and alert dedup
- **JSON and CSV exports** on-demand or via API

## Prerequisites

- Python 3.9+
- [Amazon Associates account](https://affiliate-program.amazon.com/) with PA-API 5.0 access (access key, secret key, partner tag)
- [Keepa API key](https://keepa.com/#!api) (paid plan, ~$19/mo for sufficient tokens)

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
AMAZON__ACCESS_KEY=your_access_key_here
AMAZON__SECRET_KEY=your_secret_key_here
AMAZON__PARTNER_TAG=your_partner_tag-20
KEEPA__API_KEY=your_keepa_api_key_here
```

### 3. Run a price check

```bash
python main.py check B0BSHF7WHW
```

### 4. Start the API server

```bash
python main.py serve
```

### 5. Start with scheduled monitoring

```bash
python main.py run
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `python main.py check <ASIN> [ASIN...]` | One-shot price check for specific ASINs |
| `python main.py search "<keywords>"` | Search Amazon for products |
| `python main.py deals` | Show active deals (supports `--deal-type` and `--min-roi` filters) |
| `python main.py export` | Export data as JSON (supports `--format csv` and `--save`) |
| `python main.py serve` | Start the FastAPI server |
| `python main.py run` | Start scheduler + FastAPI server |

## API Endpoints

All endpoints are available at `http://localhost:8000` by default.

### Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/products` | List monitored products |
| `POST` | `/api/v1/products` | Add an ASIN to monitoring |
| `POST` | `/api/v1/products/search` | Search Amazon via PA-API |
| `GET` | `/api/v1/products/{asin}` | Get a single product |
| `DELETE` | `/api/v1/products/{asin}` | Deactivate a product |

### Prices

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/prices/{asin}/history` | Price history with min/max/avg stats |
| `POST` | `/api/v1/prices/profit-estimate` | Calculate resale margins after fees |

### Deals

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/deals` | Active deals (filterable by `deal_type`, `min_roi`) |
| `POST` | `/api/v1/deals/scan` | Trigger an on-demand scan of all monitored products |
| `POST` | `/api/v1/deals/{id}/dismiss` | Dismiss a deal |

### Exports & Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/exports/json` | Download all data as JSON |
| `GET` | `/api/v1/exports/csv` | Download all data as CSV |
| `GET` | `/health` | System status check |

### Example requests

```bash
# Add a product to monitoring
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"asin": "B0BSHF7WHW", "label": "My Product", "target_buy_price": 25.00}'

# Calculate profit estimate
curl -X POST http://localhost:8000/api/v1/prices/profit-estimate \
  -H "Content-Type: application/json" \
  -d '{"sale_price": 50.00, "cost": 20.00}'

# Get active deals with minimum 30% ROI
curl "http://localhost:8000/api/v1/deals?min_roi=30"

# Trigger a deal scan
curl -X POST http://localhost:8000/api/v1/deals/scan
```

## Configuration

Settings are loaded from `config/config.yaml` and can be overridden with environment variables in `.env` (using `__` as the nested delimiter).

| Setting | Default | Description |
|---------|---------|-------------|
| `monitoring.check_interval_minutes` | `60` | How often the scheduler checks prices |
| `monitoring.price_drop_threshold_percent` | `10.0` | Minimum % drop to trigger a price drop deal |
| `monitoring.min_savings_percent` | `20.0` | Minimum savings % to flag as clearance |
| `monitoring.target_roi_percent` | `30.0` | Minimum ROI to flag a margin opportunity |
| `monitoring.fba_fee_percent` | `15.0` | Estimated FBA fee for profit calculations |
| `monitoring.referral_fee_percent` | `15.0` | Estimated referral fee for profit calculations |
| `server.host` | `0.0.0.0` | API server bind address |
| `server.port` | `8000` | API server port |

### Watchlist

Add ASINs or keyword searches to `config/watchlist.yaml` for batch monitoring:

```yaml
watchlist:
  - asin: "B0BSHF7WHW"
    label: "Example Product"
    target_buy_price: 25.00
  - keywords: "wireless earbuds clearance"
    label: "Earbud deals"
```

## Project Structure

```
amazon-price-monitor/
├── config/          # Settings (YAML + .env), watchlist
├── clients/         # PA-API 5.0 and Keepa API wrappers with rate limiting
├── db/              # SQLAlchemy models, engine, and repository layer
├── services/        # Business logic: orchestration, deal detection, alerts, exports, scheduler
├── api/             # FastAPI app, schemas, dependencies, route modules
├── cli/             # Typer CLI
├── data/            # Runtime data: SQLite DB, exports (gitignored)
├── logs/            # Log files (gitignored)
└── main.py          # Entry point
```

## Database

SQLite is used by default (stored at `data/prices.db`). The schema includes four tables:

- **products** -- Monitored ASINs with metadata and tracking preferences
- **price_records** -- Price snapshots with PA-API and Keepa data per check
- **deals** -- Detected deals with type, prices, drop %, and profit estimates
- **alerts** -- Deduplication log for deal notifications

## License

This project is for personal use. Amazon product data is subject to the [Amazon Associates Program Operating Agreement](https://affiliate-program.amazon.com/help/operating/agreement) and Keepa's terms of service.
