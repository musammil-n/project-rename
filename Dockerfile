FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable for Chrome binary
ENV CHROME_BIN=/usr/bin/chromium

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your bot code
COPY . /app
WORKDIR /app

# Start the bot
CMD ["python", "bot.py"]
