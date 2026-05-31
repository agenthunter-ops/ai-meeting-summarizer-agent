from pathlib import Path


SAMPLE_TRANSCRIPT = (
    "Neha: Abhishek, please create the first working POC by Friday. "
    "Jeevan, please validate the logging fields by Wednesday. "
    "Aditya: The biggest risk is latency."
)


class TranscriptionService:
    def transcribe(self, audio_path: Path) -> str:
        if not audio_path.exists():
            raise FileNotFoundError("Audio file was not saved.")

        return SAMPLE_TRANSCRIPT
