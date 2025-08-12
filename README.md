[![Coverage](https://codecov.io/gh/stylesuxx/rpi-servo-pwm/branch/main/graph/badge.svg)](https://codecov.io/gh/stylesuxx/rpi-servo-pwm)

# Raspberry Pi Zero 2 W Servo PWM

A lightweight Python library for controlling RC servos on the Raspberry Pi Zero 2 W using hardware PWM via the Linux kernel.

This library is specifically designed for **servo PWM control**. The PWM frequency is fixed to 50 Hz by default, and you specify the pulse length in microseconds.

Typical RC servos expect a pulse width between **1000 µs and 2000 µs**, where **1500 µs** is the center position. Some servo models support a wider range, e.g., **900–2100 µs**, but you must verify this in your servo's datasheet or test cautiously. Increase or decrease values gradually; if the servo starts making crackling or buzzing noises, reduce the range.
Extended pulse width ranges are usually symmetrical – for example, if you can safely reduce the pulse width by 100 µs, you can usually increase it by a similar amount.

## Why this library?

I wanted a deterministic library for one specific use case: **Servo PWM**.
Existing solutions were often too bloated, included unused features or relied on software-based PWM, which is not timing-accurate.

This library ensures:

* **Hardware-only PWM** (no bit-banging fallback)
* **Predictable timing**, as PWM generation is handled by the Raspberry Pi's PWM hardware module
* A **minimal, low-overhead interface** tailored for servos (frequency fixed at 50Hz, only pulse width adjustable)

## Supported platforms

All Raspberry Pi platforms with kernel hardware PWM support should work.

It has been tested on the following platforms:

* Raspberry Pi Zero 2 W (with Raspberry Pi OS Bullseye, Bookworm)

## Setup

This library uses the kernel PWM driver provided by Raspberry Pi OS. To enable it, configure the Device Tree Overlay and reboot.

> Make sure you are not running any other PWM-related software like `pigpiod` for example.

### Enable PWM in `/boot/config.txt`

Add the following line:

```ini
dtoverlay=pwm-2chan
```

Reboot:

```bash
sudo reboot
```

### Verify PWM availability

After reboot, check that the PWM interface is present:

```bash
ls /sys/class/pwm/pwmchip0
# Expected output: device  export  npwm  power  subsystem  uevent  unexport
```

Verify that there are two available channels:

```bash
cat /sys/class/pwm/pwmchip0/npwm
# Expected output: 2
```

### Verify Group membership

Make sure that the invoking user is part of the `gpio` group, if not add them:

```bash
sudo usermod -aG gpio $USER
```

### Default GPIO mapping

With the default overlay configuration, channels are mapped as follows:

| Channel | GPIO Pin |
|---------|----------|
| 0       | GPIO 18  |
| 1       | GPIO 19  |

### Optional: remapping PWM pins

You can remap PWM channels to other supported GPIO pins using overlay parameters.
For example, to map channel 1 to GPIO 13:

```ini
dtoverlay=pwm-2chan,pin=18,func=2,pin2=13,func2=4
```

Resulting mapping:

| Channel | GPIO Pin |
|---------|----------|
| 0       | GPIO 18  |
| 1       | GPIO 13  |

Verify the mapping:

```bash
raspi-gpio get 18
# GPIO 18: level=0 fsel=2 alt=5 func=PWM0

raspi-gpio get 13
# GPIO 13: level=0 fsel=4 alt=0 func=PWM1
```

## Installation

Install via pip:

```bash
pip install rpi-servo-pwm
```

## Usage

Example using manual resource management:

```python
from rpi_servo_pwm import HardwarePWM

# Initialize PWM on channel 0 (GPIO 18), using 50 Hz
pwm = HardwarePWM(channel=0, frequency_hz=50)

# Start PWM with initial pulse width
pwm.setup(1500)

# Move servo to a new position
pwm.set_pulse_width(2000)

# Disable and close
pwm.disable()
pwm.close()
```

Example using a context manager:

```python
from rpi_servo_pwm import HardwarePWM

with HardwarePWM(channel=0) as pwm:
    pwm.setup(1500)
    pwm.set_pulse_width(2000)
    pwm.disable()
```

Once you call `setup`, the PWM signal starts outputting on the pin. Calling `disable` stops the PWM output.

## Testing

Run unit tests with:

```bash
python -m pytest tests
```

Tests are fully mocked and safe to run without hardware access.

## Contributing

Pull requests and issue reports are welcome.

Before contributing:

```bash
python -m venv ./venv
source ./venv/bin/activate
pip install -r requirements.txt
```

## Distribution

To build and upload to PyPI:

1. Update the version in both `src/__init__.py` and `pyproject.toml`
2. Build and publish:

```bash
rm -rf dist/*
python -m build
python -m twine upload --repository testpypi dist/*
python -m twine upload dist/*
```
