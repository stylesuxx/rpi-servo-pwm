# Raspberry Pi Zero 2 W Servo PWM

A lightweight Python library for controlling servos on the Raspberry Pi Zero 2 W using hardware PWM via the Linux kernel.

## Setup

This library uses the kernel PWM driver provided by Raspberry Pi OS. To enable it, you must configure the Device Tree Overlay and reboot.

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

### Default GPIO Mapping

With the default overlay configuration, channels are mapped as follows:

| Channel | GPIO Pin |
|---------|----------|
| 0       | GPIO 18  |
| 1       | GPIO 19  |

### Optional: Remapping PWM pins

You can remap to other supported PWM-capable pins using overlay parameters.
For example, to map channel 1 to GPIO 13:

```ini
dtoverlay=pwm-2chan,pin=18,func=2,pin2=13,func2=4
```

This results in:

| Channel | GPIO Pin |
|---------|----------|
| 0       | GPIO 18  |
| 1       | GPIO 13  |

Verify the mapping with:

```bash
raspi-gpio get 18
# GPIO 18: level=0 fsel=2 alt=5 func=PWM0

raspi-gpio get 13
# GPIO 13: level=0 fsel=4 alt=0 func=PWM1
```

Note: Depending on firmware version, multiple `dtoverlay=pwm` lines may not both load.
If you encounter issues, combine pins into a single `pwm-2chan` line or consider a [custom overlay](https://github.com/raspberrypi/linux/blob/rpi-5.10.y/arch/arm/boot/dts/overlays/pwm-overlay.dts).

## Goals

This library provides low-level access to Raspberry Pi's hardware PWM interface via sysfs, avoiding high-level wrappers. This enables:

- Deterministic servo control
- Low-latency, real-time compatible operation
- Direct access to kernel PWM without background daemons

## Installation

Clone the repository:

```bash
git clone https://github.com/stylesuxx/rpi-servo-pwm.git
cd rpi-servo-pwm
```

Create a virtual environment and install dependencies:

```bash
python -m venv ./venv
source ./venv/bin/activate
pip install -r requirements.txt
```

## Usage Example

```python
from hardware_pwm import HardwarePWM

# Initialize PWM on channel 0 (GPIO 18), using 50 Hz
pwm = HardwarePWM(channel=0, frequency_hz=50)

# Setup with initial duty cycle (in microseconds)
pwm.setup(duty_us=1500)

# Move servo to new position
pwm.set_duty_us(2000)

# Disable when done
pwm.disable()
pwm.close()
```

## Testing

Run unit tests with:

```bash
python -m pytest tests
```

Tests are fully mocked and safe to run without hardware access.

## Distribution

To build and upload to PyPI:

1. Update the version in both `hardware_pwm/__init__.py` and `pyproject.toml`
2. Build and publish:

```bash
python -m build
python -m twine upload --repository testpypi dist/*
python -m twine upload dist/*
```

## Contributing

Pull requests and issue reports are welcome.

Before contributing:

```bash
python -m venv ./venv
source ./venv/bin/activate
pip install -r requirements.txt
```