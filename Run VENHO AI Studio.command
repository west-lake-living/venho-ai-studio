#!/bin/zsh

set -e

cd "/Users/hanhpham/Developer/Claude-Workspace/projects/03_AI_STUDIO/venho-ai-studio"

export PATH="$HOME/Library/Python/3.9/bin:$PATH"

python3 -m streamlit run ui/studio_app.py --server.port 8501
