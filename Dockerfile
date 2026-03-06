FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN useradd -m -r apiuser
COPY ./app ./app
EXPOSE 8000
USER apiuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
