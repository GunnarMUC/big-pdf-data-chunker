FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-script-frak \
    ghostscript \
    qpdf \
    pngquant \
    unpaper \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    && pip install --no-cache-dir ocrmypdf==16.10.0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY worker.py .

EXPOSE 5000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "600", "app:create_app()"]
