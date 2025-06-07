FROM python:3.12-slim

COPY . .

RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["python", "main.py"]

