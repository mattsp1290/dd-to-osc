FROM python:3-alpine

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY dd-to-osc.py dd-to-osc.py
CMD [ "python3", "-u", "dd-to-osc.py"]