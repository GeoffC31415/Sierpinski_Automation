import time
import json
import math
import traceback
import wiringpi

import numpy as np
import RPi.GPIO as GPIO

from os import popen
from os.path import join, dirname
from datetime import datetime as dt
from datetime import timedelta as td
from ADCPi import ADCPi

import influx_handler
import file_handler

#
# Globals
#
DEVICES = {
    'heater': {
        'pins': [17, 27],
        'state': {
            'power': None,
            'last_change': dt(2000, 1, 1)
        },
        'deadzone': {
            'temp': 0.1,
            'time': 180
        },
        'daycycle': {
            'avgT': 26,
            'deltaT': 2,
            'coldest_hour': 2
        }
    },
    'leds': {
        'state': None,
        'sunrise': td(hours=6),
        'sunset': td(hours=20)
    },
    'thermistors': {
        'adc': ADCPi(0x68, 0x69, 18)
    }
}
runNo = 'v1'
verbose = True
cycle_log = []
thermistor_volts = []


def init_calibration():
    with open(join(dirname(__file__), './data/thermistors.json'), 'r') as f:
        data = json.load(f)

    data['temps'] = np.array(data['temps'])
    data['voltages'] = np.array(data['voltages'])
    return data


def IO_setup():
    GPIO.setmode(GPIO.BCM)
    wiringpi.wiringPiSetupGpio()
    wiringpi.pinMode(18, 2)  # Pin 18 only
    wiringpi.pwmWrite(18, 0)
    for d in DEVICES:
        dev = DEVICES[d]
        if 'pins' in dev:
            for pin in dev['pins']:
                GPIO.setup(pin, GPIO.OUT)


#
# Device Logic
#
def set_heater_by_time(t):
    # Setup variables
    readings = take_readings(1)[0]
    heater = DEVICES['heater']

    # Calc intermediate values
    target_temp = calc_target_temp(t, **heater['daycycle'])
    
    # If a reading is exactly 13 degrees, the sensor has been ripped off the wall by pinpin
    useful_readings = [r for r in readings if r != 13]
    median_temp = calculate_median(useful_readings)

    power = median_temp < target_temp
    delta_t = (dt.now() - heater['state']['last_change']).total_seconds()

    # Deadzone logic
    dz = heater['deadzone']
    in_temp_deadzone = abs(median_temp - target_temp) < dz['temp']
    in_time_deadzone = delta_t < dz['time']
    init_heater = heater['state']['power'] is None

    # Set heater state if required
    if not (in_temp_deadzone or in_time_deadzone) or init_heater:
        set_heater_absolute(power)

    # Log values
    log_temps(readings, median_temp)
    log_fields({
        'heater_state': heater['state']['power'], 
        'target_temp': target_temp, 
        'temp_pi': get_pi_temp()
    })


def set_leds_by_time(t):
    # Set up timedeltas since 00:00
    sunrise = DEVICES['leds']['sunrise']
    sunset = DEVICES['leds']['sunset']
    now = t - dt(t.year, t.month, t.day)

    # Convert to angular time
    day_prop = (now - sunrise) / (sunset - sunrise)
    brightness = max(0, math.sin(day_prop * math.pi)**3)

    # Scale for LED hardware PWM via wiringpi
    brightness = int(1024 * brightness + 0.5)
    set_leds_absolute(brightness)


#
# Device Controllers
#
def set_heater_absolute(power):
    state = DEVICES['heater']['state']

    if power != state['power']:
        display_status(f'Setting heater to {power}')
        for p in DEVICES['heater']['pins']:
            GPIO.output(p, GPIO.LOW if power else GPIO.HIGH)
        state['power'] = power
        state['last_change'] = dt.now()


def set_leds_absolute(brightness):
    if brightness != DEVICES['leds']['state']:
        wiringpi.pwmWrite(18, brightness)
        DEVICES['leds']['state'] = brightness
        log_fields({'light': brightness})


#
# Utility functions
#
def volts_to_centigrade(volts, sensorNum):
    global thermistor_volts
    x = thermistor_volts['voltages'][sensorNum]
    y = thermistor_volts['temps']
    return np.interp(volts, x, y)


def calc_target_temp(t, avgT, deltaT, coldest_hour):
    # Extract parameters
    now = t - dt(t.year, t.month, t.day)

    # Detemine time angle
    angular_time = (now - td(hours=coldest_hour)) / td(hours=12)
    angular_time *= math.pi

    # Set heater according to temperature
    target = avgT - (math.cos(angular_time) * deltaT)
    return target


def take_readings(N):
    """N is the number of readings to take. 
    Each reading is a list of four numbers from the four sensors."""
    r = [0, 0, 0, 0]
    readings = []
    adc = DEVICES['thermistors']['adc']
    for n in range(N):
        for i in range(4):
            r[i] = volts_to_centigrade(adc.read_voltage(i + 1), i)
        readings.append(r)
        time.sleep(1)
    return readings


def calculate_median(lst):
    sorted_lst = sorted(lst)
    n = len(sorted_lst)
    
    if n % 2 == 0:
        middle1 = sorted_lst[n // 2 - 1]
        middle2 = sorted_lst[n // 2]
        median = (middle1 + middle2) / 2
    else:
        median = sorted_lst[n // 2]
    
    return median


def get_pi_temp():
    temp = popen("vcgencmd measure_temp").readline()
    return float(temp[5:-3])


def display_status(s):
    if verbose:
        print(str(time.ctime()) + ' ' + s)


#
# Logging
#
def log_temps(readings, repr_temp):
    temps = {'temp' + str(i): r for i,r in enumerate(readings)}
    temps['temp_avg'] = repr_temp
    log_fields(temps)


def log_fields(fields):
    cycle_log.append({'measurement': 'vivarium2', 'tags': {'run': runNo}, 'fields': fields})


def write_points(data):
    global cycle_log
    if influx_handler.write(data):
        cycle_log = []
    else:
        display_status('Problem writing sensor data to InfluxDB')


#
# Main Loop
#
def main():
    global cycle_log, thermistor_volts
    IO_setup()
    thermistor_volts = init_calibration()

    print('Initialisation complete')
    try:
        while True:
            t = dt.now()

            set_heater_by_time(t)
            set_leds_by_time(t)

            if len(cycle_log) > 0:
                write_points(cycle_log)
            file_handler.cleanVideos(minhr=6, maxhr=20, maxsize=3e6)

            time.sleep(10)
    except Exception as e:
        print(str(e))
        traceback.print_exc()
    finally:
        GPIO.cleanup()


if __name__ == '__main__':
    main()
