from __future__ import division
from webthing import (Property, MultipleThings, Thing, Value, WebThingServer)
import logging
import time
import uuid

import random
import tornado.ioloop

from twisted.internet import asyncioreactor
import tornado.platform.twisted
import websocket
import threading
import json


thermostats = []

"""A thermostat which updates its status and measurement in every few seconds."""
class RiotsThermostat(Thing):

    def __init__(self, ws_inst, data, index):
        devid = 'urn:dev:ops:riots-device-' + data["id"]
        self.id = data["id"]
        self.name = data["title"]
        self.ws = ws_inst
        self.index = index
        self.HeatingCoolingProperty = ""
        self.TemperatureProperty = ""
        self.HumidityProperty = ""
        self.TargetTemperatureProperty = ""

        Thing.__init__(self, devid, data["title"], ['Thermostat'], data["description"])

        for the_property in data["properties"]:
            value_property = ""
            if(data["properties"][the_property]["propertyType"] == "HeatingCoolingProperty"):
                self.HeatingCoolingProperty = Value([data["properties"][the_property]["value"]])
                value_property = self.HeatingCoolingProperty
            elif(data["properties"][the_property]["propertyType"] == "TemperatureProperty"):
                self.TemperatureProperty = Value(data["properties"][the_property]["value"])
                value_property = self.TemperatureProperty
            elif(data["properties"][the_property]["propertyType"] == "HumidityProperty"):
                self.HumidityProperty = Value(data["properties"][the_property]["value"])
                value_property = self.HumidityProperty
            elif(data["properties"][the_property]["propertyType"] == "TargetTemperatureProperty"):
                self.TargetTemperatureProperty = Value(data["properties"][the_property]["value"], self.update_target_temperature)
                value_property = self.TargetTemperatureProperty

            the_metadata={
                '@type': str(data["properties"][the_property]["propertyType"]),
                'title': str(data["properties"][the_property]["title"]),
                'type': str(data["properties"][the_property]["type"]),
                'description': str(data["properties"][the_property]["description"]),
                'unit': str(data["properties"][the_property]["unit"])
            }
            if "enum" in data["properties"][the_property]:
                the_metadata['enum'] = (data["properties"][the_property]["enum"])

            if "readOnly" in data["properties"][the_property]:
                the_metadata['readOnly'] = True

            self.add_property(
                Property(self,
                    data["properties"][the_property]['propertyType'],
                    value_property,
                    the_metadata
                )
            )

    def update_target_temperature(self, value):
        # print("Update_target_temperature ", self.name, " - Got ", value)
        sendData = {}
        sendData['thermostat'] = self.index
        sendData['propertyType'] = "TargetTemperatureProperty"
        sendData['value'] = str(value)
        self.ws.send(json.dumps(sendData))



class RiotsWebSocketClient:
    global thermostats
    def create(self):
      self.ws = websocket.WebSocketApp("ws://localhost:8942", on_open=self.on_open, on_close=self.on_close, on_data=self.on_data) # on_error=self.on_error, 
      self.wst = threading.Thread(target=lambda: self.ws.run_forever())
      self.wst.daemon = True
      self.wst.start()
      return self.ws

    # def on_error(self, ws, error):
    #     print("### Riots on_error" , error, " ###")

    def on_close(self, ws, close_status_code, close_msg):
        print("### Riots Connection closed ###")

    def on_open(self, ws):
        print("### Riots Connection established ###")

    def on_data(self, ws, recv_str, recv_type, recv_cont):
        # print("# On Data ", recv_str)
        obj = json.loads(recv_str)
        t_id = obj["thermostat"]
        t_prop = obj["propertyType"]
        t_data = obj["value"]

        # if(t_prop == "HeatingCoolingProperty") or t_prop == "TemperatureProperty" or t_prop == "HumidityProperty" or t_prop == "TargetTemperatureProperty":
        #    thermostats[t_id].set_property(t_prop, t_data)
        if(t_prop == "HeatingCoolingProperty"):
            thermostats[t_id].HeatingCoolingProperty.notify_of_external_update(t_data)
        elif(t_prop == "TemperatureProperty"):
            thermostats[t_id].TemperatureProperty.notify_of_external_update(t_data)
        elif(t_prop == "HumidityProperty"):
            thermostats[t_id].HumidityProperty.notify_of_external_update(t_data)
        elif(t_prop == "TargetTemperatureProperty"):
            thermostats[t_id].TargetTemperatureProperty.notify_of_external_update(t_data)


def run_server():

    ws_client = RiotsWebSocketClient()
    ws_inst = ws_client.create()

    f = open('inc/riots-device-configuration.json')
    configuration_data = json.load(f)
    for idx, thermostat_data in enumerate(configuration_data):
      thermostat = RiotsThermostat(ws_inst, thermostat_data, idx)
      thermostats.append(thermostat)
    f.close()

    server = WebThingServer(MultipleThings(thermostats, 'MultipleThermostats'), port=8888)

    try:
        logging.info('starting the server')
        server.start()
    except KeyboardInterrupt:
        logging.info('stopping the server')
        server.stop()
        logging.info('done')


if __name__ == '__main__':
    time.sleep(8) # Give Riots USB some time to start
    logging.basicConfig(
        level=10,
        format="%(asctime)s %(filename)s:%(lineno)s %(levelname)s %(message)s"
    )
    run_server()
