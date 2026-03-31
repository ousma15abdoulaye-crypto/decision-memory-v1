# ADR-M12-LLM-ARBITRATOR — M12 LLM Arbitration Layer

**Statut** : ACCEPTE  
**Date** : 2026-03-30  
**Auteur** : CTO / AO — Abdoulaye Ousmane  
**Regle** : REGLE-11 (toute integration LLM dans le moteur = ADR obligatoire)  

---

## Contexte

M12 (Procurement Document & Process Recognizer v6) est un moteur deterministe a 7 couches actives. Il classifie, extrait et lie des documents procurement via des regles regex, YAML config, et fuzzy matching.

Le deterministe excelle pour les cas frequents et bien structures (DAO, TDR, offres standards). Il echoue ou hesite sur :
- Documents atypiques (langues mixtes, OCR scanne, abreviations non standard)
- Parties obligatoires quasi-presentees (section sans heading explicite)
- Liens entre documents sans reference commune explicite (ex. offre financiere liee a un DAO via contexte projet)

Ces cas sont precisement ceux ou un procurement specialist senior prendrait une decision en 2 secondes. DMS doit faire de meme.

## Decision

Integrer un **LLM Arbitrator** — un module central (`src/procurement/llm_arbitrator.py`) qui encapsule tous les appels LLM du moteur M12. Le LLM est appele **chirurgicalement**, uniquement quand le deterministe doute.

**Modele** : `mistral-large-latest` (Tier 1 existant, via `llm_router.get_llm_client()`)  
**Temperature** : 0.0 (mode deterministe, pas de creativite)  
**Format** : `response_format={"type": "json_object"}` — JSON structure, jamais de prose  

## Perimetre : Arbitrage, pas Extraction

Le LLM Arbitrator **n'extrait pas** de donnees. Il **arbitre** entre des options proposees par le deterministe.

| Tache | Trigger | Plafond confiance |
|-------|---------|-------------------|
| `disambiguate_document_type` | confidence_det < 0.80 ou UNKNOWN | 0.85 |
| `detect_mandatory_part` | L1 + L2 ont echoue | 0.70 |
| `semantic_link_documents` | fuzzy < 0.85 ET lien contextuel possible | 0.80 |

## Regles de garde

1. **Taxonomie guard** : `disambiguate_document_type` ne peut retourner que les candidats du deterministe. Un type hors enum `DocumentKindParent` est rejete et logge.
2. **Plafonds de confiance** : chaque methode a un plafond strictement inferieur a 1.0 — l'humain reste decisionnaire sur les cas LLM.
3. **Fallback offline** : si `MISTRAL_API_KEY` absente, `is_available()` retourne `False` et toutes les methodes retournent `TracedField(value=None, confidence=0.0)`. Le moteur continue sans LLM.
4. **Timeout strict** : 10s par appel, 1 retry (configurable via `config/llm_arbitration.yaml`).
5. **Traceabilite** : chaque reponse LLM produit un `TracedField` avec `evidence=["llm_arbitration:<model>", ...]` — auditables dans Label Studio.
6. **Securite** : extraits tronques (max 3000 chars pour le type, 2000 chars pour les parties, 500 chars pour les liens). Zero donnee personnelle ou sensible dans les prompts.
7. **Non-bloquant** : toute exception dans le LLM Arbitrator est loggee WARNING et le flux continue avec le resultat deterministe.

## Cout estime

| Methode | Tokens entree | Tokens sortie | Cout estimé (mistral-large) |
|---------|--------------|--------------|----------------------------|
| disambiguate_document_type | ~1200 | ~80 | ~0.003 USD |
| detect_mandatory_part | ~800 | ~60 | ~0.002 USD |
| semantic_link_documents | ~600 | ~80 | ~0.002 USD |

Budget par document (cas difficile avec 3 appels) : ~0.007 USD. 
Sur 1000 documents, si 20% necessitent arbitrage : ~1.40 USD.

## Integration dans M12

| Module | Integration |
|--------|-------------|
| `pass_1a_core_recognition.py` | Apres L3, si confidence < 0.80 ou UNKNOWN |
| `mandatory_parts_engine.py` | Level 3, apres L1 + L2 echec |
| `process_linker.py` | Level 5 (SEMANTIC_LLM), apres CONTEXTUAL |

## Injection (pas de couplage dur)

Le `MandatoryPartsEngine` et `build_process_linking` acceptent un parametre `llm_arbitrator=None`. Si `None`, comportement offline inchange. L'injection se fait a l'initialisation de la pipeline (Pass 1C / Pass 1D).

## Modele alternatif considere

`mistral-small-latest` : moins couteux mais moins precis sur les nuances de langage Afrique de l'Ouest. Rejete car la difference de cout (<0.005 USD par appel) ne justifie pas une reduction de precision sur des decisions d'achat.

## Rollback

Désactiver via `LLM_ARBITRATOR_ENABLED=false` dans Railway Variables (priorité maximale — inspecté avant tout appel LLM). Le moteur deterministe reprend la main integrale sans redeploiement. Alternativement, passer `arbitration.enabled: false` dans `config/llm_arbitration.yaml` (nécessite redéploiement).
