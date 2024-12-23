# Use the official Freqtrade image as a parent image
FROM freqtradeorg/freqtrade:stable

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app
COPY ga.json /app

# Install any additional Python packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 8080

# Define environment variable
ENV NAME World

# Run main.py when the container launches
CMD ["python", "main.py", "--config", "ga.json"]