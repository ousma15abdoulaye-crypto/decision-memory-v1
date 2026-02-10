# Resolvers Guide — Couche B

## Overview
Resolvers implement the canonical matching pattern for entities in Couche B.

## Resolver Pattern
Constitution DMS V2.1 §5.2

Each resolver follows this pattern:
1. **Exact canonical match** - Check if entity exists in master table
2. **Exact alias match** - Check if entity exists in aliases table
3. **Fuzzy match** - Use fuzzywuzzy for similarity matching
4. **Propose new** - Create proposed entity for admin validation

## Resolvers

### `resolve_vendor(conn, vendor_name: str, threshold: int = 85) -> str`
Resolves vendor name to canonical vendor_id.

**Parameters:**
- `conn`: Database connection
- `vendor_name`: Vendor name to resolve
- `threshold`: Fuzzy matching threshold (default 85%)

**Returns:** vendor_id (string)

**Algorithm:**
1. Normalize input text
2. Check exact match in vendors table
3. Check exact match in vendor_aliases table
4. Fuzzy match against canonical names (threshold 85%)
5. If no match, create proposed vendor

### `resolve_item(conn, item_description: str, threshold: int = 85) -> str`
Resolves item description to canonical item_id.

**Parameters:**
- `conn`: Database connection
- `item_description`: Item description to resolve
- `threshold`: Fuzzy matching threshold (default 85%)

**Returns:** item_id (string)

### `resolve_unit(conn, unit_text: str) -> str`
Resolves unit text to canonical unit_id.

**Parameters:**
- `conn`: Database connection
- `unit_text`: Unit text to resolve

**Returns:** unit_id (string)

**Note:** Units use EXACT matching only (no fuzzy matching)

### `resolve_geo(conn, location_name: str, threshold: int = 90) -> str`
Resolves location name to canonical geo_id.

**Parameters:**
- `conn`: Database connection
- `location_name`: Location name to resolve
- `threshold`: Fuzzy matching threshold (default 90%, stricter)

**Returns:** geo_id (string)

**Note:** Geo uses stricter threshold (90%) due to importance of location accuracy

## Helper Functions

### `normalize_text(text: str) -> str`
Normalizes text for matching:
- Lowercase
- Remove accents
- Trim whitespace
- Remove special characters

### `generate_ulid() -> str`
Generates sortable unique ID (timestamp + random)

## TODO
- Session 2.1: Implement all resolvers
- Add caching layer
- Add performance metrics
- Add logging
