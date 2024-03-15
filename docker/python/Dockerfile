FROM python:3.10

WORKDIR /apps/IS_ontology

# run apt, yum, etc before copying any files to prevent creating layers that can be cached
# thereis no netcat in this image, we need nc for control of postgres start control in production
RUN apt update && apt install -y netcat-openbsd

RUN --mount=type=cache,target=/root/.cache/pip python3 -m pip install --upgrade pip
COPY ./IS_ontology/requirements.txt /apps/IS_ontology/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

COPY ./nltk_data /root/nltk_data

COPY ./IS_ontology /apps/IS_ontology

ENTRYPOINT ["/apps/IS_ontology/entrypoint.sh"]

