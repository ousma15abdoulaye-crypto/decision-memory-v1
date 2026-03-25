# M12 — Prérequis OCR / bridge (opérationnel)

Checklist avant d’alimenter le corpus (84 PDFs scannés) — **hors livrable code M12**, mais bloquant calibration terrain.

## 1. TLS / certificats

```bash
python -c "import urllib.request; urllib.request.urlopen('https://api.mistral.ai', timeout=10); print('OK')"
```

En cas d’échec (proxy / CA d’entreprise), pointer le bundle système :

- Windows : `set SSL_CERT_FILE=C:\path\to\cacert.pem` ou `set REQUESTS_CA_BUNDLE=...`
- Linux/macOS : `export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt`

## 2. Clés API (Railway → `.env.local`)

Copier depuis le dashboard Railway (variables `MISTRAL_API_KEY`, `LLAMA_CLOUD_API_KEY` / `LLAMADMS`) vers **`.env.local`** (déjà ignoré par git).

## 3. Validation stricte

```bash
python scripts/bridge_validate_env.py --strict
```

Code de sortie **0** si Mistral **et** Llama sont présents ; **1** sinon (bloque un run bridge cloud).

## 4. Run bridge sur les PDFs

Suivre le runbook projet (dossier des 84 PDFs, commande bridge habituelle). En cas d’échecs résiduels (MIME, taille), batch OCR externe + `scripts/merge_external_ocr_to_ls_tasks.py` si présent.

## 5. Rappel

Le **classifieur M12** se calibre sur les exports Label Studio (texte dans LS), pas sur la lecture seule R2.
