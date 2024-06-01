# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV VOSK_SERVER_INTERFACE=0.0.0.0
ENV VOSK_SERVER_PORT=2700
ENV VOSK_MODEL_PATH=/opt/vosk-model
ENV VOSK_SPK_MODEL_PATH=/opt/vosk-spk-model
ENV VOSK_SAMPLE_RATE=8000
ENV VOSK_ALTERNATIVES=0
ENV VOSK_SHOW_WORDS=true

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip

# Download and extract the English model
RUN wget -O /opt/vosk-model-en.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip && \
    unzip /opt/vosk-model-en.zip -d /opt && \
    mv /opt/vosk-model-small-en-us-0.15 /opt/vosk-model-en

# Download and extract the Vietnamese model
RUN wget -O /opt/vosk-model-vi.zip https://alphacephei.com/vosk/models/vosk-model-small-vi-0.22.zip && \
    unzip /opt/vosk-model-vi.zip -d /opt && \
    mv /opt/vosk-model-small-vi-0.22 /opt/vosk-model-vi

# Copy the server script
COPY websocket/asr_server.py /opt/vosk-server/websocket/asr_server.py

# Install Python dependencies
RUN pip install websockets vosk requests

# Expose the port
EXPOSE 2700

# Run the server
CMD ["python3", "/opt/vosk-server/websocket/asr_server.py"]