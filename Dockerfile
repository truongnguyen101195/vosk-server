# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV VOSK_SERVER_INTERFACE=0.0.0.0
ENV VOSK_SERVER_PORT=2700
ENV VOSK_MODEL_PATH=/opt/vosk-model
ENV VOSK_SPK_MODEL_PATH=/opt/vosk-model-spk
ENV VOSK_EN_MODEL_PATH=/opt/vosk-model-en
ENV VOSK_VI_MODEL_PATH=/opt/vosk-model-vi
ENV VOSK_SAMPLE_RATE=16000
ENV VOSK_ALTERNATIVES=0
ENV VOSK_SHOW_WORDS=true

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    ca-certificates

RUN mkdir -p /opt/vosk-model

# Download and extract the English language model
RUN wget -O /opt/vosk-model-en.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip && \
    unzip /opt/vosk-model-en.zip -d /opt/vosk-model-en && \
    mv /opt/vosk-model-en/vosk-model-small-en-us-0.15/* /opt/vosk-model-en/ && \
    rmdir /opt/vosk-model-en/vosk-model-small-en-us-0.15

# Download and extract the Vietnamese model
RUN wget -O /opt/vosk-model/vosk-model-small-vn-0.4.zip https://alphacephei.com/vosk/models/vosk-model-small-vn-0.4.zip && \
    unzip /opt/vosk-model/vosk-model-small-vn-0.4.zip -d /opt/vosk-model-vi && \
    mv /opt/vosk-model-vi/vosk-model-small-vn-0.4/* /opt/vosk-model-vi && \
    rmdir /opt/vosk-model-vi/vosk-model-small-vn-0.4

# Download and extract the Speaker model
RUN wget -O /opt/vosk-model-spk.zip https://alphacephei.com/vosk/models/vosk-model-spk-0.4.zip && \
    unzip /opt/vosk-model-spk.zip -d /opt/vosk-model-spk && \
    mv /opt/vosk-model-spk/vosk-model-spk-0.4/* /opt/vosk-model-spk/ && \
    rmdir /opt/vosk-model-spk/vosk-model-spk-0.4

# Copy the server script
COPY websocket/asr_server.py /opt/vosk-server/websocket/asr_server.py

# Install Python dependencies
RUN pip install websockets vosk requests

# Expose the port
EXPOSE 2700

# Run the server
CMD ["python3", "/opt/vosk-server/websocket/asr_server.py"]