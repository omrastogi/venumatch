#!/usr/bin/env bash
# start.sh — launch VenuMatch API + Streamlit UI
#
# Usage:
#   bash start.sh            # start both servers
#   bash start.sh --api      # API only  (port 8000)
#   bash start.sh --ui       # UI only   (port 8501, API must already be running)

set -e

ENV=struct_rag
API_PORT=8000
UI_PORT=8501

start_api() {
    echo "[api] starting FastAPI on port $API_PORT..."
    conda run -n $ENV uvicorn api:app --host 0.0.0.0 --port $API_PORT --reload &
    API_PID=$!
    echo "[api] pid=$API_PID"

    # wait for health check
    echo "[api] waiting for /health..."
    for i in $(seq 1 30); do
        if curl -sf "http://localhost:$API_PORT/health" > /dev/null 2>&1; then
            echo "[api] ready"
            return 0
        fi
        sleep 1
    done
    echo "[api] ERROR: did not become ready in 30s" >&2
    kill $API_PID 2>/dev/null
    exit 1
}

start_ui() {
    echo "[ui] starting Streamlit on port $UI_PORT..."
    conda run -n $ENV streamlit run app.py \
        --server.port $UI_PORT \
        --server.headless true \
        --browser.gatherUsageStats false
}

case "${1:-}" in
    --api)
        start_api
        wait
        ;;
    --ui)
        start_ui
        ;;
    *)
        start_api
        echo ""
        echo "======================================"
        echo "  VenuMatch API  : http://localhost:$API_PORT"
        echo "  Streamlit UI   : http://localhost:$UI_PORT"
        echo "  API docs       : http://localhost:$API_PORT/docs"
        echo "======================================"
        echo ""
        start_ui
        ;;
esac
