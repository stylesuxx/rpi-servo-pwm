import os
import pytest
from unittest import mock
from unittest.mock import mock_open, call

from src.rpi_servo_pwm.HardwarePWM import HardwarePWM  # adjust path if needed


@pytest.fixture
def mock_sysfs(monkeypatch):
    """Simulate sysfs directory and files for PWM."""
    base_path = "/sys/class/pwm/pwmchip0"
    channel_path = f"{base_path}/pwm0"

    # Simulate base & channel directory existence
    isdir_mock = mock.Mock(side_effect=lambda path: path in [base_path, channel_path])
    monkeypatch.setattr("os.path.isdir", isdir_mock)

    # Mock file operations
    open_mock = mock_open()
    monkeypatch.setattr("builtins.open", open_mock)

    # Skip permission waiting logic
    monkeypatch.setattr(HardwarePWM, "_wait_for_permissions", lambda *a, **k: None)

    return {
        "base_path": base_path,
        "channel_path": channel_path,
        "open_mock": open_mock,
        "isdir_mock": isdir_mock,
    }


def test_init_exports_channel_if_missing(monkeypatch):
    """Should write to export if channel dir is missing."""
    base_path = "/sys/class/pwm/pwmchip0"
    channel_path = f"{base_path}/pwm0"
    open_mock = mock_open()
    monkeypatch.setattr("builtins.open", open_mock)

    # Simulate base exists, channel missing first
    calls = {"checked": False}
    def isdir_side_effect(path):
        if path == channel_path and not calls["checked"]:
            calls["checked"] = True
            return False
        return path in {base_path, channel_path}

    monkeypatch.setattr("os.path.isdir", mock.Mock(side_effect=isdir_side_effect))
    monkeypatch.setattr(HardwarePWM, "_wait_for_permissions", lambda *a, **k: None)

    pwm = HardwarePWM(channel=0, chip=0, frequency_hz=50.0)

    open_mock.assert_any_call(f"{base_path}/export", "w")
    pwm.close()


def test_setup_calls_write_once_and_set_duty(mock_sysfs):
    pwm = HardwarePWM(channel=0)

    pwm._write_once = mock.Mock()
    pwm.set_pulse_width = mock.Mock()

    pwm.setup(pulse_width_ms=1500)

    pwm._write_once.assert_has_calls([
        call("period", pwm.period_ns),
        call("enable", 1)
    ])
    pwm.set_pulse_width.assert_called_once_with(1500)
    pwm.close()


def test_set_pulse_width_writes_correct_value(mock_sysfs):
    pwm = HardwarePWM(channel=0)
    fd = pwm.duty_fd = mock.Mock()

    pwm.set_pulse_width(1234)

    fd.seek.assert_called_once_with(0)
    fd.write.assert_called_once_with(str(1234 * 1000))
    fd.flush.assert_called_once()
    pwm.close()


def test_disable_calls_write_once(mock_sysfs):
    pwm = HardwarePWM(channel=0)
    pwm._write_once = mock.Mock()

    pwm.disable()

    pwm._write_once.assert_called_once_with("enable", 0)
    pwm.close()


def test_close_closes_fd(mock_sysfs):
    pwm = HardwarePWM(channel=0)
    pwm.duty_fd = mock.Mock()

    pwm.close()
    pwm.duty_fd.close.assert_called_once()
