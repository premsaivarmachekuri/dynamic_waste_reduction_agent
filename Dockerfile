FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generate synthetic data at container startup if not present
RUN python generate_data.py

EXPOSE 7860

CMD ["python", "app.py"]
