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

# Copy backend dependency files
COPY backend/pyproject.toml ./

# Install Python dependencies from pyproject.toml
RUN uv pip install --system .

# Copy backend application files
COPY backend/ ./backend/

# Create necessary directories
RUN mkdir -p .session data/conversations/raw data/embeddings exports certificates

# Set permissions for data directories
RUN chmod -R 755 data exports .session certificates

# Create a non-root user for security
RUN useradd -m -u 1000 telegram && chown -R telegram:telegram /app
USER telegram

# Set Python path to include backend
ENV PYTHONPATH=/app/backend:$PYTHONPATH

# Default command - discover available chats
CMD ["python", "backend/scripts/telegram_csv_downloader.py", "--discover-only"]

