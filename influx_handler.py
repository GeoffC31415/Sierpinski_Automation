from influxdb import InfluxDBClient
import json


def get_secrets():
    with open('./data/secrets.json') as s:
        secrets = json.load(s)
    return secrets


# Create the InfluxDB object as root
influxaccount = get_secrets()['InfluxAccount']
client = InfluxDBClient(**influxaccount)


def write(data):
    try:
        client.write_points(data)
        return True
    except Exception as err:
        # print(str(time.ctime()) + "    Error writing data to influx")
        # print(str(err))
        return False


def read(qry):
    return client.query(qry)
