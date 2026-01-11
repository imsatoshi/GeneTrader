# Use the official Freqtrade image as a parent image
# Updated for Python 3.12 compatibility (Issue #12)
FROM freqtradeorg/freqtrade:stable

# Set the working directory in the container
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install any additional Python packages specified in requirements.txt
# Use --break-system-packages for Python 3.12+ if needed in externally-managed environments
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy the rest of the application
COPY . /app

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV NAME=GeneTrader
ENV PYTHONUNBUFFERED=1

# Run main.py when the container launches
# Use --optimizer flag to choose between 'genetic' (default) or 'optuna'
CMD ["python", "main.py", "--config", "ga.json"]