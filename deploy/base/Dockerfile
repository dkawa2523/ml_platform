FROM python:3.11-slim

WORKDIR /workspace

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    PIP_CERT=/etc/ssl/certs/ca-certificates.crt

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git libgomp1 \
    && update-ca-certificates \
    && git config --system http.sslCAInfo /etc/ssl/certs/ca-certificates.crt \
    && apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt clearml-agent

COPY . .
RUN pip install --no-cache-dir -e pkgs/core -e "pkgs/tabular[gbm]"

CMD ["sh", "-lc", "printf 'agent.package_manager.system_site_packages: true\\n' > /tmp/clearml-agent.conf && clearml-agent --config-file /tmp/clearml-agent.conf daemon --queue \"$CLEARML_AGENT_QUEUE\""]
