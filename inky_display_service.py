#!/usr/bin/env python3

import inky.phat
import logging
import PIL.Image
import PIL.ImageDraw
import threading


class InkyDisplayCanvas:
  def __init__(self, size, color=inky.WHITE):
    self._image = PIL.Image.new("P", size, color=color)
    self._image.palette.getcolor((255,255,255))
    self._image.palette.getcolor((0,0,0))
    self._draw = None
    
  @property
  def size(self):
    return self._image.size

  @property
  def width(self):
    return self._image.width

  @property
  def height(self):
    return self._image.height

  @property
  def image(self):
    return self._image

  @property
  def draw(self):
    if self._draw is None:
      self._draw = PIL.ImageDraw.Draw(self._image)
    return self._draw

  def clear(self, color=inky.WHITE):
    self._image.paste(color, (0, 0, self._image.width, self._image.height))

  def save(self, path):
    self._image.save(path)


class InkyDisplayService:
  def __init__(self):
    self._running = None
    self._inky_display = inky.phat.InkyPHAT()
    self._inky_display.h_flip = True
    self._inky_display.v_flip = True
    self._display_condition = threading.Condition()
    self._display_thread = threading.Thread(target=self._display_service, name='Turtle Display Service')
    self._display_canvas = None
    self._free_canvases = []
    
  @property
  def running(self):
    return self._running
    
  def start(self):
    if self._running is None:
      self._running = True
      self._display_thread.start()
    else:
      logging.warning('Inky Display Service already started')
    
  def shutdown(self):
    if self._running:
      self._running = False
      with self._display_condition:
        self._display_canvas = None
        self._display_condition.notify()
      self._display_thread.join()
    else:
      logging.warning('Inky Display Service not started')
    
  def get_canvas(self, color=inky.WHITE):
    if self._free_canvases:
      canvas = self._free_canvases.pop()
      canvas.clear(color=color)
    else:
      canvas = InkyDisplayCanvas((self._inky_display.WIDTH, self._inky_display.HEIGHT), color=color)
    return canvas
  
  def display(self, canvas):
    canvas.save('/dev/shm/InkyDisplay.png')
    with self._display_condition:
      if self._display_canvas:
        self._free_canvases.append(self._display_canvas)
      self._display_canvas = canvas
      self._display_condition.notify()
    
  def _display_service(self):
    logging.info('Inky Display Service started')
    while self._running:
      display_image = None
      with self._display_condition:
        self._display_condition.wait()
        if self._display_canvas:
          display_image = self._display_canvas
          self._display_canvas = None
      if display_image:
          self._inky_display.set_image(display_image.image)
          self._inky_display.show()
          self._free_canvases.append(display_image)
    logging.info('Inky Display Service stopped')


if __name__ == "__main__":
  import argparse
  import fonts.ttf
  import PIL.ImageFont
  import time

  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--log-level',
      default=logging.INFO,
      type=lambda x: getattr(logging, x),
      help='Configure the logging level. default: INFO'
  )
  args = parser.parse_args()
  logging.basicConfig(level=args.log_level)

  inky_display_service = InkyDisplayService()
  inky_display_service.start()

  font = PIL.ImageFont.truetype(fonts.ttf.RobotoMedium, 20)

  count = 0
  try:
    while True:
      canvas = inky_display_service.get_canvas()
      text = f'Hello {count}'
      print(text)
      canvas.draw.text((40, 40), text, inky.BLACK, font=font)
      inky_display_service.display(canvas)
      time.sleep(1)
      canvas = inky_display_service.get_canvas()
      text = f'World {count}'
      print(text)
      canvas.draw.text((40, 40), text, inky.BLACK, font=font)
      inky_display_service.display(canvas)
      time.sleep(1)
      count += 1
  except KeyboardInterrupt:
    pass

  inky_display_service.shutdown()