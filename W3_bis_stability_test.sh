#!/bin/bash
# W3-bis — Test stabilité worker Railway 50 min (harness corrigé)
# Corrections: parsing latence (awk), heartbeat, validation gaps, logs robustes

set -euo pipefail

# Configuration
URL="https://dms-db-worker-production.up.railway.app"
TOKEN="${WORKER_AUTH_TOKEN}"
DURATION_MIN=50
INTERVAL_SEC=30
EXPECTED_PINGS=100

# Fichiers de sortie
RESULTS_CSV="W3_bis_results.csv"
HEARTBEAT_FILE="W3_bis_heartbeat.txt"
LOGS_FILE="W3_bis_railway_logs.txt"
VALIDATION_LOG="W3_bis_validation.log"

# Validation pré-run
if [ -z "$TOKEN" ]; then
    echo "❌ ERROR: WORKER_AUTH_TOKEN not set"
    exit 1
fi

echo "🟢 W3-bis stability test starting"
echo "Duration: $DURATION_MIN min | Expected pings: $EXPECTED_PINGS"
echo "Start time: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo ""

# Initialisation fichiers
echo "timestamp,endpoint,status_code,latency_ms,curl_exit_code" > "$RESULTS_CSV"
echo "$(date +%s)" > "$HEARTBEAT_FILE"

# Lancement capture logs Railway en arrière-plan
echo "Starting Railway logs capture..."
railway logs --service dms-db-worker --follow --tail 1000 > "$LOGS_FILE" 2>&1 &
LOGS_PID=$!
echo "Railway logs PID: $LOGS_PID"

# Vérification logs process actif
sleep 2
if ! kill -0 "$LOGS_PID" 2>/dev/null; then
    echo "⚠️  WARNING: Railway logs capture failed to start"
else
    echo "✅ Railway logs capture active"
fi

echo ""
echo "========================================="
echo "Test running... (Ctrl+C to abort)"
echo "========================================="
echo ""

# Boucle principale
start_epoch=$(date +%s)
end_epoch=$((start_epoch + DURATION_MIN * 60))
counter=0

while [ $(date +%s) -lt $end_epoch ]; do
    counter=$((counter + 1))
    current_epoch=$(date +%s)
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Heartbeat (preuve d'activité)
    echo "$current_epoch" > "$HEARTBEAT_FILE"

    # Ping test
    response=$(curl -s -w "\n%{http_code}\n%{time_total}\n%{exitcode}" \
        -H "Authorization: Bearer $TOKEN" \
        "$URL/db/ping" 2>&1)

    # Parsing robuste (awk, pas bc)
    http_code=$(echo "$response" | tail -3 | head -1)
    time_total=$(echo "$response" | tail -2 | head -1)
    curl_exit=$(echo "$response" | tail -1)

    # Conversion latence (awk portable)
    latency_ms=$(echo "$time_total" | awk '{printf "%.2f", $1 * 1000}')

    # Enregistrement
    echo "$ts,/db/ping,$http_code,$latency_ms,$curl_exit" >> "$RESULTS_CSV"

    # Check /db/info toutes les 10 itérations
    if [ $((counter % 10)) -eq 0 ]; then
        info_response=$(curl -s -w "%{http_code}" \
            -H "Authorization: Bearer $TOKEN" \
            "$URL/db/info" 2>&1)
        info_code=$(echo "$info_response" | tail -1)
        echo "$ts,/db/info,$info_code,," >> "$RESULTS_CSV"

        # Progress log
        elapsed_min=$(( (current_epoch - start_epoch) / 60 ))
        echo "[$counter/$EXPECTED_PINGS] ${elapsed_min}min — p$counter OK (HTTP $http_code, ${latency_ms}ms)"
    fi

    # Vérification logs process toujours actif (toutes les 10 itérations)
    if [ $((counter % 10)) -eq 0 ]; then
        if ! kill -0 "$LOGS_PID" 2>/dev/null; then
            echo "⚠️  WARNING: Railway logs capture died at ping $counter"
        fi
    fi

    sleep "$INTERVAL_SEC"
done

# Arrêt capture logs
if kill -0 "$LOGS_PID" 2>/dev/null; then
    kill "$LOGS_PID" 2>/dev/null || true
    echo "✅ Railway logs capture stopped"
fi

echo ""
echo "========================================="
echo "✅ Test completed"
echo "========================================="
echo "End time: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo "Pings executed: $counter"
echo ""

# Validation post-run
echo "Running post-run validation..." | tee "$VALIDATION_LOG"
echo "" | tee -a "$VALIDATION_LOG"

# 1. Comptage pings
ping_count=$(grep -c "/db/ping," "$RESULTS_CSV" || echo "0")
info_count=$(grep -c "/db/info," "$RESULTS_CSV" || echo "0")
total_requests=$((ping_count + info_count))

echo "1. Request counts:" | tee -a "$VALIDATION_LOG"
echo "   - Pings /db/ping: $ping_count / $EXPECTED_PINGS" | tee -a "$VALIDATION_LOG"
echo "   - Checks /db/info: $info_count" | tee -a "$VALIDATION_LOG"

if [ "$ping_count" -eq "$EXPECTED_PINGS" ]; then
    echo "   ✅ All pings executed" | tee -a "$VALIDATION_LOG"
else
    echo "   ❌ INCOMPLETE: Expected $EXPECTED_PINGS, got $ping_count" | tee -a "$VALIDATION_LOG"
fi

echo "" | tee -a "$VALIDATION_LOG"

# 2. Taux succès HTTP 200
http_200_count=$(grep "/db/ping,200," "$RESULTS_CSV" | wc -l)
success_rate=$(awk "BEGIN {printf \"%.1f\", ($http_200_count / $ping_count) * 100}")

echo "2. HTTP success rate:" | tee -a "$VALIDATION_LOG"
echo "   - HTTP 200: $http_200_count / $ping_count ($success_rate%)" | tee -a "$VALIDATION_LOG"

if (( $(echo "$success_rate >= 98" | bc -l) )); then
    echo "   ✅ Success rate ≥ 98%" | tee -a "$VALIDATION_LOG"
else
    echo "   ❌ FAIL: Success rate < 98%" | tee -a "$VALIDATION_LOG"
fi

# Codes erreur
error_codes=$(grep "/db/ping," "$RESULTS_CSV" | grep -v ",200," | cut -d',' -f3 | sort | uniq -c || echo "none")
echo "   - Error codes: $error_codes" | tee -a "$VALIDATION_LOG"

echo "" | tee -a "$VALIDATION_LOG"

# 3. Analyse latence
echo "3. Latency analysis:" | tee -a "$VALIDATION_LOG"

latencies=$(grep "/db/ping,200," "$RESULTS_CSV" | cut -d',' -f4 | grep -v "^$")
latency_count=$(echo "$latencies" | wc -l)

if [ "$latency_count" -gt 0 ]; then
    lat_min=$(echo "$latencies" | sort -n | head -1)
    lat_max=$(echo "$latencies" | sort -n | tail -1)
    lat_median=$(echo "$latencies" | sort -n | awk '{a[NR]=$1} END {print (NR%2==1)?a[(NR+1)/2]:(a[NR/2]+a[NR/2+1])/2}')
    lat_p95=$(echo "$latencies" | sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.95)]}')

    echo "   - Min: ${lat_min}ms" | tee -a "$VALIDATION_LOG"
    echo "   - Median: ${lat_median}ms" | tee -a "$VALIDATION_LOG"
    echo "   - P95: ${lat_p95}ms" | tee -a "$VALIDATION_LOG"
    echo "   - Max: ${lat_max}ms" | tee -a "$VALIDATION_LOG"

    if (( $(echo "$lat_p95 < 150" | bc -l) )); then
        echo "   ✅ P95 < 150ms (indicative target)" | tee -a "$VALIDATION_LOG"
    else
        echo "   ⚠️  P95 ≥ 150ms (above indicative target)" | tee -a "$VALIDATION_LOG"
    fi
