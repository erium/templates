from datetime import datetime
import lameenc
import logging
from pathlib import Path
import queue
import threading


class AudioProcessor:
    def __init__(
        self,
        samplerate: int,
        session_id: str,
        path: Path = Path(__file__).resolve().parent / "../audio",
    ):
        """
        Audio manager to manage audio recording's IO.

        Args:
            samplerate (int): Sample rate of audio recording (e.g. 16000).
            path (Path, optional): Path to save audio files to. Defaults to app/audio/.
        """
        # setup logger
        self.logger = logging.getLogger(__name__)

        self.logger.debug(
            f"AudioProcessor for session {session_id}: samplerate={samplerate}"
        )

        # setup audio recording
        self.is_recording = True
        self.mp3_stream = None
        self.queue = queue.Queue()
        self.path = path
        self.session_id = session_id
        self.samplerate = int(samplerate)
        self.encoder = self._encoder()

        # ensure export path exists
        self.path.mkdir(parents=True, exist_ok=True)

        # start encoding thread
        self.encoding_thread = threading.Thread(target=self._encoding_thread)
        self.encoding_thread.start()

    def export_mp3(self) -> Path:
        """
        Stops the audio processing thread and exports the audio file.
        """
        self.is_recording = False
        try:
            self.logger.debug("Joining encoding thread...")
            self.encoding_thread.join()
        except RuntimeError:
            self.logger.error("Encoding thread failed to join")
        else:
            self.logger.debug("Encoding thread joined")

        self._save_stream()

        return self.filepath if self.filepath else None

    def add_chunk(self, chunk: bytes):
        """
        Add audio data to the queue.

        Args:
            chunk (bytes): Audio data to add to the queue.
        """
        # add chunk to queue
        self.queue.put(chunk)

    def _encoder(self):
        """
        Create a lame encoder.

        Returns:
            Encoder: Lame encoder with bitrate 128, samplerate as specified, 1 channel and quality 7 (fastest).
        """
        self.logger.debug("Creating encoder")
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(128)
        encoder.set_in_sample_rate(self.samplerate)
        encoder.set_channels(1)
        encoder.set_quality(7)

        return encoder

    def _encoding_thread(self):
        """
        Thread to encode PCM audio data from the queue to mp3.
        Appends the mp3 data to the mp3 stream.
        """
        self.logger.debug("Starting encoding thread")

        while True:
            if not self.is_recording and self.queue.empty():
                break

            try:
                # get chunk from queue
                chunk = self.queue.get(timeout=1)

                # encode that chunk as mp3
                mp3_data = self.encoder.encode(chunk)

                if self.mp3_stream is None:
                    self.mp3_stream = mp3_data
                else:
                    self.mp3_stream += mp3_data

            except queue.Empty:
                continue

            except Exception as e:
                self.logger.error(f"Error converting PCM chunk to mp3: {e}")
                continue

        # finalize stream
        self.mp3_stream += self.encoder.flush()

    def _save_stream(self):
        self.logger.debug("Saving mp3 stream")
        self.logger.debug(f"mp3 stream size: {len(self.mp3_stream)}")

        # create filename
        now = datetime.strftime(datetime.now(), "%Y-%m-%d_%H-%M-%S%f")
        self.filepath = self.path / f"{now}_{self.session_id}.mp3"
        try:
            # write file
            with open(self.filepath, "wb") as f:
                f.write(self.mp3_stream)
        except Exception as e:
            self.logger.error(f"Error saving audio file: {e}")
            self.filepath = None
        else:
            self.logger.debug(f"Saved audio file to {self.filepath}")
