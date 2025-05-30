# Use a slim Python base image for smaller size, based on Debian Bookworm
FROM python:3.10-slim-bookworm

# Install FFmpeg and its dependencies, including fonts for drawtext filter
# libsm6 and libxext6 are common dependencies for some FFmpeg builds
# fontconfig and fonts-dejavu-core provide the DejaVuSans font used in the bot
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libsm6 \
        libxext6 \
        fontconfig \
        fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/* && \
    fc-cache -f -v # Rebuild font cache after installing fonts

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker's build cache
COPY requirements.txt .

# Install Python dependencies from requirements.txt
# --no-cache-dir: Prevents pip from storing cached downloads, reducing image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your bot code into the container
COPY . .

# Command to start your bot when the container runs
# This will execute the bot.py script
CMD ["python", "bot.py"]
