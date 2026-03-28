#!/bin/sh
set -e
#
# Point d’entrée image Docker (CMD ./start.sh) : pas d’interpolation $$ du Dockerfile
# (sur certains builders ça produisait 1PORT / 1{PORT}). PORT défaut 8080 si non défini.

# Image attendue : Dockerfile services/annotation-backend (backend.py à la racine de WORKDIR).
# Si ce fichier manque, Railway build probablement le Dockerfile racine (API DMS) : /health LS échouera.
if [ ! -f ./backend.py ]; then
  echo "[start.sh] ERROR: backend.py absent — ce conteneur n'est pas l'image annotation-backend." >&2
  echo "[start.sh] Vérifier Dockerfile Path = services/annotation-backend/Dockerfile et root = repo." >&2
  exit 1
fi

# Mistral : le backend dégrade déjà sans clé (fallback JSON). Ne plus exit 1 ici :
# sur Railway, une variable mal branchée sur le service provoquait une boucle de crash.
#
# Normalisation : retours ligne / espaces (copier-coller Windows, guillemets dans l’UI).
if [ -n "${MISTRAL_API_KEY:-}" ]; then
  # shellcheck disable=SC2001
  _k=$(printf '%s' "$MISTRAL_API_KEY" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  case $_k in
    \"*\")
      _k=${_k#\"}
      _k=${_k%\"}
      ;;
    \'*\')
      _k=${_k#\'}
      _k=${_k%\'}
      ;;
  esac
  export MISTRAL_API_KEY="$_k"
fi
# Alias parfois utilisé par erreur
if [ -z "${MISTRAL_API_KEY:-}" ] && [ -n "${MISTRAL_KEY:-}" ]; then
  _k=$(printf '%s' "$MISTRAL_KEY" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  case $_k in
    \"*\")
      _k=${_k#\"}
      _k=${_k%\"}
      ;;
    \'*\')
      _k=${_k#\'}
      _k=${_k%\'}
      ;;
  esac
  export MISTRAL_API_KEY="$_k"
fi

if [ -z "${MISTRAL_API_KEY:-}" ]; then
  echo "[start.sh] WARNING: MISTRAL_API_KEY is empty — uvicorn démarre quand même." >&2
  echo "[start.sh] Railway : ouvrir CE service (annotation-backend) → Variables → nom exact MISTRAL_API_KEY (pas seulement le projet)." >&2
  echo "[start.sh] Vérifier : pas de guillemets autour de la valeur, Redeploy après sauvegarde. GET /health → mistral_configured." >&2
else
  echo "[start.sh] MISTRAL_API_KEY défini (non vide)." >&2
fi

PORT="${PORT:-8080}"
echo "[start.sh] DMS annotation-backend — uvicorn backend:app — port=$PORT (Label Studio: GET /health)"
exec uvicorn backend:app --host 0.0.0.0 --port "$PORT" --log-level info 2>&1
