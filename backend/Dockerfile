FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml .
RUN pip install --no-cache-dir -e . 2>/dev/null || pip install --no-cache-dir \
    strands-agents strands-agents-tools bedrock-agentcore \
    fastapi "uvicorn[standard]" httpx "sqlalchemy[asyncio]" asyncpg psycopg2-binary \
    alembic redis pydantic pydantic-settings python-dotenv pandas numpy boto3 \
    "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt<5" python-multipart \
    aiohttp apscheduler jinja2 nest-asyncio playwright markdown pgvector

# Copy app
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
