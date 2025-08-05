import time

from .HardwarePWM import HardwarePWM

pwm = HardwarePWM(channel=0, chip=0, frequency_hz=50.0)

MIN_PULSE = 1000  # in microseconds
MID_PULSE = 1500
MAX_PULSE = 2000

try:
    pwm.setup(duty_us=MID_PULSE)

    while True:
        for pulse in [MIN_PULSE, MID_PULSE, MAX_PULSE, MID_PULSE]:
            pwm.set_duty_us(pulse)
            time.sleep(0.7)

except KeyboardInterrupt:
    print("Interrupted, disabling PWM...")

finally:
    pwm.disable()
    pwm.close()