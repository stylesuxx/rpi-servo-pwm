import pytest
from unittest import mock
from unittest.mock import mock_open, call
from src.rpi_servo_pwm.HardwarePWM import HardwarePWM


@pytest.fixture
def mock_sysfs(monkeypatch):
    """Simulate sysfs directory and files for PWM."""

    # Mock isdir to return True for any PWM path pattern
    def isdir_side_effect(path):
        # Accept any pwmchipX and pwmchipX/pwmY patterns
        import re

        return bool(re.match(r"/sys/class/pwm/pwmchip\d+(/pwm\d+)?$", path))

    isdir_mock = mock.Mock(side_effect=isdir_side_effect)
    monkeypatch.setattr("os.path.isdir", isdir_mock)

    # Mock file operations
    open_mock = mock_open()
    monkeypatch.setattr("builtins.open", open_mock)

    # Skip permission waiting logic
    monkeypatch.setattr(HardwarePWM, "_wait_for_permissions", lambda *a, **k: None)

    return {
        "open_mock": open_mock,
        "isdir_mock": isdir_mock,
    }


class TestInitialization:
    """Test initialization and validation."""

    def test_init_with_default_values(self, mock_sysfs):
        """Test initialization with default parameters."""
        pwm = HardwarePWM(channel=0)

        assert pwm.chip == 0
        assert pwm.channel == 0
        assert pwm.period_ns == 20_000_000  # 50Hz = 20ms period
        assert pwm.base_path == "/sys/class/pwm/pwmchip0"
        assert pwm.channel_path == "/sys/class/pwm/pwmchip0/pwm0"
        pwm.close()

    def test_init_with_custom_values(self, mock_sysfs):
        """Test initialization with custom parameters."""
        pwm = HardwarePWM(channel=1, chip=2, frequency_hz=100.0)

        assert pwm.chip == 2
        assert pwm.channel == 1
        assert pwm.period_ns == 10_000_000  # 100Hz = 10ms period
        assert pwm.base_path == "/sys/class/pwm/pwmchip2"
        assert pwm.channel_path == "/sys/class/pwm/pwmchip2/pwm1"
        pwm.close()

    def test_init_validation_negative_channel(self):
        """Should raise ValueError for negative channel."""
        with pytest.raises(ValueError, match="Channel must be non-negative"):
            HardwarePWM(channel=-1)

    def test_init_validation_negative_chip(self):
        """Should raise ValueError for negative chip."""
        with pytest.raises(ValueError, match="Chip must be non-negative"):
            HardwarePWM(channel=0, chip=-1)

    def test_init_validation_zero_frequency(self):
        """Should raise ValueError for zero frequency."""
        with pytest.raises(ValueError, match="Frequency must be positive"):
            HardwarePWM(channel=0, frequency_hz=0.0)

    def test_init_validation_negative_frequency(self):
        """Should raise ValueError for negative frequency."""
        with pytest.raises(ValueError, match="Frequency must be positive"):
            HardwarePWM(channel=0, frequency_hz=-50.0)

    def test_init_missing_chip_directory(self, monkeypatch):
        """Should raise RuntimeError if PWM chip doesn't exist."""
        monkeypatch.setattr("os.path.isdir", lambda path: False)

        with pytest.raises(RuntimeError, match="PWM chip 0 does not exist"):
            HardwarePWM(channel=0)

    def test_init_exports_channel_if_missing(self, monkeypatch):
        """Should write to export if channel dir is missing."""
        base_path = "/sys/class/pwm/pwmchip0"
        channel_path = f"{base_path}/pwm0"
        open_mock = mock_open()
        monkeypatch.setattr("builtins.open", open_mock)

        # Simulate base exists, channel missing initially
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
        open_mock().write.assert_any_call("0")
        pwm.close()


class TestFrequencyCalculation:
    """Test frequency to period conversion."""

    @pytest.mark.parametrize(
        "frequency,expected_period",
        [
            (50.0, 20_000_000),  # 50Hz = 20ms
            (100.0, 10_000_000),  # 100Hz = 10ms
            (1000.0, 1_000_000),  # 1kHz = 1ms
            (1.0, 1_000_000_000),  # 1Hz = 1s
        ],
    )
    def test_frequency_to_period_conversion(
        self, mock_sysfs, frequency, expected_period
    ):
        """Test various frequency to period conversions."""
        pwm = HardwarePWM(channel=0, frequency_hz=frequency)
        assert pwm.period_ns == expected_period
        pwm.close()


class TestSetup:
    """Test setup functionality."""

    def test_setup_sequence(self, mock_sysfs):
        """Test setup calls methods in correct order."""
        pwm = HardwarePWM(channel=0)
        pwm._write_once = mock.Mock()
        pwm.set_pulse_width = mock.Mock()

        pwm.setup(pulse_width_us=1500)

        # Verify call order and arguments
        expected_calls = [call("period", pwm.period_ns), call("enable", 1)]
        pwm._write_once.assert_has_calls(expected_calls)
        pwm.set_pulse_width.assert_called_once_with(1500)
        pwm.close()


