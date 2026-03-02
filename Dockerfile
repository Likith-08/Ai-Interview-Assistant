FROM python:3.10

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y ffmpeg

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 7860

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860"]