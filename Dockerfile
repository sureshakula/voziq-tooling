FROM codercom/code-server:latest

USER root

# Install Python + Node.js (for Claude Code)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-full \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code globally
RUN npm install -g @anthropic-ai/claude-code

# Create venv owned by coder user (UID 1000)
RUN python3 -m venv /opt/venv \
    && chown -R 1000:1000 /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Startup script in /etc so it's NOT shadowed by /home/coder bind mount
RUN mkdir -p /etc/entrypoint.d
COPY setup-workspace.sh /etc/entrypoint.d/setup-workspace.sh
RUN chmod +x /etc/entrypoint.d/setup-workspace.sh

# Override ENTRYPOINTD to our non-shadowed location
ENV ENTRYPOINTD=/etc/entrypoint.d

USER 1000
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8080
# Use the official entrypoint (already in the base image at /usr/bin/entrypoint.sh)
# It runs fixuid -> entrypoint.d scripts -> dumb-init code-server
ENTRYPOINT ["/usr/bin/entrypoint.sh", "--bind-addr", "0.0.0.0:8080", "--auth", "none", "/home/coder/workspace"]
