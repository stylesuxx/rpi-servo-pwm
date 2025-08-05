import pytest
from unittest import mock
from unittest.mock import mock_open, call

from src.rpi_servo_pwm.HardwarePWM import HardwarePWM  # replace with actual module name


@pytest.fixture
def mock_sysfs(monkeypatch):
    # Simulate directory structure
    base_path = "/sys/class/pwm/pwmchip0"
    channel_path = f"{base_path}/pwm0"

    isdir_mock = mock.Mock(side_effect=lambda path: path in [base_path, channel_path])
    monkeypatch.setattr("os.path.isdir", isdir_mock)

    open_mock = mock_open()
    monkeypatch.setattr("builtins.open", open_mock)

    return {
        "base_path": base_path,
        "channel_path": channel_path,
        "open_mock": open_mock,
        "isdir_mock": isdir_mock,
    }


def test_init_exports_channel_if_missing(monkeypatch):
    base_path = "/sys/class/pwm/pwmchip0"
    channel_path = f"{base_path}/pwm0"
    open_mock = mock_open()
    monkeypatch.setattr("builtins.open", open_mock)

    # Simulate base path exists, but channel path doesn't initially
    paths = set([base_path])

    def isdir_side_effect(path):
        if path == channel_path and "check_channel" not in paths:
            paths.add("check_channel")
            return False
        return path in paths

    monkeypatch.setattr("os.path.isdir", mock.Mock(side_effect=isdir_side_effect))

    pwm = HardwarePWM(channel=0, chip=0, frequency_hz=50.0)

    export_path = f"{base_path}/export"
    open_mock.assert_any_call(export_path, "w")
    pwm.close()


def test_setup_calls_write_once_and_set_duty(mock_sysfs):
    pwm = HardwarePWM(channel=0)

    pwm._write_once = mock.Mock()
    pwm.set_pulse_width = mock.Mock()

    pwm.setup(pulse_width=1500)

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
