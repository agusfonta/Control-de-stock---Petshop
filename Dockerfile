FROM python:3.13-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY plantilla_productos.csv .
COPY start.sh ./start.sh
CMD ["sh", "./start.sh"]
