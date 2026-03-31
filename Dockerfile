# Dockerfile - Flask App (Backend/Frontend)
FROM python:3.11-slim

WORKDIR /app

# Instala dependências Python primeiro (cache de camada)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código-fonte da aplicação
COPY main.py .
COPY app/ ./app/
COPY database/schema.sql ./database/schema.sql
COPY database/init_db.py ./database/init_db.py
COPY database/migrate_ia.py ./database/migrate_ia.py
COPY database/migrate_schema_pncp.py ./database/migrate_schema_pncp.py
COPY templates/ ./templates/
COPY static/ ./static/

# Cria pasta de downloads (será mapeada como volume)
RUN mkdir -p /app/downloads

EXPOSE 5000

CMD ["python", "main.py"]
