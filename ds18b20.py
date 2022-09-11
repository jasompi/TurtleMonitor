#!/usr/bin/env python3

from classproperty import classproperty
import glob
import logging
import threading
import time


class DS18B20:
  _devices = {}
  _async_mode = False
  _service_thread = None
  _bulk_read = True
  def __init__(self, device_folder):
    self._device_folder = device_folder
    self._device_id = None
    self._temperature = 0
    self._timestamp = None

  def read_property(self, filename):
    with open(f'{self._device_folder}/{filename}', 'r') as f:
      return f.readline().strip()

  def write_property(self, filename, data):
    with open(f'{self._device_folder}/{filename}', 'w') as f:
      return f.write(data)

  @property
  def device_folder(self):
    return self._device_folder

  @property
  def device_id(self):
    if not self._device_id:
      self._device_id = self.read_property('name')
    return self._device_id

  @property
  def temperature(self):
    if not self._async_mode:
      self._read_temperature()
    return self._temperature

  def _read_temperature(self):
    temp_raw = self.read_property('temperature')
    if temp_raw:
      self._temperature = float(temp_raw) / 1000.0
      self._timestamp = time.time()

  @property
  def timestamp(self):
    return self._timestamp

  @property
  def conv_time(self):
    return self.read_property('conv_time')

  @property
  def resolution(self):
    return self.read_property('resolution')

  @resolution.setter
  def resolution(self, resolution):
    return self.write_property('resolution', resolution)

  def __str__(self):
    return f'DS18B20 ({self.device_id})'

  @staticmethod
  def fahrenheit(celsius):
    return celsius * 9.0 / 5.0 + 32.0

  @classproperty
  def devices(cls):
    base_dir = '/sys/bus/w1/devices/'
    for device_folder in glob.glob(base_dir + '28*'):
      if not device_folder in cls._devices:
        cls._devices[device_folder] = DS18B20(device_folder)
    return list(cls._devices.values())

  @classproperty
  def async_mode(cls):
    return cls._async_mode

  @classmethod
  def _read_temperatures(cls):
      for dev in cls.devices:
        dev._read_temperature()

  @classmethod
  def service_loop(cls):
    logging.info('DS18B20 Service started')
    while cls._async_mode:
      if cls._bulk_read:
        try:
          with open('/sys/bus/w1/devices/w1_bus_master1/therm_bulk_read', 'w') as f:
            f.write('trigger')
        except BaseException as ex:
          cls._bulk_read = False
          logging.warning(f'Cound not trigger buck read {ex}')
      cls._read_temperatures()
    logging.info('DS18B20 Service stopped')

  @classmethod
  def start(cls):
    if not cls._async_mode:
      cls._read_temperatures()
      cls._async_mode = True
      cls._service_thread = threading.Thread(target=cls.service_loop, name='DS18B20 Service')
      cls._service_thread.start()
    else:
      logging.warning('DS18B20 Service already started')

  @classmethod
  def shutdown(cls):
    if cls._async_mode:
      cls._async_mode = False
      cls._service_thread.join()
    else:
      logging.warning('DS18B20 Service not started')



fahrenheit = DS18B20.fahrenheit

if __name__ == "__main__":
  import argparse

  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--log-level',
      default=logging.INFO,
      type=lambda x: getattr(logging, x),
      help='Configure the logging level. default: INFO'
  )
  parser.add_argument(
      '--async-mode',
      default=False,
      type=bool,
      help='Collect temperature reading in async mode'
  )
  args = parser.parse_args()
  logging.basicConfig(level=args.log_level)

  device_names = {
    '28-012115d1f634': 'Water',
    '28-012114259884': 'Air',
  }

  devices = DS18B20.devices

  if args.async_mode:
    DS18B20.start()

  try:
    while True:
      for device in devices:
        device_id = device.device_id
        device_name = device_names[device_id]
        temp_c = device.temperature
        temp_f = DS18B20.fahrenheit(temp_c)
        timestamp = device.timestamp
        print(f'[{timestamp}] {device_name:>7}({device_id}): {temp_c}℃ {temp_f}℉')
      time.sleep(1)
  except KeyboardInterrupt:
    pass

  if args.async_mode:
    DS18B20.shutdown()
