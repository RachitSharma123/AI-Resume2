#!/bin/bash
cd /home/rachit/AI-Resume2
export DEEPSEEK_API_KEY=sk-20be22cb459f454697a37d1eee766d3a
export AI_PROVIDER=deepseek
exec uvicorn api.index:app --host 0.0.0.0 --port 8001 --workers 2
