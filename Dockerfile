FROM python:3.11-slim

COPY . /home
WORKDIR /home

# System deps for building some wheels
RUN apt-get update && apt-get install -y build-essential curl git && rm -rf /var/lib/apt/lists/*

# Install project base requirements and MCP
RUN pip3 install --upgrade pip \
 && pip3 install -r requirements.base.txt \
 && pip3 install --no-cache-dir openai==1.40.6 "mcp==1.12.4" \
 && pip3 install --no-cache-dir httpx==0.25.2

# Optional: install full requirements if desired (may fail on some arches)
# RUN pip3 install -r requirements.txt
