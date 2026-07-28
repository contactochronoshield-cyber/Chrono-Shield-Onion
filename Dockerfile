FROM python:3.10-slim

# Crear usuario sin privilegios por seguridad
RUN useradd -m -u 1000 chronouser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
RUN chown -R chronouser:chronouser /app

USER chronouser

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:5000/health || exit 1

CMD ["python", "backend/api.py"]
