import unittest
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Pipeline"))
from Pipeline.audio_pipeline import AudioPipeline, SAMPLE_RATE


class _AlwaysSpeechVad:
    def is_speech(self, frame, sample_rate):
        return True


class AudioNoiseReductionTests(unittest.TestCase):
    def make_pipeline(self):
        pipeline = AudioPipeline.__new__(AudioPipeline)
        pipeline.vad = _AlwaysSpeechVad()
        pipeline.noise_reduction_enabled = True
        pipeline.noise_gate_multiplier = 1.8
        pipeline.ambient_rms = 100.0
        pipeline._ambient_samples = 10
        pipeline.highpass_cutoff_hz = 100.0
        return pipeline

    @staticmethod
    def frame_with_level(level):
        return np.full(480, level, dtype=np.int16).tobytes()

    def test_adaptive_gate_rejects_noise_but_accepts_louder_speech(self):
        pipeline = self.make_pipeline()

        self.assertFalse(pipeline._is_command_speech(self.frame_with_level(120)))
        self.assertTrue(pipeline._is_command_speech(self.frame_with_level(300)))

    def test_highpass_filter_reduces_low_frequency_rumble(self):
        pipeline = self.make_pipeline()
        pipeline._ambient_samples = 0
        time_axis = np.arange(SAMPLE_RATE, dtype=np.float32) / SAMPLE_RATE
        rumble = np.sin(2 * np.pi * 40 * time_axis).astype(np.float32)

        filtered = pipeline._reduce_noise(rumble)

        self.assertLess(
            np.sqrt(np.mean(filtered * filtered)),
            np.sqrt(np.mean(rumble * rumble)) * 0.3,
        )


if __name__ == "__main__":
    unittest.main()
