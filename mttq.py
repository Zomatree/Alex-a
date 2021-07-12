import io
import json
import wave
import audioop
from threading import Thread
import time
from discord.opus import Decoder
from paho.mqtt.client import Client

PLAY_BYTES = "hermes/audioServer/{}/playBytes/+"
PLAY_FINISHED = "hermes/audioServer/{}/playFinished"
AUDIO_FRAME = "hermes/audioServer/{}/audioFrame"
CHANNELS = 1
FRAME_RATE = 16000
CHUNK = int(FRAME_RATE * 20 / 1000)
SAMPLE_WIDTH = 2
PLAYER_FRAMES = 256

class MQTTClient:
    def __init__(self, config):
        self.config = config
        self.mqtt = Client()

        self.connect()

    def connect(self):
        self.mqtt.connect(self.config["mqtt"]["host"], self.config["mqtt"]["port"])

    def start(self):
        self.mqtt.loop_forever()

    def stop(self):
        self.mqtt.disconnect()

class AudioPlayer(MQTTClient):
    def __init__(self, config, play_func):
        super().__init__(config)

        self.play_func = play_func
        play_bytes = PLAY_BYTES.format(self.config["rhasspy"]["site"])
        print(play_bytes)
        self.mqtt.subscribe(play_bytes)
        self.mqtt.message_callback_add(play_bytes, self.on_play_bytes)

    def on_play_bytes(self, client, userdata, message):
        request_id = message.topic.split("/")[4]

        with io.BytesIO(message.payload) as wav_buffer:
            try:
                with wave.Wave_read(wav_buffer) as wav:
                    data = wav.readframes(PLAYER_FRAMES)

                    while data:
                        upsampled, _ = audioop.ratecv(data, SAMPLE_WIDTH, CHANNELS, FRAME_RATE, Decoder.SAMPLING_RATE, None)
                        stero = audioop.tostereo(upsampled, SAMPLE_WIDTH, 1, 1)
                        self.play_func(stero)
                        data = wav.readframes(PLAYER_FRAMES)

                    play_finished_topic = PLAY_FINISHED.format(self.config["rhasspy"]["site"])
                    play_finished_message = json.dumps({"id": request_id, "siteId": self.config["rhasspy"]["site"]})
                    self.mqtt.publish(play_finished_topic, play_finished_message)
            except EOFError:
                pass

    def start(self):
        Thread(target=super().start).start()

class AudioRecorder(MQTTClient):
    def __init__(self, config, stream: io.BytesIO):
        super().__init__(config)
        self.stream = stream

    def start(self):
        Thread(target=self.send_audio_frames).start()

    def publish_frames(self, frames):
        with io.BytesIO() as wav_buffer:
            with wave.open(wav_buffer, "wb") as wav:
                wav.setnchannels(CHANNELS)
                wav.setsampwidth(SAMPLE_WIDTH)
                wav.setframerate(FRAME_RATE)
                wav.writeframes(frames)

            audio_frame_topic = AUDIO_FRAME.format(self.config["rhasspy"]["site"])
            audio_frame_message = wav_buffer.getvalue()
            self.mqtt.publish(audio_frame_topic, audio_frame_message)

    def send_audio_frames(self):
        while True:
            frames = self.stream.read(CHUNK)
            self.publish_frames(frames)
            time.sleep(.2)
