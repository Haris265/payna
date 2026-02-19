# Use the Python 3.10 base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /payna

# Copy the requirements file to the container
COPY requirements.txt /payna/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . /payna/



