# DMS Firewall Contracts

## Principle

- **Couche A → Couche B**: Write ONLY via outbox + POST /api/market-signals
- **Couche B → Couche A**: READ-ONLY (catalog search + stats)
- **Direct DB cross-access**: FORBIDDEN

## Allowed Market Signal Fields (A → B)

```json
{
  "item_name": "string (required)",
  "vendor_name": "string (required)",
  "unit_price": "float (required)",
  "currency": "string (default: XOF)",
  "geo_name": "string (optional)",
  "unit_code": "string (optional)",
  "quantity": "float (optional)",
  "signal_date": "string ISO date (optional)",
  "source": "string (optional)",
  "case_reference": "string (optional)"
}
```

Any field outside this whitelist → **422 Unprocessable Entity**

## Couche B Read Endpoints (available to A)

| Endpoint | Method | Description |
|---|---|---|
| `/api/catalog/vendors/search?q=` | GET | Search vendors |
| `/api/catalog/items/search?q=` | GET | Search items |
| `/api/catalog/units/search?q=` | GET | Search units |
| `/api/catalog/geo/search?q=` | GET | Search geography |
| `/api/market-intelligence/stats?item_id=&geo_id=` | GET | Price statistics |

## Blocked Operations on Market Signals

- `UPDATE market_signals` → FORBIDDEN
- `DELETE market_signals` → FORBIDDEN
- Corrections: insert new signal with `superseded_by` pointing to original

## Enforcement

1. **Pydantic model** with `extra = "forbid"` on MarketSignalPayload
2. **Firewall middleware** blocks cross-layer HTTP calls
3. **Role check**: POST /api/market-signals requires `admin` role
4. **Outbox pattern**: signals only emitted after committee validation
