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
        display_status('Readings: {:>8.4f}{:>8.4f}{:>8.4f}{:>8.4f}'.format(*r))
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
