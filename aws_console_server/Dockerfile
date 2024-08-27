FROM python:3.12.5-alpine3.20

WORKDIR /aws_console_server
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"]