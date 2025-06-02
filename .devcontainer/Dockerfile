# Use Python 3.11 as the base image
FROM mcr.microsoft.com/devcontainers/python:3.11

# Install essential dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up the workspace directory
WORKDIR /workspace

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python utilities
RUN pip install --upgrade pip \
    && pip install black pylint

# Create a non-root user if not already present
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN if ! id -u $USERNAME >/dev/null 2>&1; then \
    groupadd --gid $USER_GID $USERNAME \
    && useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && mkdir -p /home/$USERNAME/.vscode-server/extensions \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME; \
    fi
