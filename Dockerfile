# Pin to Debian 12 (bookworm)
FROM python:3.12-bookworm
ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg \
    unixodbc unixodbc-dev libpq-dev \
    # add build + xmlsec toolchain:
    build-essential pkg-config \
    libxml2 libxml2-dev libxslt1-dev \
    libxmlsec1 libxmlsec1-dev libxmlsec1-openssl \
 && rm -rf /var/lib/apt/lists/*

# Microsoft ODBC repo (unchanged)
RUN set -eux; \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
      | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg; \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
      > /etc/apt/sources.list.d/mssql-release.list; \
    apt-get update; \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

ENV ODBCINI=/etc/odbc.ini \
    ODBCSYSINI=/etc \
    LD_LIBRARY_PATH=/usr/lib:/usr/lib/x86_64-linux-gnu:/opt/microsoft/msodbcsql18/lib

# Python deps
COPY requirements.txt .

# Force source builds for lxml & xmlsec so they use the system libxml2/xmlsec
RUN pip install --no-cache-dir --no-binary=lxml,xmlsec -r requirements.txt

# App code
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
