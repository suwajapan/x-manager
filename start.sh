#!/bin/bash
cd /Users/nakayuu/Documents/諏訪/x-manager
python3 -m uvicorn main:app --port 8001 --loop asyncio
