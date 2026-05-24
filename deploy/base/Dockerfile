FROM python:3.11-slim

WORKDIR /workspace

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && update-ca-certificates \
    && git config --system http.sslCAInfo /etc/ssl/certs/ca-certificates.crt \
    && apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt clearml-agent

COPY . .
RUN pip install --no-cache-dir -e pkgs/core -e pkgs/tabular

CMD ["sh", "-lc", "clearml-agent daemon --queue \"$CLEARML_AGENT_QUEUE\""]
