#!/usr/bin/env python3

import adafruit_veml6075 as veml6075
import board
import busio
import data_store
from ds18b20 import fahrenheit, DS18B20
import fonts.ttf
import glob
from hc_sr04 import UltrasonicSensor
import inky.phat
import logging
import math
import os
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import random
import threading
import time
from inky_display_service import InkyDisplayService


WATER_HIGH_LEVEL = 240
WATER_LOW_LEVEL = 200
WATER_MAX_DISTANCE = 300

random.seed()

class TurtleDisplay:
  def load_image(name):
    # Get the current path
    PATH = os.path.dirname(__file__)
    return PIL.Image.open(os.path.join(PATH, f'{name}.png')).resize((24, 24))

    # Load the font
  font = PIL.ImageFont.truetype(fonts.ttf.RobotoMedium, 20)
  symbola20_font = PIL.ImageFont.truetype('/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf', 20)
  symbola30_font = PIL.ImageFont.truetype('/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf', 20)
  symbola40_font = PIL.ImageFont.truetype('/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf', 35)
  # Load images and icons
  uv_icon = load_image('UV')
  air_icon = '🌡'
  water_wave_icon = '🌊'
  fill_water_icon = '🚰'
  turtle_icon = '🐢'
  snail_icon = '🐌🐌'
  water_tilde_symbols = ' ∼≈≋'
  water_tilde_offsets = [0, 6, 3, 0]
  caption_width_ratio = 0.35
  water_icon_w, water_icon_h = symbola20_font.getsize(water_tilde_symbols[3])
  fill_water_w, fill_water_h = symbola20_font.getsize(fill_water_icon)
  turtle_icon_w, turtle_icon_h = symbola40_font.getsize(turtle_icon)
  snail_icon_w, snail_icon_h = symbola30_font.getsize(snail_icon)

  def __init__(self, inky_service):
    self._inky_service = inky_service
    self._air_temp_str = ''
    self._water_temp_str = ''
    self._uv_str = ''
    self._water_level = -1

  def display(self, air_temp, water_temp, uva, uvb, water_distance):
    water_depth = WATER_MAX_DISTANCE - water_distance
    water_level = max(min(17, round((water_depth - WATER_LOW_LEVEL) * 17/(WATER_HIGH_LEVEL - WATER_LOW_LEVEL))), 0)

    air_temp_str = f': {round(air_temp)}℃ {round(fahrenheit(air_temp))}℉'
    water_temp_str = f': {round(water_temp)}℃ {round(fahrenheit(water_temp))}℉'
    uv_str = f': {round(uva)}(A) {round(uvb)}(B)'
    logging.debug(f'uv: {uv_str}; air: {air_temp_str}; water: {water_temp_str}; water_level: {water_level}')

    if (air_temp_str != self._air_temp_str or water_temp_str != self._water_temp_str
        or uv_str != self._uv_str or water_level != self._water_level):
      self._air_temp_str = air_temp_str
      self._water_temp_str = water_temp_str
      self._uv_str = uv_str
      self._water_level = water_level

      canvas = self._inky_service.get_canvas()
      img = canvas.image
      draw = canvas.draw

      icon_w, icon_h = self.uv_icon.size
      w, h = self.font.getsize('UV')
      x = int(canvas.width * self.caption_width_ratio - w)
      x = 28
      y = 4
      img.paste(self.uv_icon, (x - icon_w - 2, y))
      draw.text((x, y), uv_str, inky.BLACK, font=self.font)
      w, h = self.font.getsize(uv_str)
      uv_right, uv_bottom = x + w, y + h

      icon_w, icon_h = self.symbola20_font.getsize(self.air_icon)
      w, h = self.font.getsize('Air')
      x = int(canvas.width * self.caption_width_ratio - w)
      x = 28
      y = int(canvas.height / 2 - h - 5)
      draw.text((x, y), air_temp_str, inky.BLACK, font=self.font)
      draw.text((x - icon_w - 2, y), self.air_icon, inky.BLACK, font=self.symbola20_font)

      icon_w, icon_h = self.symbola20_font.getsize(self.water_wave_icon)
      w, h = self.font.getsize('Water')
      x = int(canvas.width * self.caption_width_ratio - w)
      x = 28
      y = int(canvas.height / 2 + 5)
      draw.text((x, y), water_temp_str, inky.BLACK, font=self.font)
      draw.text((x - icon_w - 2, y), self.water_wave_icon, inky.BLACK, font=self.symbola20_font)
      w, h = self.font.getsize(water_temp_str)
      wt_right, wt_bottom = x + w, y + h

      y += h + 2
      x = 0

      left = x
      draw_turtle = True
      draw_snail = True
      while water_level >= 0:
        water_tilde_symbol = self.water_tilde_symbols[min(3, water_level)]
        water_tilde_offset = self.water_tilde_offsets[min(3, water_level)]
        if draw_turtle:
          turtle_offset = random.randrange(0, 3 * self.turtle_icon_w)
          turtle_x = canvas.width / 2 - turtle_offset
          turtle_y = canvas.height - self.turtle_icon_h
          water_str = water_tilde_symbol * math.floor(turtle_x / self.water_icon_w)
          draw.text((x, y + water_tilde_offset), water_str, inky.BLACK, font=self.symbola20_font)
          draw.text((turtle_x, turtle_y), self.turtle_icon, inky.BLACK, font=self.symbola40_font)
          left = max(left, turtle_x + self.turtle_icon_w)
          draw_turtle = False

        if (y < wt_bottom):
          left = max(left, wt_right)
        if (y < uv_bottom):
          left = max(left, uv_right)
        num = math.ceil((left - x)/self.water_icon_w)
        remain = 13 - num
        if draw_snail:
          reduce = math.ceil(self.snail_icon_w/self.water_icon_w)
          remain -= reduce
          space = reduce * self.water_icon_w
          offset = random.randrange(self.snail_icon_w, space)
          draw.text((canvas.width - offset, canvas.height - self.snail_icon_h), self.snail_icon, inky.BLACK, font=self.symbola30_font)
          draw_snail = False
        draw.text((x + self.water_icon_w * num, y + water_tilde_offset), water_tilde_symbol * remain, inky.BLACK, font=self.symbola20_font)
        water_level -= 3
        y -= (self.water_icon_h - 4)

      logging.debug(f'Update display')
      self._inky_service.display(canvas)


