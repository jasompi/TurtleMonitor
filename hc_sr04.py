#!/usr/bin/env python3

import RPi.GPIO as GPIO
import logging
import logging
import threading
import time

# Use BCM GPIO references
# instead of physical pin numbers
GPIO.setmode(GPIO.BCM)

# Define GPIO to use on Pi
GPIO_TRIGGER = 23
GPIO_ECHO    = 24

TRIGGER_PULSE_WIDTH = 0.000010 # 10uS
SOUND_SPEED = 343000   # 343000 mm/s

MEASURE_TIMEOUT = 1.0 # 1s

class UltrasonicSensor:
  def __init__(self, trigger_pin=GPIO_TRIGGER, echo_pin=GPIO_ECHO, measure_count=3, measure_interval=0.01, measure_period=1):
    self._trigger_pin = trigger_pin
    self._echo_pin = echo_pin
    self._measure_count = measure_count
    self._measure_interval = measure_interval
    self._measure_period = measure_period
    self._async_mode = False
    self._service_thread = None
    self._event = threading.Event()
    self._distance = -1
    self._begin = None
    self._elapsed = None
    # Set pins as output and input
    GPIO.setup(self._trigger_pin, GPIO.OUT)
    GPIO.setup(self._echo_pin, GPIO.IN)
    # Set trigger to False (Low)
    GPIO.output(self._trigger_pin, False)
    GPIO.add_event_detect(self._echo_pin, GPIO.BOTH, callback=self._measure_callback)

  def _measure_callback(self, channel):
    now = time.time()
    echo = GPIO.input(channel)
    if echo:
      self._begin = now
    else:
      if self._begin:
        self._elapsed = now - self._begin
      self._event.set()

  def _trigger(self):
    while GPIO.input(self._echo_pin) != 0:
      logging.error('Wait until ECHO is not 0')

    self._begin = None
    self._elapsed = None
    self._event.clear()

    GPIO.output(self._trigger_pin, True)
    time.sleep(TRIGGER_PULSE_WIDTH)
    GPIO.output(self._trigger_pin, False)

  def _measure(self):
    self._trigger()
    if self._event.wait(timeout=MEASURE_TIMEOUT) and self._elapsed:
      distance = (self._elapsed * SOUND_SPEED) / 2
      logging.debug(f'ECHO elapsesd {self._elapsed} seconds, distance={distance}mm')
    else:
      distance = -1
      if self._begin:
        logging.error('Could not detect falling edge on echo pin')
      else:
        logging.error('Could not detect rising edge on echo pin')
    return distance

  def _measure_average(self):
    measure_count = 0
    error_count = 0
    total_distance = 0
    while measure_count < self._measure_count and error_count < self._measure_count:
      begin = time.time()
      distance = self._measure()
      if distance < 0:
        error_count += 1
      else:
        total_distance += distance
        measure_count += 1
      end = time.time()
      elapsed = end - begin
      logging.debug(f'measure takes {elapsed}s')
      wait_period = self._measure_interval - elapsed
      if wait_period > 0:
        time.sleep(wait_period)
    if measure_count > 0:
      distance = total_distance / measure_count
      return distance
    else:
      logging.error(f'Failed to measure distance after {error_count} trials.')
      return -1

  @property
  def distance(self):
    if not self._async_mode:
      return self._measure_average()
    return self._distance


  def _measure_loop(self):
    logging.info('Ultrasonic Sensor measure_loop started')
    while self._async_mode:
      begin = time.time()
      self._distance = self._measure_average()
      end = time.time()
      elapsed = end - begin
      logging.debug(f'measure average takes {elapsed}s')
      wait_period = self._measure_period - elapsed
      if wait_period > 0:
        time.sleep(wait_period)
    logging.info('Ultrasonic Sensor measure_loop stopped')

  def start(self):
    if not self._async_mode:
      self._measure_average()
      self._async_mode = True
      self._service_thread = threading.Thread(target=self._measure_loop, name='Ultrasonic Sensor Measure Service')
      self._service_thread.start()
    else:
      logging.warning('Ultrasonic Sensor Measure Service already started')

  def shutdown(self):
    if self._async_mode:
      self._async_mode = False
      self._service_thread.join()
    else:
      logging.warning('Ultrasonic Sensor Measure Service not started')


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

  distance_sensor = UltrasonicSensor()
  if args.async_mode:
    distance_sensor.start()

  try:
    while True:
      distance = distance_sensor.distance
      print(f'Distance : {distance}')
      time.sleep(1)
  except KeyboardInterrupt:
    # User pressed CTRL-C
    # Reset GPIO settings
    distance_sensor.shutdown()
    GPIO.cleanup()

