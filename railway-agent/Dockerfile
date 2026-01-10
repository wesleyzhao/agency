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

# Create non-root user (Claude CLI refuses bypassPermissions as root)
RUN useradd -m -s /bin/bash agent

# Create workspace directory with proper ownership
RUN mkdir -p /workspace && chown -R agent:agent /workspace

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Give agent user ownership of app directory
RUN chown -R agent:agent /app

# Switch to non-root user
USER agent

# Set environment
ENV PYTHONUNBUFFERED=1

# Run the agent
CMD ["python", "main.py"]
