FROM ghcr.io/data-privacy-stack/presidio-analyzer:latest

WORKDIR /app

COPY ./server.py /app/server.py

RUN pip install --no-cache-dir PyYAML uvicorn fastapi

EXPOSE 3000

CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]