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

# Mistral : le backend dégrade sans clé (fallback). Ne pas exit 1 (évite boucle Railway).
#
# Ordre : MISTRAL_API_KEY → DMS_API_MISTRAL (Railway DMS) → MISTRAL_KEY.
# Trim CR/LF/espaces ; retire guillemets externes si l’UI Railway les a inclus.
_trim_key() {
  printf '%s' "$1" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}
_strip_outer_quotes() {
  _v="$1"
  case $_v in
    \"*\")
      _v=${_v#\"}
      _v=${_v%\"}
      ;;
    \'*\')
      _v=${_v#\'}
      _v=${_v%\'}
      ;;
  esac
  printf '%s' "$_v"
}
_normalize_mistral_value() {
  _strip_outer_quotes "$(_trim_key "$1")"
}

if [ -n "${MISTRAL_API_KEY:-}" ]; then
  export MISTRAL_API_KEY="$(_normalize_mistral_value "$MISTRAL_API_KEY")"
fi
if [ -z "${MISTRAL_API_KEY:-}" ] && [ -n "${DMS_API_MISTRAL:-}" ]; then
  export MISTRAL_API_KEY="$(_normalize_mistral_value "$DMS_API_MISTRAL")"
fi
if [ -z "${MISTRAL_API_KEY:-}" ] && [ -n "${MISTRAL_KEY:-}" ]; then
  export MISTRAL_API_KEY="$(_normalize_mistral_value "$MISTRAL_KEY")"
fi

if [ -z "${MISTRAL_API_KEY:-}" ]; then
  echo "[start.sh] WARNING: aucune clé Mistral (MISTRAL_API_KEY ou DMS_API_MISTRAL) — fallback prédictions." >&2
else
  echo "[start.sh] Clé Mistral chargée (MISTRAL_API_KEY ou DMS_API_MISTRAL)." >&2
fi

PORT="${PORT:-8080}"
echo "[start.sh] DMS annotation-backend — uvicorn backend:app — port=$PORT (GET /health)" >&2
exec uvicorn backend:app --host 0.0.0.0 --port "$PORT" --log-level info 2>&1
