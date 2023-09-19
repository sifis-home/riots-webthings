import requests
import json
import time

def update_thermostat():
  wot_url = "http://localhost:8888/0/properties"
  response = requests.get(wot_url)
  resp_json = response.json()

  values = {}

  for property_name in resp_json:
    propn = ""
    propv = resp_json[property_name]

    if property_name == 'TargetTemperatureProperty':
      propn = "set_temperature"
    elif property_name == 'TemperatureProperty':
      propn = "temperature"
    elif property_name == 'HumidityProperty':
      propn = "humidity"
    elif property_name == 'HeatingCoolingProperty':
      propn = "status"
      if(propv == "off"):
        propv = 0
      else:
        propv = 1
    values[propn] = propv
  
  values["name"] = "Riots Thermostat 1"
  api_url = "https://yggio.sifis-home.eu:3000/dht-insecure/"

  topic_name = "SIFIS::RiotsThermostat"
  topic_uuid = "FirstRiotsThermostat"
  response = requests.post(api_url + "topic_name/" + topic_name + "/topic_uuid/" + topic_uuid, json=values,verify=False)


while True:
  try:
    time.sleep(10)
    update_thermostat()
  except requests.exceptions.ConnectionError as error:
    print(error)

