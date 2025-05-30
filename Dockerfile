# Use a slim Python base image for smaller size
FROM python:3.10-slim-bookworm

# Install FFmpeg and its dependencies
# 'bookworm' (Debian 12) uses 'ffmpeg' package name.
# We're also cleaning up apt lists to keep the image size down.
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory for your application inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker's build cache
COPY requirements.txt .

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your bot code into the container
COPY . .

# Command to start your bot when the container runs
CMD ["python", "bot.py"]
