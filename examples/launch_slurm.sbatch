#!/usr/bin/env bash
#SBATCH --job-name=file-explorer
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=02:00:00
#SBATCH --output=file-explorer-%j.out

set -euo pipefail
: "${EXPLORER_APP_DIR:?Set EXPLORER_APP_DIR to the shared app directory}"
: "${EXPLORER_PYTHON:?Set EXPLORER_PYTHON to the cluster virtualenv Python executable}"
: "${FILE_EXPLORER_ROOTS:?Set FILE_EXPLORER_ROOTS to a JSON mapping of allowed roots}"
explorer_port="${EXPLORER_PORT:-8517}"
if [[ ! "$explorer_port" =~ ^[0-9]+$ ]] || (( explorer_port < 1024 || explorer_port > 65535 )); then
  echo "EXPLORER_PORT must be between 1024 and 65535" >&2
  exit 2
fi
cd "$EXPLORER_APP_DIR"
printf 'Compute host: %s\nPort: %s\n' "$(hostname -f)" "$explorer_port"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
exec "$EXPLORER_PYTHON" -m streamlit run streamlit_app.py \
  --server.address=127.0.0.1 \
  --server.port="$explorer_port" \
  --server.headless=true
