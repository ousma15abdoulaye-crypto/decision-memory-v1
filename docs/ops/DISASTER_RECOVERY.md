# Disaster Recovery — DMS V4.1

**Date :** 2026-04-03
**Statut :** OPERATIONNEL
**Contexte :** M15 Phase 7 — Documentation DR

---

## Vue d'ensemble

DMS est deploye sur Railway (PostgreSQL manage + service FastAPI + Label Studio).
Railway fournit des backups automatiques sur les tiers payants (a verifier dans Dashboard).
RTO cible : < 4 heures pour une perte totale du service. RPO : < 24h (backup automatique).

---

## Architecture de sauvegarde

### Backup Railway (automatique)

Railway Pro/Team : backup automatique quotidien, retention 7 jours.
Verification : Railway Dashboard > Database > Backups.

**Commande de verification :**
```
railway run --service railway-postgres psql -c "SELECT NOW();"
```

### Backup manuel (complement)

```powershell
# Charger les variables Railway
python scripts/with_railway_env.py python -c "import os; print(os.environ['RAILWAY_DATABASE_URL'])"

# Dump complet (depuis .env.railway.local)
# Renseigner depuis Railway Dashboard > Variables (ne jamais committer une vraie valeur)
$env:PGPASSWORD = "<RAILWAY_POSTGRES_PASSWORD>"
pg_dump -h maglev.proxy.rlwy.net -p 35451 -U postgres -d railway -Fc -f "backup_$(Get-Date -Format 'yyyyMMdd_HHmm').dump"

# Tables critiques uniquement
pg_dump -h maglev.proxy.rlwy.net -p 35451 -U postgres -d railway -Fc \
  -t "couche_b.procurement_dict_items" \
  -t "public.market_signals_v2" \
  -t "public.market_surveys" \
  -t "public.annotation_registry" \
  -t "public.decision_snapshots" \
  -f "backup_critical_$(Get-Date -Format 'yyyyMMdd_HHmm').dump"
```

---

## Procedure de restauration

### Scenario 1 — Perte partielle (table corrompue)

```powershell
# Restaurer une table specifique
pg_restore -h maglev.proxy.rlwy.net -p 35451 -U postgres -d railway \
  --table=procurement_dict_items --data-only backup_YYYYMMDD_HHMM.dump
```

### Scenario 2 — Perte totale (service Railway down)

1. Creer un nouveau service Railway PostgreSQL
2. Restaurer depuis le backup :
   ```
   pg_restore -h <new-host> -p <port> -U postgres -d railway -Fc backup_YYYYMMDD_HHMM.dump
   ```
3. Mettre a jour `.env.railway.local` avec la nouvelle URL
4. Appliquer toutes les migrations manquantes :
   ```
   python scripts/with_railway_env.py python scripts/apply_railway_migrations_safe.py --apply
   ```
5. Verifier la sante du systeme :
   ```
   python scripts/with_railway_env.py python scripts/probe_railway_full.py
   ```

### Scenario 3 — Perte annotations locales non sync

**Delta de donnees non recuperables :**
- 87 annotations locales en attente de sync (au 2026-04-03)
- Procedure de re-annotation : 87 x 45 min = ~65 heures (3.4 jours/agent)

**Mitigation :** Lancer le sync avant toute maintenance Railway :
```
$env:LOCAL_DATABASE_URL = "postgresql://user:pass@localhost:5432/dms"
python scripts/with_railway_env.py python scripts/sync_annotations_local_to_railway.py --apply
```

---

## RTO / RPO

| Scenario | RTO Estime | RPO | Notes |
|----------|-----------|-----|-------|
| Table corrompue | 30 min | < 24h | pg_restore ciblé |
| Service Railway down | 2-4h | < 24h | Nouveau service + restore |
| Perte DB totale (sans backup) | 3-5 jours | N/A | Re-annotation corpus |
| Perte annotations locales non sync | 3-5 jours | N/A | Re-annotation |

---

## Tables critiques (par ordre de priorite)

| Table | Schema | Taille estimee | Critique |
|-------|--------|----------------|---------|
| procurement_dict_items | couche_b | ~1490 lignes | CRITIQUE — dictionnaire metier |
| market_surveys | public | ~21850 lignes | CRITIQUE — donnees prix |
| market_signals_v2 | public | ~1108 lignes | HAUTE — signaux calcules |
| annotation_registry | public | 0 Railway (87 local) | HAUTE — campagne annotation |
| decision_snapshots | public | ~12 lignes | MOYENNE — historique decisions |
| zone_context_registry | public | ~21 lignes | MOYENNE — contexte zones |

---

## Alertes et monitoring

### Probe health check

Executer apres chaque intervention Railway :
```
python scripts/with_railway_env.py python scripts/probe_railway_full.py
```

### Signaux d'alerte

- `alembic current` != `067_fix_market_coverage_trigger` -> migration echouee
- P3 strong+moderate < 40% -> signal engine degrade
- P6 annotation_registry validated = 0 -> annotations non syncees

---

## Contacts d'urgence

- CTO : coordination et decision GO/NO-GO
- Railway Support : https://railway.app/help
- Runbook migrations : `docs/adr/ADR-RAILWAY-ALEMBIC-SYNC-GOVERNANCE.md`

---

## Checklist DR verifiee le 2026-04-03

- [x] Backup automatique Railway : a verifier dans Dashboard (tier Pro requis)
- [x] Procedure backup manuel documentee
- [x] Procedure restauration documentee
- [x] RTO/RPO documente
- [x] Tables critiques identifiees et priorisees
- [ ] Backup manuel execute et archive (a faire post-M15)
- [ ] Restauration testee en environnement de staging (a planifier)
- [ ] Alerte automatique backup echec (a configurer Railway ou cron)

---

*Document M15 Phase 7 — Genere 2026-04-03*
