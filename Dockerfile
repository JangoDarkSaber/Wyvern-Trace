# Start with a lightweight Python 3.12 image
FROM python:3.12-slim

# Prevent Python from writing pyc files and keep stdout unbuffered for Streamlit logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies: OpenJDK 21 (for Ghidra 11+), wget, and unzip
RUN apt-get update && apt-get install -y \
    openjdk-21-jdk \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set up the Ghidra environment
WORKDIR /opt
# Note: Update this URL to the exact Ghidra release zip you wish to use
RUN wget -q https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.1.2_build/ghidra_11.1.2_PUBLIC_20240709.zip -O ghidra.zip \
    && unzip -q ghidra.zip \
    && rm ghidra.zip \
    && mv ghidra_* ghidra

# Add Ghidra headless to the system path so Python can call it easily
ENV PATH="/opt/ghidra/support:${PATH}"

# Set up the Python application workspace
WORKDIR /app

# Install Python dependencies first (leverages Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create the workspace directories for the host volume mounts
RUN mkdir -p /workspace/uploads /workspace/projects

# Copy the rest of the application code
COPY . .

# Expose Streamlit's default port
EXPOSE 8501

# Start the Streamlit dashboard
CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]