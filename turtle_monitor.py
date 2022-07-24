#!/usr/bin/env python3

import adafruit_veml6075 as veml6075
import adafruit_ads1x15.ads1015 as ADS
import adafruit_ads1x15.analog_in as analog_in
import argparse
import board
import busio
import fonts.ttf
import glob
import inky.phat
import logging
import math
import os
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import threading
import time
from inky_display_service import InkyDisplayService


parser = argparse.ArgumentParser()
parser.add_argument(
    '--log-level',
    default=logging.INFO,
    type=lambda x: getattr(logging, x),
    help='Configure the logging level. default: INFO'
)
args = parser.parse_args()
logging.basicConfig(level=args.log_level)


i2c = busio.I2C(board.SCL, board.SDA)

# Create VEML6075 object using the I2C bus
veml = veml6075.VEML6075(i2c, integration_time=100)

# Create the ADC object using the I2C bus
ads = ADS.ADS1015(i2c)
# set gain to 2x since the range is 0 ~ 1.6v

# Create single-ended input on channel 0
chan = analog_in.AnalogIn(ads, ADS.P0)

HIGH_LEVEL = 1.6
HIGH_THRESHOLD = 1.5

LOW_THRESHOLD = 0.5
LOW_LEVEL = 0


def fahrenheit(celsius):
  return celsius * 9.0 / 5.0 + 32.0


class TurtleDisplay:
  def load_image(name):
    # Get the current path
    PATH = os.path.dirname('.')
    return PIL.Image.open(os.path.join(PATH, f'{name}.png')).resize((24, 24))

    # Load the font
  font = PIL.ImageFont.truetype(fonts.ttf.RobotoMedium, 20)
  symbola20_font = PIL.ImageFont.truetype('/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf', 20)
  symbola40_font = PIL.ImageFont.truetype('/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf', 30)
  # Load images and icons
  uv_icon = load_image('UV')
  air_icon = '🌡'
  water_wave_icon = '🌊'
  fill_water_icon = '🚰'
  turtle_icon = '🐢'
  water_tilde_symbols = ' ∼≈≋'
  water_tilde_offsets = [0, 6, 3, 0]
  caption_width_ratio = 0.35
  water_icon_w, water_icon_h = symbola20_font.getsize(water_tilde_symbols[3])
  fill_water_w, fill_water_h = symbola20_font.getsize(fill_water_icon)
  turtle_icon_w, turtle_icon_h = symbola40_font.getsize(turtle_icon)

  def __init__(self, inky_service):
    self._inky_service = inky_service
    self._air_temp_str = ''
    self._water_temp_str = ''
    self._uv_str = ''
    self._water_level = -1

  def display(self, air_temp, water_temp, uva, uvb, water_voltage):
    water_level = min(17, round(water_voltage * 10))
    logging.debug(f'water_level = {water_level}')
   
    air_temp_str = f': {round(air_temp)}℃ {round(fahrenheit(air_temp))}℉'
    water_temp_str = f': {round(water_temp)}℃ {round(fahrenheit(water_temp))}℉'
    uv_str = f': {round(uva)}(A) {round(uvb)}(B)'
  
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
      while water_level >= 0:
        water_tilde_symbol = self.water_tilde_symbols[min(3, water_level)]
        water_tilde_offset = self.water_tilde_offsets[min(3, water_level)]
        water_str = water_tilde_symbol * 5
        if draw_turtle:
          draw.text((x, y + water_tilde_offset), water_str, inky.BLACK, font=self.symbola20_font)
          turtle_x = canvas.width / 2 - self.turtle_icon_w / 2
          turtle_y = y + self.water_icon_h - self.turtle_icon_h
          draw.text((turtle_x, turtle_y), self.turtle_icon, inky.BLACK, font=self.symbola40_font)
          left = max(left, turtle_x + self.turtle_icon_w)
          draw_turtle = False

        if (y < wt_bottom):
          left = max(left, wt_right)
        if (y < uv_bottom):
          left = max(left, uv_right)
        num = math.ceil((left - x)/self.water_icon_w)
        remain = 13 - num
        draw.text((x + self.water_icon_w * num, y + water_tilde_offset), water_tilde_symbol * remain, inky.BLACK, font=self.symbola20_font)
        water_level -= 3
        y -= (self.water_icon_h - 4)

      self._inky_service.display(canvas)


base_dir = '/sys/bus/w1/devices/'

def read_first_line(device_folder, filename):
  with open(device_folder + '/' + filename, 'r') as f:
    return next(iter(f.readlines()), None)

def read_name(device_folder):
  return read_first_line(device_folder, 'name')

def read_temp_raw(device_folder):
  return read_first_line(device_folder, 'temperature')

def read_temp(device_folder):
    temp_raw = read_temp_raw(device_folder)
    if temp_raw:
        temp_c = float(temp_raw) / 1000.0
        return temp_c

device_names = {
  '28-012115d1f634': 'Water',
  '28-012114259884': 'Air',
}

temperatures = {
}

inky_service = InkyDisplayService()
inky_service.start()
turtle_display = TurtleDisplay(inky_service)
logging.info('Turtle Monitor started')

try:
  while True:
    for device_folder in glob.glob(base_dir + '28*'):
      device_id = (read_name(device_folder) or '').strip()
      device_name = device_names[device_id]
      temp_c = read_temp(device_folder)
      temp_f = fahrenheit(temp_c)

      logging.debug(f'{device_name:>7}({device_id}): {temp_c}℃ {temp_f}℉')
      temperatures[device_name] = temp_c

    air_temp = temperatures['Air']
    water_temp = temperatures['Water']
    uva, uvb, uv_index = veml.uv_data
    logging.debug(f'uva={uva}, uvb={uvb}, uv_index={uv_index}')

    voltage = chan.voltage
    logging.debug("voltage: {:>5.3f}".format(voltage))

    turtle_display.display(air_temp, water_temp, uva, uvb, voltage)
    time.sleep(1)
except KeyboardInterrupt:
  pass

inky_service.shutdown()
logging.info('Turtle Monitor stopped')