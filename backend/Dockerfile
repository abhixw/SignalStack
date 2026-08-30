# Pinned to bookworm (Debian 12, OpenSSL 3.0.x), not the unqualified
# python:3.12-slim tag — that currently resolves to trixie (Debian 13),
# whose much newer OpenSSL 3.5.x fails the TLS handshake against MongoDB
# Atlas with "SSL: TLSV1_ALERT_INTERNAL_ERROR" (confirmed empirically:
# same MONGODB_URI connects fine outside Docker, and switching tlsCAFile
# didn't help — this is a protocol/cipher negotiation issue, not CA trust).
FROM python:3.12-slim-bookworm

WORKDIR /app

# System deps for bcrypt/cryptography wheels on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
