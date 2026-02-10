# API Couche B — Market Intelligence

## Overview
Couche B provides the Market Intelligence Layer as defined in Constitution DMS V2.1.

## Endpoints

### Catalog Search (Autocomplete)

#### GET `/api/catalog/vendors/search`
Search vendors (canonical + aliases)
- **Query params**: `q` (string, min 1 char)
- **Returns**: List of matching vendors

#### GET `/api/catalog/items/search`
Search items
- **Query params**: `q` (string, min 1 char)
- **Returns**: List of matching items

#### GET `/api/catalog/units/search`
Search units
- **Query params**: `q` (string, min 1 char)
- **Returns**: List of matching units

#### GET `/api/catalog/geo/search`
Search geo zones
- **Query params**: `q` (string, min 1 char)
- **Returns**: List of matching geo zones

### Market Survey

#### POST `/api/market-survey`
Create market survey with propose-only pattern
- **Body**: Survey data
- **Returns**: Survey ID

#### GET `/api/market-survey/validation-queue`
Get pending proposals for admin validation
- **Returns**: List of pending signals

#### PATCH `/api/market-survey/{signal_id}/validate`
Validate or reject market signal (admin)
- **Path params**: `signal_id` (string)
- **Body**: `action` (approve/reject)
- **Returns**: Updated signal status

### Market Intelligence

#### GET `/api/market-intelligence/search`
Search market signals with filters
- **Query params**: 
  - `item` (optional)
  - `geo` (optional)
  - `vendor` (optional)
  - `date_from` (optional)
  - `date_to` (optional)
- **Returns**: List of matching signals

#### GET `/api/market-intelligence/stats`
Get price statistics (avg, min, max, median)
- **Query params**: 
  - `item_id` (required)
  - `geo_id` (optional)
- **Returns**: Statistics object

## TODO
- Session 3.1: Implement all endpoints
- Add authentication/authorization
- Add rate limiting
- Add response schemas
