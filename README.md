# Riots WebThings

This repository provides implementation of two simulated Riots Thermostats

Thermostats change measured temperature (and heating status) in random intervals approx once in every three seconds

----

Riots implementation of [Web of Things](https://www.w3.org/WoT/wg/) for WP6 demos

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
