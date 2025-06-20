FROM python:3.12

RUN mkdir /kmk-project

WORKDIR /kmk-project

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .
