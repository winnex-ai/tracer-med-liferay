# madhava-service — ponte HTTP Madhava -> Liferay
# Base: Python 3.12-slim. Consumes winnex-tracer + winnex-ai-normalize +
# winnex-madhava from PyPI.
FROM python:3.12-slim

WORKDIR /app

COPY src/ /app/src/
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --force-reinstall -r /app/requirements.txt
# O quality gate (winnex_ai_normalize.core.quality) decide basis/k1/stage1
# pela prova do motor sobre o corpus. Fixar basis no app é errado: pca_corpus
# degrada recall em dados sem manifold (Word2Vec 0.677→0.096, ProtBERT
# 1.0→0.134, medidos) e random exclui 0% em manifold forte.
# >=1.9.24 e obrigatorio, nao preferencia: 1.9.3 segfaulta em set_basis()
# com quant=INT8, o que torna basis="pca_corpus" (UB Width) inalcancavel. Sem
# essa versao, app.py nao consegue produzir exclusao com prova — o certificado
# sai com total_provably_excluded=0, valido e vazio. 1.9.24 tambem honra o k
# por chamada e marca degradacao (degraded_reason) no commitment assinado.
RUN pip install --no-cache-dir --force-reinstall "winnex-madhava>=1.9.24"

ENV PYTHONPATH=/app/src
EXPOSE 8600

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8600"]
