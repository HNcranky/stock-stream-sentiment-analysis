FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY stock_producer.py .
COPY stock_data.csv .

CMD ["python", "stock_producer.py"]
