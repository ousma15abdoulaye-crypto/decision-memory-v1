text
# Decision Memory System

![Version](https://img.shields.io/badge/version-1.2.0-blue)
![Status](https://img.shields.io/badge/constitution-FROZEN-red)
![License](https://img.shields.io/badge/license-Internal-orange)

> **Un assistant cognitif intelligent en procurement, conçu pour restaurer la capacité de décision humaine sous pression opérationnelle.**

---

## 🎯 Mandat

Ce système part d'une douleur réelle:
- **99 offres sur 21 lots**
- **3 jours d'ouverture manuelle**
- Comités épuisés avant même l'analyse
- Paperasse qui écrase la réflexion

**Solution:** Remplacer le secrétariat procurement par un assistant intelligent qui:
- Ingère, classe, extrait les documents (DAO/RFQ, offres)
- Pré-remplit les CBA et PV
- Fait émerger une mémoire décisionnelle vivante
- Fournit un contexte marché actionnable

**Sans jamais:** décider à la place de l'humain, noter les fournisseurs, ou juger les personnes.

---

## 🏗️ Architecture

### Couche A — L'ouvrier cognitif
**Métaphore:** Le stagiaire ultra-efficace qui fait toute la paperasse.

**Modules:**
1. **Ingestion pragmatique** (Word, PDF, Excel, scans)
2. **Extraction structurée** (DAO/RFQ, offres techniques/financières)
3. **Pré-remplissage CBA/PV** (templates embarqués, mapping auto)
4. **Génération artefacts** (Excel, Word, PDF standards)

**Formats V1 prioritaires:** Word (.docx), PDF, Excel (.xlsx), scans qualité bureau.  
**Évolution future:** WhatsApp photos, images basse résolution.

### Couche B — Le collègue expérimenté
**Métaphore:** Le senior qui se souvient de tout et donne le contexte, sans dire quoi faire.

**Fonctions:**
- Mémoire décisionnelle passive (alimentée automatiquement)
- Market Intelligence (base MARKET_INTEL dense)
- Recherche factuelle ("Quels fournisseurs ont livré des NFI dans le Centre?")
- Rappels contextuels non intrusifs (cas similaires, prix historiques)
- Paquet audit/onboarding (ZIP complet cas)

---

## 📜 Constitution (FROZEN)

La Constitution V1.2 définit **12 invariants intouchables** qui gouvernent toute évolution du système.

**📖 [Lire la Constitution complète](./CONSTITUTION.md)**

### Invariants clés

1. **Réduction radicale de la charge cognitive** — Le système ne doit jamais augmenter l'effort.
2. **Primauté absolue de la Couche A** — L'ouvrier cognitif avant tout.
3. **Mémoire = sous-produit** — Jamais une obligation.
4. **Système non décisionnaire** — L'humain décide toujours.
5. **Traçabilité sans accusation** — Faits, pas jugements.
6. **Conception Sahel-first** — Chaos résilient.
7. **ERP-agnostique** — Fonctionne avec ou sans ERP.
8. **Online-first V1, offline-capable futur** — Pragmatisme adoption.
9. **Append-only** — On corrige en ajoutant, jamais en effaçant.
10. **Technologie subordonnée** — IA/OCR/LLM optionnels.
11. **Survivabilité absolue** — Au-delà du créateur.
12. **Fidélité au réel** — Enregistre ce qui s'est passé, pas ce qui aurait dû.

### Test Ultime de Dérive

Avant toute évolution, répondre à ces **3 questions**:

1. Est-ce que cela peut être utilisé **contre un individu** ?
2. Est-ce que cela **réduit la liberté de décision humaine** ?
3. Est-ce que cela **centralise le pouvoir cognitif** ?

👉 **Si OUI à une seule → rejet ou report Phase 3+.**

---

## 🚀 Quick Start

### Prérequis

- Python 3.10+
- Node.js 18+ (pour le frontend)
- PostgreSQL 14+ (SQLite pour dev)

### Installation

```bash
# Clone le repo
git clone https://github.com/votre-org/decision-memory-system.git
cd decision-memory-system

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install

# Démarrer
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
Configuration
Copier .env.example → .env et configurer:

text
DATABASE_URL=postgresql://user:pass@localhost:5432/dms
OPENAI_API_KEY=sk-...  # Optionnel, pour extraction avancée
SCI_MANUAL_PATH=./data/SC-PR-02-Procurement-Manual-3.2-FR.pdf
📁 Structure du Projet
text
decision-memory-system/
├── CONSTITUTION.md          # 📜 Document fondateur FROZEN
├── CHANGELOG.md             # 📝 Historique des versions
├── README.md                # Ce fichier
├── .github/
│   └── pull_request_template.md  # Template PR avec Test Ultime de Dérive
├── backend/
│   ├── app/
│   │   ├── main.py          # Point d'entrée FastAPI
│   │   ├── routes/          # Routes API (couche A, couche B)
│   │   ├── services/        # Logique métier
│   │   │   ├── ingestion.py
│   │   │   ├── extraction.py
│   │   │   ├── cba_generator.py
│   │   │   ├── pv_generator.py
│   │   │   └── market_intel.py
│   │   ├── models/          # ORM (SQLAlchemy)
│   │   ├── templates/       # Templates CBA/PV embarqués
│   │   └── config.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Composants React/Vue
│   │   ├── pages/           # Pages (création cas, mémoire, market intel)
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
└── data/
    ├── templates/           # Templates CBA Excel par catégorie
    │   ├── cba_materiel_bureau.xlsx
    │   ├── cba_nfi.xlsx
    │   ├── cba_vivres.xlsx
    │   └── ...
    ├── manual/              # Manuel Procurement SCI (référence)
    │   └── SC-PR-02-Procurement-Manual-3.2-FR.pdf
    └── samples/             # Échantillons pour tests
🎓 Documentation
Constitution V1.2 — Document fondateur FROZEN

Changelog — Historique des versions

Architecture détaillée — Design technique

Schéma de données — Tables et relations

Guide développeur — Contribuer au projet

Manuel utilisateur — Comment utiliser le système

🔒 Scope V1 (Non négociable)
✅ Inclus en V1
UN seul processus procurement (DAO ou RFQ) par instance

Max 3 écrans utilisateur

Ingestion Word, PDF, Excel, scans qualité

Extraction DAO/RFQ + offres techniques/financières

Pré-remplissage CBA/PV (templates embarqués)

Table MARKET_INTEL

Mémoire passive (alimentation automatique post-décision)

Recherche factuelle simple

Rappels contextuels (cas similaires)

Alertes prix (rappels factuels)

❌ Explicitement INTERDIT en V1
Scoring/ranking fournisseurs

Recommandations automatiques

Dashboards KPIs HQ

Compliance/audit/fraude

Multi-workflow complexe

Saisie données pour reporting uniquement

Dépendance ERP

Logique d'optimisation

🛠️ Tech Stack
Backend
Framework: FastAPI (Python 3.10+)

Database: PostgreSQL 14+ (SQLite pour dev)

ORM: SQLAlchemy

Extraction docs: python-docx, PyPDF2, openpyxl

OCR (optionnel): Tesseract, AWS Textract

AI (optionnel): OpenAI API, Anthropic Claude

Frontend
Framework: React 18 + Vite (ou Vue.js 3)

UI: Tailwind CSS + ShadCN/UI

State: Zustand ou Context API

Forms: React Hook Form + Zod

Infrastructure
Containerization: Docker + Docker Compose

CI/CD: GitHub Actions

Monitoring: Sentry (errors), Plausible (analytics)

Hosting V1: VPS (DigitalOcean, Hetzner) ou cloud (AWS, Azure)

🧪 Tests
bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm run test
📊 Critères de Succès V1
Le succès est démontré lorsque:

✅ Temps comité: 3 jours → < 1 jour

✅ Taux adoption: > 80% bureau pays dans 6 mois

✅ Satisfaction utilisateur: > 4/5 (NPS positif)

✅ Onboarding: < 15 minutes

✅ Support sollicité: < 5% des cas

✅ Aucune plainte "l'outil a décidé à ma place"

👉 Si le système nécessite une explication, il a déjà échoué.

🤝 Contribution
Process
Lire la Constitution V1.2 (obligatoire)

Fork le repo

Créer une branche feature (git checkout -b feature/ma-feature)

Commit avec messages conventionnels (feat:, fix:, docs:)

Push (git push origin feature/ma-feature)

Ouvrir une PR (le template inclut le Test Ultime de Dérive)

Rules
Toute PR doit passer le Test Ultime de Dérive (3 questions)

Vérifier la checklist des 12 invariants

Review obligatoire: Tech Lead + Product Owner

Si OUI à une question du Test → Governance board review requis

📞 Support
Issues GitHub: Pour bugs et features

Discussions GitHub: Pour questions générales

Email: abdoulaye.ousmane@savethechildren.org (créateur/mainteneur)

📄 License
Internal Use Only — Save the Children International
Ce système est propriétaire et destiné à un usage interne SCI uniquement.

🙏 Remerciements
Ce système a été conçu pour résoudre une douleur réelle vécue par les équipes procurement terrain au Sahel.

Patient Zéro: Cas MOPTI-2026-01 (21 lots, 99 offres, 3 jours d'ouverture manuelle)

Vision: Abdoulaye Ousmane (Supply Chain Coordinator, Save the Children Mali)

🎯 Roadmap
V1.0 (Q2 2026)
 Couche A complète (ingestion, extraction, pré-remplissage)

 Table MARKET_INTEL + alimentation passive

 Recherche factuelle + rappels contextuels

 Déploiement bureau pays Mali (Bamako, Mopti)

 Adoption > 80%

V1.5 (Q3 2026)
 Application mobile survey terrain

 Export/import données entre bases locales

 Templates CBA personnalisables (backend)

V2.0 (Q4 2026)
 Capacités offline progressives

 Support photos WhatsApp / images basse résolution

 OCR avancé

 LLM léger (si critères remplis: adoption > 80%, base > 500 entrées)

© 2026 — Decision Memory System

This system protects organizations from forgetting, not from their people.
