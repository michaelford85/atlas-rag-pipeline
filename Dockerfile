# Base image
FROM python:3.11-slim

# Set noninteractive mode to silence debconf warnings
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# --- 1️⃣ Install required packages (as root) ---
RUN apt-get update && \
    apt-get install -y --no-install-recommends vim bash curl && \
    rm -rf /var/lib/apt/lists/*

# --- 2️⃣ Create a non-root user ---
RUN useradd -ms /bin/bash appuser

# --- 3️⃣ Copy project files (including .env.vault) ---
# The .env.vault file and scripts will now be copied correctly
COPY .env.vault .env.vault
COPY . .


# --- 4️⃣ Fix ownership for non-root user ---
RUN chown -R appuser:appuser /app

# --- 5️⃣ Install Python dependencies ---
RUN pip install --no-cache-dir -r requirements.txt

# --- 6️⃣ Switch to non-root user ---
USER appuser

# --- 7️⃣ Default command ---
CMD ["bash"]