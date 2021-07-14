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
SLEEP_TIME = Decoder.FRAME_LENGTH // 1000

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
        self.mqtt.subscribe(play_bytes)
        self.mqtt.message_callback_add(play_bytes, self.on_play_bytes)
        self.play_finished_topic = PLAY_FINISHED.format(self.config["rhasspy"]["site"])

    def on_play_bytes(self, client, userdata, message):
        request_id = message.topic.split("/")[4]
        
        upsampled, _ = audioop.ratecv(message.payload, SAMPLE_WIDTH, CHANNELS, FRAME_RATE, Decoder.SAMPLING_RATE, None)
        stero = audioop.tostereo(upsampled, SAMPLE_WIDTH, 1, 1)
        
        f = io.BytesIO(stero)
        audio = f.read(Decoder.FRAME_SIZE)

        while audio:
            start_time = time.time()
            self.play_func(audio)
            audio = f.read(Decoder.FRAME_SIZE)
            time.sleep(max(0, SLEEP_TIME - (time.time() - start_time)))

        play_finished_message = json.dumps({"id": request_id, "siteId": self.config["rhasspy"]["site"]})
        self.mqtt.publish(self.play_finished_topic, play_finished_message)

    def start(self):
        Thread(target=super().start).start()

# python doesnt have any way to pass by ref so im using a one length list as my mutable with the audio inside

class AudioRecorder(MQTTClient):
    def __init__(self, config, stream: list[bytes]):
        super().__init__(config)
        self.stream = stream
        self.audio_frame_topic = AUDIO_FRAME.format(self.config["rhasspy"]["site"])

    def start(self):
        Thread(target=self.send_audio_frames).start()

    def send_audio_frames(self):
        while True:
            frames = self.stream[0]
            print(frames)
            self.mqtt.publish(self.audio_frame_topic, frames)
