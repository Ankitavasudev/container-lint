# Deliberately bad sample used by the README and the CI smoke test.
# Run `container-lint examples/Dockerfile` to see every rule fire.
FROM ubuntu
RUN apt-get install curl
RUN apt-get update && apt-get upgrade -y
ADD https://example.com/tools.tgz /opt/tools.tgz
COPY . .
EXPOSE 22
CMD python app.py