class TestPulseWidth:
    """Test pulse width functionality."""

    def test_set_pulse_width_writes_correct_value(self, mock_sysfs):
        """Test pulse width conversion and file operations."""
        pwm = HardwarePWM(channel=0)
        pwm.duty_fd = mock.Mock()

        pwm.set_pulse_width(1234)

        pwm.duty_fd.seek.assert_called_once_with(0)
        pwm.duty_fd.write.assert_called_once_with(str(1234 * 1000))  # μs to ns
        pwm.duty_fd.flush.assert_called_once()
        pwm.close()

    def test_set_pulse_width_validation_negative(self, mock_sysfs):
        """Should raise ValueError for negative pulse width."""
        pwm = HardwarePWM(channel=0)

        with pytest.raises(ValueError, match="Pulse width must be non-negative"):
            pwm.set_pulse_width(-100)
        pwm.close()

    def test_set_pulse_width_validation_exceeds_period(self, mock_sysfs):
        """Should raise ValueError when pulse width exceeds period."""
        pwm = HardwarePWM(channel=0, frequency_hz=50.0)  # 20ms period

        # Try to set 25ms pulse width (exceeds 20ms period)
        with pytest.raises(ValueError, match="cannot exceed period"):
            pwm.set_pulse_width(25000)  # 25ms in μs
        pwm.close()

    def test_set_pulse_width_boundary_values(self, mock_sysfs):
        """Test boundary values for pulse width."""
        pwm = HardwarePWM(channel=0, frequency_hz=50.0)  # 20ms period
        pwm.duty_fd = mock.Mock()

        # Test zero (should work)
        pwm.set_pulse_width(0)
        pwm.duty_fd.write.assert_called_with("0")

        # Test maximum valid value (exactly the period)
        pwm.duty_fd.reset_mock()
        pwm.set_pulse_width(20000)  # 20ms in μs
        pwm.duty_fd.write.assert_called_with(str(20000 * 1000))

        pwm.close()


class TestControlMethods:
    """Test control methods."""

    def test_disable_calls_write_once(self, mock_sysfs):
        """Test disable functionality."""
        pwm = HardwarePWM(channel=0)
        pwm._write_once = mock.Mock()

        pwm.disable()

        pwm._write_once.assert_called_once_with("enable", 0)
        pwm.close()

    def test_write_once_opens_and_writes(self, mock_sysfs):
        """Test _write_once internal method."""
        pwm = HardwarePWM(channel=0)

        pwm._write_once("enable", 1)

        mock_sysfs["open_mock"].assert_any_call(
            "/sys/class/pwm/pwmchip0/pwm0/enable", "w"
        )
        mock_sysfs["open_mock"]().write.assert_any_call("1")
        pwm.close()


class TestResourceManagement:
    """Test resource management and cleanup."""

    def test_close_closes_fd(self, mock_sysfs):
        """Test close method closes file descriptor."""
        pwm = HardwarePWM(channel=0)
        # Replace the duty_fd with a mock after initialization
        mock_fd = mock.Mock()
        mock_fd.closed = False  # Ensure it's not already closed
        pwm.duty_fd = mock_fd

        pwm.close()

        mock_fd.close.assert_called_once()

    def test_close_handles_missing_fd(self, mock_sysfs):
        """Test close handles case where duty_fd doesn't exist."""
        pwm = HardwarePWM(channel=0)
        del pwm.duty_fd  # Remove the attribute

        # Should not raise an exception
        pwm.close()

    def test_close_handles_already_closed_fd(self, mock_sysfs):
        """Test close handles already closed file descriptor."""
        pwm = HardwarePWM(channel=0)
        pwm.duty_fd = mock.Mock()
        pwm.duty_fd.closed = True

        pwm.close()

        # Should not call close on already closed fd
        pwm.duty_fd.close.assert_not_called()

    def test_context_manager_usage(self, mock_sysfs):
        """Test context manager functionality."""
        with mock.patch.object(HardwarePWM, "close") as mock_close:
            with HardwarePWM(channel=0) as pwm:
                assert isinstance(pwm, HardwarePWM)

            mock_close.assert_called_once()

    def test_context_manager_with_exception(self, mock_sysfs):
        """Test context manager calls close even with exceptions."""
        with mock.patch.object(HardwarePWM, "close") as mock_close:
            try:
                with HardwarePWM(channel=0) as pwm:
                    raise ValueError("Test exception")
            except ValueError:
                pass

            mock_close.assert_called_once()


class TestPermissionWaiting:
    """Test permission waiting functionality."""

    def test_wait_for_permissions_success(self, monkeypatch):
        """Test successful permission waiting."""
        # Mock os.access to return True (permissions available)
        monkeypatch.setattr("os.access", lambda path, mode: True)
        monkeypatch.setattr("os.path.isdir", lambda path: True)

        # Create real instance to test _wait_for_permissions
        pwm = HardwarePWM.__new__(HardwarePWM)
        pwm.channel_path = "/test/path"

        # Should complete without raising
        pwm._wait_for_permissions("duty_cycle", timeout=0.1)

    def test_wait_for_permissions_timeout(self, monkeypatch):
        """Test permission waiting timeout."""
        # Mock os.access to always return False (no permissions)
        monkeypatch.setattr("os.access", lambda path, mode: False)
        monkeypatch.setattr("time.sleep", lambda x: None)  # Speed up test

        pwm = HardwarePWM.__new__(HardwarePWM)
        pwm.channel_path = "/test/path"

        with pytest.raises(PermissionError, match="Timeout waiting for write access"):
            pwm._wait_for_permissions("duty_cycle", timeout=0.1)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_high_frequency(self, mock_sysfs):
        """Test with very high frequency values."""
        pwm = HardwarePWM(channel=0, frequency_hz=10000.0)  # 10kHz
        assert pwm.period_ns == 100_000  # 0.1ms
        pwm.close()

    def test_very_low_frequency(self, mock_sysfs):
        """Test with very low frequency values."""
        pwm = HardwarePWM(channel=0, frequency_hz=0.1)  # 0.1Hz
        assert pwm.period_ns == 10_000_000_000  # 10s
        pwm.close()

    def test_fractional_frequency(self, mock_sysfs):
        """Test with fractional frequency values."""
        pwm = HardwarePWM(channel=0, frequency_hz=33.33)  # ~30ms period
        expected_period = int(1000000 / 33.33) * 1000
        assert pwm.period_ns == expected_period
        pwm.close()
