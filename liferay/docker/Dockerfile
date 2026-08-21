# Tracer-MED × Tracer-GOV × Liferay — imagem com os componentes instalados
#
# Estende a imagem oficial Liferay Portal CE 7.4.3.132-ga132 e instala os
# bundles OSGi Winnex (Tracer-MED + Tracer-GOV) DURANTE o build.
#
# Os JARs são copiados para /opt/liferay/deploy (o diretório que o
# fileinstall do Liferay monitora). O entrypoint da imagem preserva esse
# diretório, então os bundles são instalados no primeiro boot.
#
# Build:
#   docker build -t tracer-liferay:1.0.0 -f liferay/docker/Dockerfile liferay/docker
#
# Os portlets são isolados: Tracer-MED e Tracer-GOV são bundles separados
# (com.winnex.tracermed / com.winnex.tracergov) e adicionados a páginas
# próprias após o primeiro boot.

FROM liferay/portal:7.4.3.132-ga132

# ---------------------------------------------------------------------------
# 1. OSGi bundles Winnex (Tracer-MED + Tracer-GOV, isolados)
#    --chown=liferay:liferay: o auto-deploy do Liferay roda como usuário
#    "liferay"; sem o owner correto o deploy falha com "Unable to write".
# ---------------------------------------------------------------------------
# Tracer-MED (motor + ponte + portlet)
COPY --chown=liferay:liferay artifacts/com.winnex.madhava.api-1.0.0.jar       /opt/liferay/deploy/
COPY --chown=liferay:liferay artifacts/com.winnex.madhava.service-1.0.0.jar   /opt/liferay/deploy/
COPY --chown=liferay:liferay artifacts/com.winnex.tracermed-1.0.0.jar         /opt/liferay/deploy/

# Tracer-GOV (API + ponte + portlet)
COPY --chown=liferay:liferay artifacts/com.winnex.tracergov.api-1.0.0.jar     /opt/liferay/deploy/
COPY --chown=liferay:liferay artifacts/com.winnex.tracergov.service-1.0.0.jar /opt/liferay/deploy/
COPY --chown=liferay:liferay artifacts/com.winnex.tracergov-1.0.0.jar         /opt/liferay/deploy/
