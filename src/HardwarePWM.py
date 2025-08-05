import os


class HardwarePWM:
    def __init__(
        self,
        channel: int,
        chip: int = 0,
        frequency_hz: float = 50.0
    ):
        self.chip = chip
        self.channel = channel
        self.base_path = f"/sys/class/pwm/pwmchip{chip}"
        self.channel_path = os.path.join(self.base_path, f"pwm{channel}")
        self.period_ns = int(1000000 / frequency_hz) * 1000

        if not os.path.isdir(self.base_path):
            raise RuntimeError(f"PWM chip {chip} does not exist at {self.base_path}")

        if not os.path.isdir(self.channel_path):
            self._export_channel()

        # Open duty_cycle file for efficient repeated writes
        self.duty_fd = open(os.path.join(self.channel_path, "duty_cycle"), "w")

    def _export_channel(self):
        export_path = os.path.join(self.base_path, "export")
        with open(export_path, "w") as f:
            f.write(str(self.channel))

    def _write_once(self, name: str, value):
        path = os.path.join(self.channel_path, name)
        with open(path, "w") as f:
            f.write(str(value))

    def setup(self, pulse_width: int):
        self._write_once("period", self.period_ns)
        self.set_pulse_width(pulse_width)
        self._write_once("enable", 1)

    def set_pulse_width(self, pulse_width: int):
        """Set the PWM pulse width in microseconds (e.g., 1000–2000)."""
        duty_ns = pulse_width * 1000
        self.duty_fd.seek(0)
        self.duty_fd.write(str(duty_ns))
        self.duty_fd.flush()

    def disable(self):
        self._write_once("enable", 0)

    def close(self):
        self.duty_fd.close()
        # Intentionally not unexporting — leave it available for other users

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
