FROM python:3.11

COPY . .

RUN pip install -r requirements.txt

EXPOSE 443

CMD ["python", "main.py"]