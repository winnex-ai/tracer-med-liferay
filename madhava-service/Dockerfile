# madhava-service — ponte HTTP Madhava -> Liferay
# Base: Python 3.12-slim. Consumes winnex-tracer + winnex-ai-normalize +
# winnex-madhava 1.9.2 from PyPI.
FROM python:3.12-slim

WORKDIR /app

COPY src/ /app/src/
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --force-reinstall -r /app/requirements.txt
RUN pip install --no-cache-dir --force-reinstall "winnex-madhava==1.9.2"

ENV PYTHONPATH=/app/src
EXPOSE 8600

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8600"]
