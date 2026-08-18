# madhava-service — ponte HTTP Madhava -> Liferay
# Base: Python 3.12-slim + wheel manylinux cp312 do winnex-madhava (C++20).
# IMPORTANTE: o winnex-madhava 1.8.8 publica wheel manylinux apenas para
# cp312 no PyPI (verificado). Python 3.12 evita compilar o sdist (C++).
FROM python:3.12-slim

WORKDIR /app

# Copia o codigo do servico de ponte (src/app.py) e as dependencias
COPY src/ /app/src/
COPY requirements.txt /app/requirements.txt

# winnex-madhava 1.8.8 depende APENAS de numpy (verificado no pyproject).
# Nao usa sentence-transformers. O motor recebe vetores float32 prontos.
# O wheel manylinux cp312 instala sem compilador.
RUN pip install --no-cache-dir -r /app/requirements.txt

ENV PYTHONPATH=/app/src
EXPOSE 8600

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8600"]
