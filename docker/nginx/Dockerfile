FROM nginx:1.17.4-alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY ./docker/nginx/IS_ontology.conf /etc/nginx/conf.d
