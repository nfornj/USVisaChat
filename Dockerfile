FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH (it's installed to ~/.local/bin)
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies from pyproject.toml
RUN uv pip install --system .

# Copy application files
COPY *.py ./

# Create necessary directories
RUN mkdir -p .session data/conversations/raw data/embeddings exports

# Set permissions for data directories
RUN chmod -R 755 data exports .session

# Create a non-root user for security
RUN useradd -m -u 1000 telegram && chown -R telegram:telegram /app
USER telegram

# Default command - discover available chats
CMD ["python", "telegram_csv_downloader.py", "--discover-only"]