else
    echo "   ❌ No valid latency data" | tee -a "$VALIDATION_LOG"
fi

echo "" | tee -a "$VALIDATION_LOG"

# 4. Détection gaps (timestamps > 60s écart anormal)
echo "4. Continuity check (gaps detection):" | tee -a "$VALIDATION_LOG"

timestamps=$(grep "/db/ping," "$RESULTS_CSV" | cut -d',' -f1)
prev_epoch=""
max_gap=0
gap_detected=0

while IFS= read -r ts; do
    current_epoch=$(date -d "$ts" +%s 2>/dev/null || echo "0")
    if [ -n "$prev_epoch" ] && [ "$current_epoch" -ne 0 ]; then
        gap=$((current_epoch - prev_epoch))
        if [ "$gap" -gt "$max_gap" ]; then
            max_gap=$gap
        fi
        if [ "$gap" -gt 60 ]; then
            echo "   ⚠️  Gap detected: ${gap}s between pings" | tee -a "$VALIDATION_LOG"
            gap_detected=1
        fi
    fi
    prev_epoch=$current_epoch
done <<< "$timestamps"

echo "   - Max gap between pings: ${max_gap}s" | tee -a "$VALIDATION_LOG"

if [ "$gap_detected" -eq 0 ]; then
    echo "   ✅ No abnormal gaps (all ≤ 60s)" | tee -a "$VALIDATION_LOG"
else
    echo "   ❌ FAIL: Gaps > 60s detected" | tee -a "$VALIDATION_LOG"
fi

echo "" | tee -a "$VALIDATION_LOG"

# 5. Logs Railway capturés
echo "5. Railway logs:" | tee -a "$VALIDATION_LOG"
logs_size=$(wc -l < "$LOGS_FILE")
echo "   - Lines captured: $logs_size" | tee -a "$VALIDATION_LOG"

if [ "$logs_size" -gt 10 ]; then
    echo "   ✅ Logs captured" | tee -a "$VALIDATION_LOG"
else
    echo "   ⚠️  WARNING: Logs may be incomplete" | tee -a "$VALIDATION_LOG"
fi

# Recherche erreurs critiques dans logs
errors=$(grep -i "error\|timeout\|disconnect\|reconnect" "$LOGS_FILE" | wc -l || echo "0")
echo "   - Error/timeout keywords: $errors occurrences" | tee -a "$VALIDATION_LOG"

if [ "$errors" -eq 0 ]; then
    echo "   ✅ No critical errors in logs" | tee -a "$VALIDATION_LOG"
else
    echo "   ⚠️  Errors detected, manual review required" | tee -a "$VALIDATION_LOG"
fi

echo "" | tee -a "$VALIDATION_LOG"
echo "=========================================" | tee -a "$VALIDATION_LOG"
echo "Validation complete. See $VALIDATION_LOG for details." | tee -a "$VALIDATION_LOG"
echo "=========================================" | tee -a "$VALIDATION_LOG"

# Résumé final
echo ""
echo "📊 Files generated:"
echo "   - Results: $RESULTS_CSV"
echo "   - Railway logs: $LOGS_FILE"
echo "   - Validation: $VALIDATION_LOG"
echo "   - Heartbeat: $HEARTBEAT_FILE"
