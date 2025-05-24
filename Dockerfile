FROM python:3.10-slim

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your bot code
COPY . /app
WORKDIR /app

# Start the bot
CMD ["python", "bot.py"]
