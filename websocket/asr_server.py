#!/usr/bin/env python3

import json
import os
import sys
import asyncio

import requests
import websockets
import concurrent.futures
import logging

import py3langid as langid
from vosk import Model, SpkModel, KaldiRecognizer


def process_chunk(rec, message):
    rec.AcceptWaveform(message)
    result = rec.Result()
    if rec.FinalResult():
        stop = True
    else:
        stop = False
    return result, stop


# def detect_language(audio_data):
#     # Initialize recognizers for both languages
#     rec_en = KaldiRecognizer(en_model, args.sample_rate)
#     rec_vi = KaldiRecognizer(vi_model, args.sample_rate)
#
#     # Use a short sample for language detection
#     sample_size = min(8000, len(audio_data))  # Use the first 0.5 seconds (8000 samples at 16000 Hz)
#     sample_data = audio_data[:sample_size]
#
#     rec_en.AcceptWaveform(sample_data)
#     rec_vi.AcceptWaveform(sample_data)
#
#     result_en = json.loads(rec_en.Result())
#     result_vi = json.loads(rec_vi.Result())
#
#     confidence_en = result_en.get('confidence', 0)
#     confidence_vi = result_vi.get('confidence', 0)
#
#     if confidence_en > confidence_vi:
#         logging.info("detect_language en")
#
#         return 'en'
#     else:
#         logging.info("detect_language vi")
#
#         return 'en'

def detect_language(audio_data):
    # Detect language using langid
    langid.set_languages(['en', 'vi'])
    lid_result = langid.classify(audio_data.decode('utf-8', errors='ignore'))
    detected_lang = lid_result[0]
    logging.info(f"Detected language: {detected_lang}")
    return detected_lang


async def recognize(websocket, path):
    global vi_model
    global en_model
    global spk_model
    global args
    global pool

    loop = asyncio.get_running_loop()
    rec = None
    phrase_list = None
    sample_rate = args.sample_rate
    show_words = args.show_words
    max_alternatives = args.max_alternatives
    session_id = ''
    user_id = ''

    logging.info('Connection from %s', websocket.remote_address);
    audio_data = b''
    while True:

        message = await websocket.recv()

        if isinstance(message, str) and 'end' in message:
            break

        # Load configuration if provided
        if isinstance(message, str) and 'config' in message:
            jobj = json.loads(message)['config']
            logging.info("Config %s", jobj)
            if 'sample_rate' in jobj:
                sample_rate = float(jobj['sample_rate'])
            if 'words' in jobj:
                show_words = bool(jobj['words'])
            if 'max_alternatives' in jobj:
                max_alternatives = int(jobj['max_alternatives'])
            continue

        if isinstance(message, str) and 'session' in message:
            jobj = json.loads(message)['session']
            logging.info("Session %s", jobj)
            if 'session_id' in jobj:
                session_id = jobj['session_id']
            if 'user_id' in jobj:
                user_id = jobj['user_id']
            continue

        # Accumulate audio data
        if isinstance(message, bytes):
            audio_data += message

    logging.info("đến đây r")

    # Detect language using a short initial sample
    detected_lang = detect_language(audio_data)

    if detected_lang == 'vi':
        current_model = vi_model
    else:
        current_model = en_model

    # Create the recognizer, word list is temporary disabled since not every model supports it

    rec = KaldiRecognizer(current_model, sample_rate)
    rec.SetWords(show_words)
    rec.SetMaxAlternatives(max_alternatives)
    # rec.SetSpkModel(spk_model)

    response, stop = await loop.run_in_executor(pool, process_chunk, rec, audio_data)
    await websocket.send(response)
    if stop:
        send_to_llm(session_id, user_id, response)
        await websocket.close()


def send_to_llm(session_id, user_id, result):
    global args
    try:
        result_json = json.loads(result)
        prompt_text = result_json.get('text', '')
        logging.info(f" send result to server: {prompt_text}")
        payload = {'prompt': prompt_text}

        url = f'{args.llm_host}/v1/webrtc/{session_id}/{user_id}'
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info(f"Successfully sent result to server: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending result to server: {e}")


async def start():
    global vi_model
    global en_model
    global spk_model
    global args
    global pool

    # Enable loging if needed
    #
    # logger = logging.getLogger('websockets')
    # logger.setLevel(logging.INFO)
    # logger.addHandler(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO)

    args = type('', (), {})()

    args.interface = os.environ.get('VOSK_SERVER_INTERFACE', '0.0.0.0')
    args.port = int(os.environ.get('VOSK_SERVER_PORT', 2700))
    args.en_model_path = os.environ.get('VOSK_EN_MODEL_PATH', '/opt/vosk-model-en')
    args.vi_model_path = os.environ.get('VOSK_VI_MODEL_PATH', '/opt/vosk-model-vi')
    args.spk_model_path = os.environ.get('VOSK_SPK_MODEL_PATH')
    args.sample_rate = float(os.environ.get('VOSK_SAMPLE_RATE', 16000))
    args.max_alternatives = int(os.environ.get('VOSK_ALTERNATIVES', 0))
    args.show_words = bool(os.environ.get('VOSK_SHOW_WORDS', True))
    args.llm_host = bool(os.environ.get('LLM_HOST', True))

    if len(sys.argv) > 1:
        args.model_path = sys.argv[1]

    # Gpu part, uncomment if vosk-api has gpu support
    #
    # from vosk import GpuInit, GpuInstantiate
    # GpuInit()
    # def thread_init():
    #     GpuInstantiate()
    # pool = concurrent.futures.ThreadPoolExecutor(initializer=thread_init)
    en_model = Model(args.en_model_path)
    vi_model = Model(args.vi_model_path)

    spk_model = SpkModel(args.spk_model_path)

    pool = concurrent.futures.ThreadPoolExecutor((os.cpu_count() or 1))

    async with websockets.serve(recognize, args.interface, args.port, max_size=None):
        await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(start())
