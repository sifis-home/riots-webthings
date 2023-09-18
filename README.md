# Riots WebThings

This repository provides implementation that connects Riots Thermostats to SIFIS-Home architecture.

Thermostats are implemented as Web of Things complient devices.

----

Riots implementation of [Web of Things](https://www.w3.org/WoT/wg/) for SIFIS-Home WP6

Uses [Python webthing library]([https://github.com/WebThingsIO/webthing-python)

Running in Docker:
```bash
docker build --pull -t test . && docker run --rm -it test
```


Running in Python:
```python
python3 ./src/riots-webthings.py
```


## Acknowledgements

This software has been developed in the scope of the H2020 project SIFIS-Home with GA n. 952652.
