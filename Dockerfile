FROM python:3

WORKDIR /build

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "./src/riots-webthings.py"]
