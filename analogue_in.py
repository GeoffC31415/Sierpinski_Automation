import time
import json
import argparse

import numpy as np

from datetime import datetime as dt
from ADCPi import ADCPi

adc = ADCPi(0x68, 0x69, 16)
r = [0, 0, 0, 0]
thermistor_calibration = {}
with open('thermistor_calibration.json', 'r') as f:
    thermistor_calibration = json.load(f)
    for k in thermistor_calibration:
        # Interp requires ascending X - reverse array order
        thermistor_calibration[k] = np.array(thermistor_calibration[k])[::-1]


def volts_to_centigrade(volts):
    x = thermistor_calibration['voltages']
    y = thermistor_calibration['temperature']
    return np.interp(volts, x, y)


def take_readings(N):
    readings = []
    for n in range(N):
        start = dt.now()
        for i in range(4):
            r[i] = adc.read_voltage(i + 1)
        end = dt.now()
        t = (end - start).total_seconds()
        print(
            'Readings {:>3} of {} : {:>4.0f}ms {:>8.4f}{:>8.4f}{:>8.4f}{:>8.4f}'
            .format(n + 1, N, 1000 * t, *volts_to_centigrade(r)))
        readings.append(r)
        time.sleep(1)
    return readings


def print_avgs(readings):
    avgs = np.median(readings, axis=0)
    print(avgs)


def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--N',
                        '-n',
                        type=int,
                        help='Number of samples to take')
    parser.add_argument('--temp',
                        '-t',
                        help='Temperature readings were taken at')
    args = parser.parse_args()

    readings = np.array(take_readings(args.N))
    with open('temp_calibration.json', 'r+') as f:
        calibrations = json.load(f)
    calibrations[str(args.temp)] = np.median(readings, axis=0).tolist()
    with open('temp_calibration.json', 'w') as f:
        json.dump(calibrations, f)


if __name__ == '__main__':
    main()
