FROM python:3.9.16 AS base

# Set working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt /app/requirements.txt

# Upgrade pip
RUN pip install --upgrade pip

# Install Python packages from the requirements file
RUN pip install -r /app/requirements.txt

# Set port
EXPOSE 5000

# Run the entrypoint script on container startup
ENTRYPOINT ["/entrypoint.sh"]
