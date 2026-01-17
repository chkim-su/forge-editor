FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tmux \
    git \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir pyyaml

# Set up workspace
WORKDIR /workspace

# Copy forge plugin
COPY . /workspace/forge

# Copy mock Claude CLI
COPY tests/docker/mock-claude /usr/local/bin/claude
RUN chmod +x /usr/local/bin/claude

# Create test user for isolation
RUN useradd -m -s /bin/bash testuser && \
    chown -R testuser:testuser /workspace

# Set up Claude plugin environment
ENV CLAUDE_PLUGIN_ROOT=/workspace/forge
ENV CLAUDE_WORKING_DIR=/workspace/test

# Create test workspace directory
RUN mkdir -p /workspace/test/.claude/local && \
    chown -R testuser:testuser /workspace/test

USER testuser
WORKDIR /workspace/test

# Entry point
COPY --chown=testuser:testuser tests/docker/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
