FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for claude-agent-sdk)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI (required for claude-agent-sdk)
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user for running Claude CLI
# Claude CLI refuses --dangerously-skip-permissions when running as root
RUN useradd -m -s /bin/bash agent && \
    mkdir -p /workspace && \
    chown -R agent:agent /workspace

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
RUN chown -R agent:agent /app

# Set environment
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/agent

# Switch to non-root user
USER agent

# Run the agent
CMD ["python", "main.py"]
