# Riots WebThings

This repository provides implementation that connects Riots Thermostats to SIFIS-Home architecture.

Thermostats are implemented as Web of Things complient devices.

----

Riots implementation of [Web of Things](https://www.w3.org/WoT/wg/) for SIFIS-Home WP6

The implementation uses [Python webthing library]([https://github.com/WebThingsIO/webthing-python)


The project can be run using docker-compose
```bash
docker-compose up
```


Running in Python:
```python
pip3 install -r requirements.txt
python3 ./src/riots-usb.py
python3 ./src/riots-webthings.py
python3 ./src/riots-dht.py
```


## Acknowledgements

This software has been developed in the scope of the H2020 project SIFIS-Home with GA n. 952652.
