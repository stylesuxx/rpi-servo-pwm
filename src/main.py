import time

from .HardwarePWM import HardwarePWM

pwm = HardwarePWM(channel=0, chip=0, frequency_hz=50.0)

MIN_PULSE = 1000  # in microseconds
MID_PULSE = 1500
MAX_PULSE = 2000


with HardwarePWM(channel=0) as pwm:
    pwm.setup(1500)
    pwm.set_pulse_width(2000)

    try:
        while True:
            for pulse in [MIN_PULSE, MID_PULSE, MAX_PULSE, MID_PULSE]:
                pwm.set_pulse_width(pulse)
                time.sleep(0.7)

    except KeyboardInterrupt:
        print("Interrupted, disabling PWM...")

    finally:
        pwm.disable()
