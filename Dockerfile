FROM python:3.11-slim

# 1. System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    python3-renderpm \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Upgrade pip and install OpenEnv
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
# openenv[core] installs the base package; openenv-core provides the openenv.core subpackage
RUN pip install --no-cache-dir "openenv[core]==0.1.3" openenv-core

# 🚩 THE CRITICAL HACK: 
# OpenEnv 0.1.3 __init__.py does both 'import env' AND 'import agent'.
# We create dummy packages for both to satisfy it.
RUN mkdir -p /app/env && touch /app/env/__init__.py
RUN mkdir -p /app/agent && touch /app/agent/__init__.py

# 3. Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy all project files
# models.py and other root-level modules live alongside server/ — COPY server/ misses them.
COPY models.py .
COPY server/ ./server/
COPY openenv.yaml . 
COPY inference.py .
# 5. Set the Python Path
# We point to /app so it finds our dummy 'env' and your 'server'
ENV PYTHONPATH="/app:/app/server"

# 6. Verification - This should finally pass
RUN python3 -c "import pkgutil, openenv; mods = [m.name for m in pkgutil.iter_modules(openenv.__path__)]; print('openenv submodules:', mods); from openenv.core.env_server.http_server import create_app; print('Jessica.ai: Environment Engine Ready')"

RUN mkdir -p /app/logs && chmod 777 /app/logs

EXPOSE 7860

# 7. Start the server
CMD ["python3", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]