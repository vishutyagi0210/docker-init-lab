FROM python as builder

WORkDIR /app

COPY . .

RUN pip install -r requirements.txt --target /app/data

#################################### stage-2 #######################################
FROM python:slim

WORKDIR /app

COPY --from=builder /app/main.py /app/main.py

COPY --from=builder /app/data /app/data

ENV PYTHONPATH=/app/data

RUN groupadd -r appusers && useradd -r -g appusers rajpal

RUN chown rajpal:appusers /app/main.py

USER rajpal  

CMD ["python","main.py"]  
