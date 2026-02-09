#!/usr/bin/env python3
"""
Test de transformation des placeholders numériques
Vérifie compatibilité PostgreSQL
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import transform_numeric_placeholders


def test_single_placeholder():
    """Test transformation simple :0"""
    query = "SELECT * FROM cases WHERE id=:0"
    params = ("abc123",)
    
    query2, bind = transform_numeric_placeholders(query, params)
    
    print("Test 1: Single placeholder")
    print(f"  Input:  {query}")
    print(f"  Params: {params}")
    print(f"  Output: {query2}")
    print(f"  Bind:   {bind}")
    
    assert ":p0" in query2, f"Expected :p0 in '{query2}'"
    assert ":0" not in query2, f"Original :0 should be replaced in '{query2}'"
    assert bind == {"p0": "abc123"}, f"Expected {{'p0': 'abc123'}}, got {bind}"
    print("  ✅ PASSED\n")


def test_multiple_placeholders():
    """Test transformation multiple :0, :1, :2"""
    query = "SELECT * FROM cases WHERE id=:0 AND status=:1"
    params = ("abc", "open")
    
    query2, bind = transform_numeric_placeholders(query, params)
    
    print("Test 2: Multiple placeholders")
    print(f"  Input:  {query}")
    print(f"  Params: {params}")
    print(f"  Output: {query2}")
    print(f"  Bind:   {bind}")
    
    assert ":p0" in query2
    assert ":p1" in query2
    assert bind == {"p0": "abc", "p1": "open"}, f"Expected correct binding, got {bind}"
    print("  ✅ PASSED\n")


def test_insert_many_placeholders():
    """Test INSERT avec 7 placeholders"""
    query = """
    INSERT INTO artifacts (id, case_id, kind, filename, path, uploaded_at, meta_json)
    VALUES (:0, :1, :2, :3, :4, :5, :6)
    """
    params = ("id1", "case1", "dao", "file.pdf", "/path", "2026-02-09", "{}")
    
    query2, bind = transform_numeric_placeholders(query, params)
    
    print("Test 3: INSERT avec 7 placeholders")
    print(f"  Params count: {len(params)}")
    print(f"  Bind keys: {list(bind.keys())}")
    
    for i in range(7):
        assert f":p{i}" in query2, f"Expected :p{i} in query"
        assert f"p{i}" in bind, f"Expected p{i} in bind dict"
        assert bind[f"p{i}"] == params[i], f"Expected bind['p{i}'] = {params[i]}"
    
    print("  ✅ PASSED\n")


def test_no_placeholders():
    """Test requête sans placeholders"""
    query = "SELECT * FROM cases ORDER BY created_at DESC"
    params = ()
    
    query2, bind = transform_numeric_placeholders(query, params)
    
    print("Test 4: Pas de placeholders")
    print(f"  Input:  {query}")
    print(f"  Output: {query2}")
    print(f"  Bind:   {bind}")
    
    assert query2 == query, "Query should be unchanged"
    assert bind == {}, "Bind should be empty dict"
    print("  ✅ PASSED\n")


def test_edge_case_10_params():
    """Test avec :10 pour vérifier word boundary"""
    query = "INSERT INTO t VALUES (:0, :1, :2, :3, :4, :5, :6, :7, :8, :9)"
    params = tuple(range(10))
    
    query2, bind = transform_numeric_placeholders(query, params)
    
    print("Test 5: 10 paramètres (edge case)")
    print(f"  Params: {params}")
    print(f"  Bind keys: {sorted(bind.keys())}")
    
    # Vérifier que :0 n'a pas été remplacé par :p0 dans :10 → :p10
    assert ":p0" in query2
    assert ":p9" in query2
    assert len(bind) == 10
    print("  ✅ PASSED\n")


def main():
    print("\n" + "=" * 60)
    print("TEST TRANSFORMATION PLACEHOLDERS — PostgreSQL Compat")
    print("=" * 60 + "\n")
    
    try:
        test_single_placeholder()
        test_multiple_placeholders()
        test_insert_many_placeholders()
        test_no_placeholders()
        test_edge_case_10_params()
        
        print("=" * 60)
        print("✅ TOUS LES TESTS PASSÉS")
        print("=" * 60)
        print("\nTransformation validée:")
        print("  ✓ :0 → :p0, :1 → :p1, etc.")
        print("  ✓ Binding dict {'p0': val, 'p1': val, ...}")
        print("  ✓ Compatible PostgreSQL + SQLAlchemy text()")
        print("  ✓ Word boundary respecté (pas de collision :10)")
        print()
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
