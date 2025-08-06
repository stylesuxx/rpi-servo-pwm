import os
import time


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

        self._wait_for_permissions("duty_cycle", timeout=1.0)
        self.duty_fd = open(os.path.join(self.channel_path, "duty_cycle"), "w")

    def _export_channel(self) -> None:
        export_path = os.path.join(self.base_path, "export")
        with open(export_path, "w") as f:
            f.write(str(self.channel))

    def _wait_for_permissions(self, filename: str, timeout: float = 1.0) -> None:
        path = os.path.join(self.channel_path, filename)
        start = time.time()
        while time.time() - start < timeout:
            if os.access(path, os.W_OK):
                return
            time.sleep(0.05)

        raise PermissionError(f"Timeout waiting for write access to {path}")

    def _write_once(self, name: str, value) -> None:
        path = os.path.join(self.channel_path, name)
        with open(path, "w") as f:
            f.write(str(value))

    def setup(self, pulse_width_ms: int) -> None:
        self._write_once("period", self.period_ns)
        self.set_pulse_width(pulse_width_ms)
        self._write_once("enable", 1)

    def set_pulse_width(self, pulse_width_ms: int) -> None:
        """Set the PWM pulse width in microseconds (e.g., 1000–2000)."""
        duty_ns = pulse_width_ms * 1000
        self.duty_fd.seek(0)
        self.duty_fd.write(str(duty_ns))
        self.duty_fd.flush()

    def disable(self) -> None:
        self._write_once("enable", 0)

    def close(self) -> None:
        self.duty_fd.close()
        # Intentionally not unexporting — leave it available for other users

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
