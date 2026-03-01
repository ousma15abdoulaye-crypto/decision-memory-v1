"""
Tests endpoints GET /geo/* — M3.
Prouve que tous les endpoints retournent 200 et des données non vides.

Périmètre M3 :
  GET /geo/countries
  GET /geo/countries/{iso2}/regions
  GET /geo/regions/{region_id}/cercles
  GET /geo/cercles/{cercle_id}/communes
  GET /geo/communes/search
  GET /geo/zones

Hors périmètre M3 (pas d'API zombie) :
  Communes par zone — reporté au jalon de chargement des zones organisationnelles
"""

from __future__ import annotations


def test_get_countries_200(test_client, geo_seed):
    """GET /geo/countries doit retourner 200 et au moins 1 pays."""
    resp = test_client.get("/geo/countries")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_countries_mali_present(test_client, geo_seed):
    """Le Mali doit apparaître dans GET /geo/countries."""
    resp = test_client.get("/geo/countries")
    assert resp.status_code == 200
    iso2s = [c["iso2"] for c in resp.json()]
    assert "ML" in iso2s


def test_get_regions_by_country_200(test_client, geo_seed):
    """GET /geo/countries/ML/regions doit retourner 200 et 11 régions."""
    resp = test_client.get("/geo/countries/ML/regions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 11


def test_get_regions_unknown_country_404(test_client, geo_seed):
    """GET /geo/countries/XX/regions doit retourner 404."""
    resp = test_client.get("/geo/countries/XX/regions")
    assert resp.status_code == 404


def test_get_cercles_by_region_200(test_client, geo_seed, db_conn):
    """GET /geo/regions/{id}/cercles doit retourner 200 et 8 cercles pour Mopti."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM geo_regions WHERE code = 'ML-5'")
        row = cur.fetchone()
    region_id = str(row["id"])

    resp = test_client.get(f"/geo/regions/{region_id}/cercles")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8


def test_get_communes_by_cercle_200(test_client, geo_seed, db_conn):
    """GET /geo/cercles/{id}/communes doit retourner 200 et au moins 1 commune."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT id FROM geo_cercles WHERE code = 'MOP-MOP'")
        row = cur.fetchone()
    cercle_id = str(row["id"])

    resp = test_client.get(f"/geo/cercles/{cercle_id}/communes")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


def test_search_communes_200(test_client, geo_seed):
    """GET /geo/communes/search?q=Mopti doit retourner 200 et des résultats."""
    resp = test_client.get("/geo/communes/search?q=Mopti")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_search_communes_too_short_422(test_client, geo_seed):
    """GET /geo/communes/search?q=M (1 char) doit retourner 422."""
    resp = test_client.get("/geo/communes/search?q=M")
    assert resp.status_code == 422


def test_search_communes_no_q_422(test_client, geo_seed):
    """GET /geo/communes/search sans q doit retourner 422."""
    resp = test_client.get("/geo/communes/search")
    assert resp.status_code == 422


def test_get_zones_200(test_client, geo_seed):
    """GET /geo/zones doit retourner 200 (liste vide en M3 — table non seedée)."""
    resp = test_client.get("/geo/zones")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Table existe, mais non seedée en M3
    assert len(data) == 0
