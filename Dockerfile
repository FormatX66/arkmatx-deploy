FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
COPY frontend ./frontend
RUN python -m pip install --no-cache-dir .
RUN useradd --create-home arkmatx && mkdir -p /app/data && chown -R arkmatx:arkmatx /app
USER arkmatx
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
