# AUDIT SENIOR — Decision Memory System V1
**Date** : 19 février 2026  
**Rôle** : Auditeur Senior / Tech Lead / Procurement Strategist  
**Périmètre** : Audit factuel du repository — zéro modification de code  
**Méthode** : Lecture exhaustive du code source, tests, documentation, CI/CD, architecture  

---

## RÉSUMÉ EXÉCUTIF

Le projet Decision Memory System (DMS) est un **assistant cognitif procurement** à deux couches (Couche A : exécution / Couche B : mémoire marché) qui vise à réduire de 90 % le travail répétitif d'analyse comparative (CBA/PV) dans les marchés publics et privés de la sous-région Afrique (Mali, Côte d'Ivoire initialement).

**Verdict global** : Le projet marche dans le bon sens. La vision est claire, l'architecture est saine, et la discipline d'exécution (Constitution gelée, ADR, invariants CI) est remarquable pour un projet à ce stade. **Cependant**, des failles systémiques et techniques précises empêchent le passage à l'échelle. Une fois corrigées, elles ne vont pas alourdir l'outil mais le rendre **redoutablement efficace**.

---

## TABLE DES MATIÈRES

1. [Ce que le projet fait bien](#1-ce-que-le-projet-fait-bien)
2. [Failles systémiques](#2-failles-systémiques)
3. [Failles techniques](#3-failles-techniques)
4. [Analyse stratégique : changement de paradigme ?](#4-analyse-stratégique--le-projet-tient-il-sa-promesse-)
5. [Matrice de priorité des corrections](#5-matrice-de-priorité-des-corrections)
6. [Conclusion](#6-conclusion)

---

## 1. CE QUE LE PROJET FAIT BIEN

| Aspect | Constat | Appréciation |
|--------|---------|--------------|
| **Vision** | Constitution gelée V3.3.2 avec 10 invariants non-négociables | ✅ Excellente discipline |
| **Architecture 2 couches** | Couche A autonome, Couche B consultative, flux B→A interdit | ✅ Séparation nette |
| **Choix technologique** | FastAPI + PostgreSQL strict (zéro SQLite), Alembic migrations SQL brut | ✅ Choix solides |
| **Code réel** | ~4 300 lignes de logique métier fonctionnelle sur ~5 200 LOC total | ✅ ~80 % code réel |
| **Moteur CBA** | Génération Excel multi-feuilles (Info Générales, Registre Dépôt, Analyse Technique/Financière, Synthèse) | ✅ Fonctionnel |
| **Moteur PV** | Génération Word (PV Ouverture + PV Analyse) horodaté | ✅ Fonctionnel |
| **Scoring** | Moteur multi-critères avec profils adaptatifs (Fournitures, Travaux, Services, Santé) | ✅ Conforme M3B |
| **Sécurité de base** | JWT + RBAC, BCrypt, validation MIME par magic bytes, rate limiting | ✅ Fondations correctes |
| **Tests** | 200+ fonctions de test, PostgreSQL réel (pas de mocks DB) | ✅ Base solide |
| **Résilience** | Circuit breaker (PyBreaker) + retry (Tenacity) sur les connexions DB | ✅ Bonne pratique |
| **Append-only** | Philosophie d'immutabilité dans l'architecture | ✅ Concept juste |
| **Invariants CI** | 9 fichiers de tests constitutionnels vérifiant la conformité à la vision | ✅ Unique et puissant |
| **Règles métier** | REGLES_METIER V1.4 mappé sur Code Marchés Mali + SCI | ✅ Ancré dans le réel |
| **ADR** | 3 Architecture Decision Records gelés (exécution, discipline, séparation) | ✅ Traçabilité décisionnelle |

---

## 2. FAILLES SYSTÉMIQUES

Ce sont les failles de conception, d'organisation ou de stratégie qui, une fois corrigées, renforcent structurellement l'outil.

### FS-01 : Couche B absente — pas de différenciation

**Constat** : La Couche B (mémoire marché, signaux prix, intelligence contextuelle) est **entièrement absente** du code. Seul un `resolvers.py` existe avec du fuzzy matching basique.

**Impact** : Sans Couche B, le DMS est un générateur de CBA/PV performant — mais pas un outil à mémoire. C'est la mémoire qui fait la promesse de changement de paradigme. Sans elle, il n'y a pas de différenciation par rapport à un Excel bien structuré.

**Correction** : Implémenter le pipeline de capture automatique (décisions → signaux) + recherche consultative. Ça n'alourdit pas : c'est un flux en lecture seule, append-only, découplé.

---

### FS-02 : Extraction DAO cassée — stub critique

**Constat** : La fonction `extract_dao_criteria_structured()` dans `src/api/analysis.py:32-39` est un **stub qui retourne toujours une liste vide**. Commentaire dans le code : *"STUB: This function was removed in previous refactoring but is still called."*

**Impact** : L'extraction automatique des critères d'un DAO/RFQ ne fonctionne pas. L'utilisateur doit saisir manuellement les critères — ce qui annule la promesse de réduction de charge cognitive de 90 %.

**Correction** : Réimplémenter la fonction ou câbler l'extraction existante dans `src/couche_a/extraction.py` (qui contient déjà du parsing PDF/DOCX/XLSX fonctionnel). Pas d'alourdissement — le code existe, il faut le rebrancher.

---

### FS-03 : API Scoring partiellement câblée

**Constat** : L'endpoint `POST /api/scoring/calculate` dans `src/couche_a/scoring/api.py` contient des commentaires `# stub - implement actual loading` et retourne `scores_count=0, eliminations_count=0`.

**Impact** : Le moteur de scoring **existe et fonctionne** (testé unitairement, 15 tests passent), mais l'API qui l'expose n'est pas branchée sur les données réelles du case.

**Correction** : Câbler le chargement des fournisseurs et critères depuis la DB vers le moteur. Le moteur est prêt — il manque la plomberie API.

---

### FS-04 : Couverture de tests à 5,2 % — fragilité structurelle

**Constat** : Le ratio code testé / code total est d'environ 5,2 % (selon l'audit CI du 17/02). 16 modules sur 31 dans `src/` n'ont **aucun test**.

**Modules non testés critiques** :
- `src/api/cases.py` — Création/listage de dossiers
- `src/api/analysis.py` — Pipeline d'analyse
- `src/api/documents.py` — Gestion documentaire
- `src/couche_a/services/cba.py` — Service CBA
- `src/couche_a/services/extraction.py` — Service d'extraction
- `src/couche_a/routers.py` — Routeurs Couche A (1 test skipé)

**Impact** : Toute modification risque de casser silencieusement une fonctionnalité. Le gate CI `fail_under=40` (activé via `.milestones/M-TESTS.done`) est un bon mécanisme mais le seuil réel est loin.

**Correction** : Prioriser les tests d'intégration API (cas réel : upload DAO → extraction → scoring → export CBA). Ça ne ralentit pas le développement — ça l'accélère en réduisant le debug.

---

### FS-05 : Pas de test de workflow bout-en-bout (E2E)

**Constat** : Aucun test ne valide le parcours complet : `Créer dossier → Upload DAO → Upload offres → Extraction → Scoring → Export CBA/PV`. Les tests sont unitaires ou d'intégration partielle.

**Impact** : Impossible de garantir que le flux complet fonctionne après chaque modification. Un acheteur en situation réelle pourrait rencontrer une rupture invisible entre deux étapes.

**Correction** : Un seul test E2E avec des données synthétiques suffit. Coût : ~100 lignes. Bénéfice : confiance totale.

---

### FS-06 : Dictionnaire procurement Sahel absent

**Constat** : L'ADR-0001 déclare le dictionnaire de normalisation comme *"non contournable"* (`M-NORMALISATION-ITEMS`). Or, aucun fichier de dictionnaire Sahel n'existe dans le code. Le module de normalisation n'est pas implémenté.

**Impact** : Sans dictionnaire, les termes des offres ne sont pas normalisés. Un fournisseur qui écrit "Ciment Portland CPA 45" et un autre qui écrit "Ciment CPA-45" sont traités comme deux items différents. La mémoire marché (Couche B) ne peut pas fonctionner sans normalisation.

**Correction** : Créer un fichier de référence (CSV/JSON) avec les items courants Sahel (BTP, fournitures bureau, médical). 200-300 entrées suffisent pour le MVP. Pas d'alourdissement — c'est un lookup table.

---

### FS-07 : Documentation dispersée et dupliquée

**Constat** : Le repository contient 20+ fichiers `.md` à la racine, un dossier `docs/` avec 60+ fichiers, un dossier `docs/freeze/` avec des copies gelées, un dossier `nano docs/` avec une ancienne version, et un dossier `ocs/`. Plusieurs documents existent en 3+ copies avec des versions différentes.

**Impact** : Un nouveau développeur ne sait pas quel document fait référence. Les mises à jour se font dans un fichier mais pas dans les copies. Le risque de dérive est élevé.

**Correction** : 
- `docs/` = source unique de vérité
- `docs/freeze/` = snapshots horodatés (garder mais ne plus dupliquer à la racine)
- Supprimer `nano docs/`, `ocs/`, et les `.md` redondants à la racine
- Garder à la racine uniquement : README.md, CHANGELOG.md, CONSTITUTION.md

---

## 3. FAILLES TECHNIQUES

Ce sont les failles de code, sécurité ou infrastructure qui, une fois corrigées, durcissent l'outil sans le complexifier.

### FT-01 : Clé JWT avec valeur par défaut en dur [CRITIQUE]

**Constat** : `src/auth.py:21`
```python
SECRET_KEY = os.getenv("JWT_SECRET", "CHANGE_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32")
```

**Impact** : Si la variable d'environnement `JWT_SECRET` n'est pas définie (oubli de configuration en production), tous les tokens sont signés avec une clé connue publiquement. **Contournement total de l'authentification possible.**

**Correction** : Supprimer la valeur par défaut. Lever une exception au démarrage si `JWT_SECRET` est absent.
```python
SECRET_KEY = os.environ["JWT_SECRET"]  # Crash explicite si absent
```

---

### FT-02 : Injection SQL via pattern LIKE [HAUTE]

**Constat** : `src/couche_a/routers.py:201-210`
```python
"supplier_pattern": f'%"supplier_name": "{supplier_name}"%',
```

**Impact** : L'input utilisateur `supplier_name` est injecté directement dans un pattern LIKE sans échappement. Un attaquant peut manipuler la requête de vérification de doublons.

**Correction** : Utiliser les opérateurs JSON PostgreSQL (`->>'supplier_name'`) ou échapper les caractères spéciaux LIKE (`%`, `_`, `\`).

---

### FT-03 : Append-only partiellement appliqué [HAUTE]

**Constat** : La migration `010_enforce_append_only_audit.py` ne révoque DELETE/UPDATE que sur 3 tables (`audits`, `market_signals`, `memory_entries`). Les tables `cases`, `artifacts`, `documents`, `scoring_results` ne sont **pas protégées** au niveau base de données.

**Impact** : La Constitution déclare "append-only" comme invariant fondamental, mais l'enforcement est incomplet. Un accès DB direct peut modifier ou supprimer des enregistrements de scoring ou d'analyse.

**Correction** : Étendre les REVOKE à toutes les tables de données métier, ou ajouter des triggers PostgreSQL `BEFORE DELETE/UPDATE` qui lèvent des exceptions.

---

### FT-04 : Endpoints API sans authentification [HAUTE]

**Constat** : Certains endpoints comme `list_cases()` dans `src/api/cases.py` n'ont pas de dépendance `CurrentUser`. Ils sont accessibles publiquement.

**Impact** : N'importe qui peut lister tous les dossiers d'achat, voir les métadonnées (titres, types de procédure, montants estimés). Information commercialement sensible.

**Correction** : Ajouter `current_user: User = Depends(get_current_user)` sur tous les endpoints métier. Filtrer par ownership.

---

### FT-05 : Expiration JWT de 8 heures [MOYENNE]

**Constat** : `src/auth.py:23` — `ACCESS_TOKEN_EXPIRE_MINUTES = 480`

**Impact** : Un token volé reste valide pendant 8 heures. Pas de mécanisme de refresh token ni de révocation.

**Correction** : Réduire à 1-2 heures. Implémenter un refresh token avec rotation. Coût : ~50 lignes. Bénéfice : sécurité significativement améliorée.

---

### FT-06 : Pas de journalisation des échecs d'authentification [MOYENNE]

**Constat** : `src/auth.py` — `authenticate_user()` retourne `None` silencieusement en cas d'échec. Aucun log, aucun compteur.

**Impact** : Les attaques par force brute passent inaperçues. Pas de détection d'intrusion possible.

**Correction** : Logger chaque échec avec username + IP (sans le mot de passe). Ajouter un compteur par IP avec blocage temporaire après N échecs.

---

### FT-07 : Pas de CORS configuré [MOYENNE]

**Constat** : `main.py` n'inclut pas `CORSMiddleware`. Aucune politique CORS définie.

**Impact** : Si le frontend est servi depuis un domaine différent de l'API, les requêtes seront bloquées par le navigateur. Inversement, si CORS est trop permissif, des sites malveillants peuvent faire des requêtes au nom de l'utilisateur.

**Correction** : Configurer explicitement les origines autorisées via variable d'environnement.

---

### FT-08 : Headers de sécurité HTTP absents [MOYENNE]

**Constat** : Aucun header de sécurité n'est configuré :
- Pas de `Strict-Transport-Security` (HSTS)
- Pas de `X-Content-Type-Options`
- Pas de `X-Frame-Options`
- Pas de `Content-Security-Policy`

**Impact** : Vulnérabilités XSS, clickjacking, et downgrade HTTPS possibles.

**Correction** : Un middleware de 10 lignes suffit.

---

### FT-09 : Pas de limite de taille de requête globale [BASSE]

**Constat** : Les uploads individuels sont limités (50 MB par fichier, 500 MB par case), mais il n'y a pas de `RequestSizeMiddleware` global.

**Impact** : Des requêtes JSON volumineuses (hors upload) peuvent consommer la mémoire du serveur.

**Correction** : Ajouter une limite globale au niveau middleware.

---

### FT-10 : Pool de connexions DB non configuré [BASSE]

**Constat** : `src/db.py` utilise les paramètres par défaut de SQLAlchemy pour le pool de connexions.

**Impact** : Sous charge, les connexions peuvent s'épuiser. Le `pool_pre_ping=True` est correctement configuré, mais `pool_size` et `max_overflow` sont aux valeurs par défaut.

**Correction** : Configurer explicitement `pool_size=20, max_overflow=40` (ou via variables d'environnement).

---

## 4. ANALYSE STRATÉGIQUE : LE PROJET TIENT-IL SA PROMESSE ?

### 4.1 Le projet va-t-il dans le bon sens ?

**OUI.** Sans ambiguïté. Voici pourquoi :

1. **Le problème est réel** : Dans la sous-région, un expert procurement passe 70-90 % de son temps à extraire des données de documents, les structurer dans Excel, calculer des scores, et rédiger des PV. Ce travail est répétitif, error-prone, et ne nécessite pas d'expertise — mais il consomme l'expertise.

2. **La solution est correctement cadrée** : Le DMS ne cherche pas à remplacer l'expert, mais à libérer sa capacité cognitive. La philosophie "non-décisionnel" (Invariant 4) est **stratégiquement juste** — dans un contexte où la confiance institutionnelle est fragile, un outil qui "recommande" serait rejeté. Un outil qui "structure et calcule" sera adopté.

3. **L'architecture est évolutive** : La séparation Couche A/B permet d'ajouter de l'intelligence (Couche B, puis LLM léger) sans toucher au moteur de scoring. C'est un design qui vieillit bien.

4. **Les règles métier sont ancrées dans le réel** : REGLES_METIER V1.4 cartographie les seuils du Code des Marchés du Mali ET du SCI (Standards Commerciaux Internationaux). Ce n'est pas un outil générique — il parle la langue de la sous-région.

### 4.2 Peut-il changer le paradigme du procurement dans la sous-région ?

**POTENTIELLEMENT OUI, mais sous conditions strictes :**

| Condition | Statut actuel | Verdict |
|-----------|---------------|---------|
| Couche A fonctionnelle end-to-end | ⚠️ 85 % (extraction DAO cassée) | Corrigeable en 1-2 semaines |
| Couche B opérationnelle | ❌ Absente | Bloquant pour la différenciation — 4-6 semaines |
| Dictionnaire Sahel | ❌ Absent | Bloquant pour la normalisation — 1-2 semaines |
| Adoption terrain sans formation | ⚠️ UI fonctionnelle mais basique | OK pour expert, pas pour junior |
| Sécurité production-ready | ⚠️ Fondations OK, failles critiques | 1 semaine de hardening |
| CI/CD opérationnel | ⚠️ Bloqué administrativement | 1 jour |
| Déploiement cloud | ✅ Railway/Render/Docker ready | Prêt |

### 4.3 Ce qui manque pour le changement de paradigme

1. **La mémoire marché** (Couche B) : C'est LE différenciateur. Sans elle, le DMS est un "Super Excel". Avec elle, c'est un outil qui dit *"La dernière fois qu'on a acheté du ciment Portland à Bamako, c'était à 85 000 FCFA/tonne chez Fournisseur X en septembre 2025"*. Cette intelligence contextuelle **n'existe nulle part** dans la sous-région. C'est ce qui change le paradigme.

2. **Le dictionnaire de normalisation** : Sans lui, la mémoire ne fonctionne pas. C'est la clé de voûte entre Couche A et Couche B.

3. **L'export 1-click CBA/PV** : Fonctionnel mais pas encore testé avec des données réelles de marché (seulement des données synthétiques). Le premier pilote terrain validera ou invaldera la promesse.

### 4.4 Risques stratégiques

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Rejet par les experts procurement (trop technique) | Moyenne | Fatal | UX test avec 3-5 experts terrain avant lancement |
| Problèmes de connectivité (Sahel = réseau instable) | Haute | Majeur | Constitution dit "online-only V1" — risque assumé mais réel |
| Résistance institutionnelle (peur du contrôle) | Moyenne | Majeur | Positionner comme outil de l'expert, pas de l'institution |
| Concurrence d'outils internationaux (SAP Ariba, etc.) | Basse | Faible | Ces outils ne parlent pas le langage procurement Sahel |
| Dérive fonctionnelle (trop de features) | Moyenne | Majeur | Constitution gelée = excellente protection |

---

## 5. MATRICE DE PRIORITÉ DES CORRECTIONS

### Corrections qui rendent l'outil redoutablement efficace sans l'alourdir :

| # | Faille | Effort | Impact | Priorité |
|---|--------|--------|--------|----------|
| FT-01 | JWT sans valeur par défaut | 1 ligne | Critique | **P0 — Immédiat** |
| FS-02 | Rebrancher extraction DAO | 2-3 jours | Critique | **P0 — Semaine 1** |
| FS-03 | Câbler API scoring | 1-2 jours | Haute | **P0 — Semaine 1** |
| FT-02 | Fix injection LIKE | 1 heure | Haute | **P0 — Semaine 1** |
| FT-04 | Auth sur tous les endpoints | 2 heures | Haute | **P0 — Semaine 1** |
| FT-03 | Append-only complet | 1 jour | Haute | **P1 — Semaine 2** |
| FS-04 | Tests intégration API | 1 semaine | Haute | **P1 — Semaine 2-3** |
| FS-05 | 1 test E2E complet | 2 jours | Haute | **P1 — Semaine 2** |
| FS-06 | Dictionnaire Sahel MVP | 1 semaine | Critique | **P1 — Semaine 2-3** |
| FT-05 | Refresh token + expiration courte | 2 jours | Moyenne | **P2 — Semaine 3** |
| FT-06 | Log des échecs auth | 2 heures | Moyenne | **P2 — Semaine 3** |
| FT-07 | CORS configuré | 1 heure | Moyenne | **P2 — Semaine 3** |
| FT-08 | Headers sécurité | 1 heure | Moyenne | **P2 — Semaine 3** |
| FS-01 | Couche B complète | 4-6 semaines | Critique | **P1 — Sprint 2-3** |
| FS-07 | Consolidation docs | 2 jours | Basse | **P3 — Continu** |

---

## 6. CONCLUSION

### Le projet est-il viable ?

**OUI.** Le DMS V1 est un projet sérieux avec une vision claire, une architecture saine, et une discipline d'exécution (Constitution, ADR, invariants CI) rarement vue dans des projets de cette taille. Le code est réel (~80 % fonctionnel), pas du scaffolding.

### Est-il prêt pour la production ?

**PAS ENCORE.** Trois bloqueurs :
1. L'extraction DAO est cassée (stub qui retourne vide)
2. La clé JWT a une valeur par défaut en dur
3. Certains endpoints sont publics sans authentification

Ces trois points se corrigent en **moins d'une semaine** sans toucher à l'architecture.

### Va-t-il changer le paradigme ?

**Il en a le potentiel, mais la Couche B est le catalyseur.** Sans elle, c'est un très bon outil. Avec elle, c'est un avantage compétitif unique dans la sous-région. Le dictionnaire de normalisation Sahel est la clé de voûte — sans lui, ni la Couche A ni la Couche B ne peuvent fonctionner à leur potentiel.

### Recommandation finale

> **Bétonner les 15 corrections identifiées dans cet ordre de priorité. Aucune n'alourdit l'outil — chacune le durcit.** La Couche A sera production-ready en 2-3 semaines. La Couche B (différenciateur stratégique) doit suivre dans le sprint suivant. Le premier pilote terrain avec 3-5 experts procurement validera définitivement la promesse.

---

*Rapport établi sans biais ni complaisance. Aucune modification de code effectuée.*  
*Basé sur l'analyse exhaustive de : 5 200 LOC Python, 200+ tests, 13 migrations SQL, 80+ fichiers de documentation, 6 workflows CI, 3 ADR.*