def main():
  device_names = {
    '28-012115d1f634': 'Air',
    '28-012114259884': 'Water',
  }

  temperatures = {
  }

  DS18B20.start()

  devices = DS18B20.devices

  inky_service = InkyDisplayService()
  inky_service.start()
  turtle_display = TurtleDisplay(inky_service)
  logging.info('Turtle Monitor started')

  i2c = busio.I2C(board.SCL, board.SDA)
  
  ds = data_store.DataStore()

  # Create VEML6075 object using the I2C bus
  veml = veml6075.VEML6075(i2c, integration_time=100)

  distance_sensor = UltrasonicSensor(measure_period=5)
  distance_sensor.start()
  time.sleep(1)
  
  try:
    while True:
      for dev in devices:
        device_id = dev.device_id
        device_name = device_names[device_id]
        temp_c = dev.temperature
        temp_f = dev.fahrenheit(temp_c)

        logging.info(f'{device_name:>7}({device_id}): {temp_c}℃ {temp_f}℉')
        temperatures[device_name] = temp_c

      air_temp = temperatures['Air']
      water_temp = temperatures['Water']

      uva, uvb, uv_index = veml.uv_data
      logging.info(f'uva={uva}, uvb={uvb}, uv_index={uv_index}')

      distance = distance_sensor.distance
      average_distance = distance_sensor.moving_average_distance
      logging.info("distance: {:>5.0f}mm; moving_average: {:>5.0f}mm".format(distance, average_distance))
      ds.add_data(air_temp, water_temp, uva, uvb, distance)
      turtle_display.display(air_temp, water_temp, uva, uvb, average_distance)
      time.sleep(5)
  except KeyboardInterrupt:
    pass

  ds.close()
  distance_sensor.shutdown()
  inky_service.shutdown()
  DS18B20.shutdown()
  logging.info('Turtle Monitor stopped')


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

  main()
