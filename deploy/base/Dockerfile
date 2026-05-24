FROM python:3.11-slim

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt clearml-agent

COPY . .
RUN pip install --no-cache-dir -e pkgs/core -e pkgs/tabular

CMD ["sh", "-lc", "clearml-agent daemon --queue \"$CLEARML_AGENT_QUEUE\""]
