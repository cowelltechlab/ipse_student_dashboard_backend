# Pin to Debian 12 (bookworm) so Microsoft ODBC repo is available & signed
FROM python:3.12-bookworm

# Noninteractive apt installs
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# OS deps (use --no-install-recommends to keep image smaller)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    unixodbc \
    unixodbc-dev \
    libpq-dev \
    libreoffice \
 && rm -rf /var/lib/apt/lists/*

# Add Microsoft repo (bookworm) using keyring (no apt-key)
RUN set -eux; \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
      | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg; \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
      > /etc/apt/sources.list.d/mssql-release.list; \
    apt-get update; \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

# ODBC env (optional)
ENV ODBCINI=/etc/odbc.ini \
    ODBCSYSINI=/etc \
    LD_LIBRARY_PATH=/usr/lib:/usr/lib/x86_64-linux-gnu:/opt/microsoft/msodbcsql18/lib

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
