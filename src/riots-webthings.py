from __future__ import division
from webthing import (Property, MultipleThings, Thing, Value, WebThingServer)
import logging
import time
import uuid

import random
import tornado.ioloop


class SimulatedRiotsThermostat(Thing):
    """A thermostat which updates its status and measurement in every few seconds."""

    def __init__(self, name, id):
        devid = 'urn:dev:ops:riots-device-' , id
        self.name = name

        Thing.__init__(
            self,
            devid,
            name,
            ['Thermostat'],
            'Riots web connected thermostat'
        )

        self.status = Value("off")
        self.add_property(
            Property(self,
                'HeatingCoolingProperty',
                self.status,
                metadata={
                    '@type': 'HeatingCoolingProperty',
                    'title': 'Heating status',
                    'type': 'string',                
                    'enum': ["off", "heating"],
                    'description': 'The status of heating',
                    'readOnly': True,
                }))

        self.temperature = Value(24.8)
        self.add_property(
            Property(self,
                'TemperatureProperty',
                self.temperature,
                metadata={
                    '@type': 'TemperatureProperty',
                    'title': 'Measured temperature',
                    'type': 'number',
                    'description': 'The current temperature in C',
                    'minimum': -20,
                    'maximum': 30,
                    'unit': 'degree celsius',
                    'readOnly': True,
                }))

        self.target_temperature = Value(21, lambda v: logging.info('%s temperature setpoint is now %s', self.name, v))

        self.add_property(
            Property(self,
                'TargetTemperatureProperty',
                self.target_temperature,
                metadata={
                    '@type': 'TargetTemperatureProperty',
                    'title': 'Set temperature',
                    'type': 'number',
                    'description': 'Target temperature 15-25',
                    'minimum': 15,
                    'maximum': 25,
                    'unit': 'degree celsius',
                }))

        self.timer = tornado.ioloop.PeriodicCallback(
            self.update_values,
            3000,
            0.5
        )
        self.timer.start()

    def update_values(self):
        new_temp = self.read_from_gpio()
        self.temperature.notify_of_external_update(new_temp)

        if new_temp > self.target_temperature.get():
          self.status.notify_of_external_update("off")

        else:
          self.status.notify_of_external_update("heating")

        logging.info('Update %s to %s (setpoint %s => %s)', self.name, new_temp, self.target_temperature.get(), self.status.get())


    def cancel_update_level_task(self):
        self.timer.stop()

    @staticmethod
    def read_from_gpio():
        return 18 + round(6.0 * random.random(), 1)


def run_server():

    thermostat1 = SimulatedRiotsThermostat("First thermostat", "1234")
    thermostat2 = SimulatedRiotsThermostat("Second thermostat", "5678")

    server = WebThingServer(MultipleThings([thermostat1, thermostat2], 'MultipleThermostats'), port=8888)

    try:
        logging.info('starting the server')
        server.start()
    except KeyboardInterrupt:
        logging.info('stopping the server')
        server.stop()
        logging.info('done')


if __name__ == '__main__':
    logging.basicConfig(
        level=10,
        format="%(asctime)s %(filename)s:%(lineno)s %(levelname)s %(message)s"
    )
    run_server()
