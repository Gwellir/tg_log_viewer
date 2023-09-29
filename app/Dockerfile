FROM python:3.10

ENV PYTHONUNBUFFERED 1

WORKDIR /opt/app

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", ":8000", "--workers", "4", "--threads", "4", "tg_log_viewer.wsgi"]
