# syntax = docker/dockerfile
FROM thuxit/upython:3.13-16-uv-bookworm AS production-stage
ARG APP_USER=www-data
#RUN \
#  apt-get update \
#  && DEPS=" \
#    telnet \
#    iproute2 \
#    net-tools \
#    iputils-ping \
#  " \
#  && seq 1 8 | xargs -I{} mkdir -p /usr/share/man/man{} \
#  && apt-get update && apt-get install -y --no-install-recommends $DEPS \
#  && rm -rf /var/lib/apt/lists/* \
#  && mv /root/.local/bin/uv /usr/local/bin/uv \
#  && chmod +x /usr/local/bin/uv
COPY pyproject.toml uv.lock /code/
WORKDIR /code/
ENV UV_SYSTEM_PYTHON=1
ENV UV_PROJECT_ENVIRONMENT=/usr/local
RUN uv sync --index-strategy unsafe-best-match
#RUN uv pip install --no-cache --prerelease=allow --index-strategy unsafe-best-match --requirement pyproject.toml

COPY . /code/

#  --no-cache-dir --extra-index-url https://pypi.thux.dev/simple/ -r /requirements.txt


# uWSGI will listen on this port
EXPOSE 8000

ENV DJANGO_SETTINGS_MODULE=core.settings
ENV ENV=dev
ENV DATABASE_URL='sqlite:////tmp/db.sqlite'

RUN python /code/manage.py check \
  && python /code/manage.py collectstatic --noinput --link \
  && chown -R ${APP_USER} /code/core/settings \
  && mv uwsgi.ini /etc

USER ${APP_USER}:${APP_USER}


# Uncomment after creating your docker-entrypoint.sh
#ENTRYPOINT ["/bin/bash"]

CMD ["uwsgi", "--ini=/etc/uwsgi.ini", "--show-config"]
