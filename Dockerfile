FROM codercom/code-server:latest

USER root

# Install Python + Node.js (for Claude Code)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code globally
RUN npm install -g @anthropic-ai/claude-code

# Create venv and install AIPass
WORKDIR /app
COPY . .
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install -e .
RUN chown -R 1000:1000 /opt/venv

# Switch back to coder user
USER coder

# venv on PATH for coder too
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8080

ENTRYPOINT ["code-server", "--auth", "none", "--bind-addr", "0.0.0.0:8080", "/app"]
