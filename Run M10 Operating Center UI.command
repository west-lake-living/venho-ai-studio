#!/bin/zsh

set -u

REPO_DIR="/Users/hanhpham/Developer/Claude-Workspace/projects/03_AI_STUDIO/venho-ai-studio"
PORT="${VENHO_UI_PORT:-8501}"
URL="http://localhost:$PORT"

cd "$REPO_DIR"
export PATH="$HOME/Library/Python/3.9/bin:$PATH"

echo "Starting VENHO AI Studio — M10 Operating Center"
echo "Repo: $REPO_DIR"
echo "URL:  $URL"
echo ""

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "A UI server is already running on port $PORT."
  echo "Opening $URL ..."
  open "$URL"
  echo ""
  echo "You can close this Terminal window."
  exit 0
fi

if ! python3 -m streamlit --version >/dev/null 2>&1; then
  echo "Streamlit is not installed for python3."
  echo 'Installing UI dependencies with: python3 -m pip install -e ".[ui]"'
  python3 -m pip install -e ".[ui]"
  if ! python3 -m streamlit --version >/dev/null 2>&1; then
    echo ""
    echo "Could not install Streamlit automatically."
    echo 'Try manually: python3 -m pip install -e ".[ui]"'
    echo ""
    echo "Press Enter to close this window."
    read
    exit 1
  fi
fi

(sleep 2; open "$URL") &

python3 -m streamlit run ui/studio_app.py \
  --server.address localhost \
  --server.port "$PORT" \
  --server.headless true

echo ""
echo "UI stopped. Press Enter to close this window."
read
