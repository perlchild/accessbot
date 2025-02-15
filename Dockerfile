FROM continuumio/miniconda3

ENV ERRBOT_DIR=/errbot
ENV SDM_DOCKERIZED=true

RUN mkdir -p $ERRBOT_DIR
WORKDIR $ERRBOT_DIR

COPY requirements/common.txt ./requirements.txt
RUN pip install \
      --no-cache-dir \
      --disable-pip-version-check \
      -r requirements.txt
RUN pip install errbot[slack]

COPY data ./data
COPY config.py .
COPY errbot-slack-bolt-backend ./errbot-slack-bolt-backend

RUN mkdir -p plugins/sdm
COPY plugins/sdm ./plugins/sdm/

ENTRYPOINT [ "errbot" ]
