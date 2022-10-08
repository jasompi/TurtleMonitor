#!/usr/bin/env python3
import array

class MovingAverage:
  def __init__(self, window_size=1):
    self._window_size = max(window_size, 1)
    self._values = array.array('d', [0 for _ in range(self._window_size)])
    self._count = 0
    self._sum = 0
  
  @property
  def window_size(self):
    return self._window_size
  
  @property
  def average(self):
    return self._sum / max(min(self._count, self._window_size), 1)

  @property
  def count(self):
    return self._count

  @property
  def filled(self):
    return self._count >= self._window_size

  def add(self, value):
    index = self._count % self._window_size
    self._sum += value - self._values[index]
    self._values[index] = value
    self._count += 1


if __name__ == "__main__":
  import unittest
  import random
  
  class SimpleTest(unittest.TestCase):
    def testNoWindow(self):
      ma = MovingAverage(0)
      self.assertEqual(ma.window_size, 1)
      self.assertEqual(ma.average, 0)
      self.assertEqual(ma.count, 0)
      self.assertFalse(ma.filled)
      for _ in range(10):
        r = random.random()
        ma.add(r)
        self.assertEqual(ma.average, r)
        self.assertTrue(ma.filled)

    def testMovingAverage(self):
      ma = MovingAverage(5)
      self.assertEqual(ma.window_size, 5)
      self.assertEqual(ma.average, 0)
      self.assertEqual(ma.count, 0)
      self.assertFalse(ma.filled)

      ma.add(7)
      self.assertEqual(ma.count, 1)
      self.assertFalse(ma.filled)
      self.assertEqual(ma.average, 7.0)

      ma.add(8)
      self.assertEqual(ma.count, 2)
      self.assertFalse(ma.filled)
      self.assertEqual(ma.average, 7.5)

      ma.add(9)
      self.assertEqual(ma.count, 3)
      self.assertFalse(ma.filled)
      self.assertEqual(ma.average, 8.0)

      ma.add(10)
      self.assertEqual(ma.count, 4)
      self.assertFalse(ma.filled)
      self.assertEqual(ma.average, 8.5)

      ma.add(11)
      self.assertEqual(ma.count, 5)
      self.assertTrue(ma.filled)
      self.assertEqual(ma.average, 9.0)

      ma.add(12)
      self.assertEqual(ma.count, 6)
      self.assertTrue(ma.filled)
      self.assertEqual(ma.average, 10.0)

      ma.add(0)
      self.assertEqual(ma.count, 7)
      self.assertTrue(ma.filled)
      self.assertEqual(ma.average, 42.0/5)

      ma.add(0)
      self.assertEqual(ma.count, 8)
      self.assertTrue(ma.filled)
      self.assertEqual(ma.average, 33.0/5)

      ma.add(-12)
      self.assertEqual(ma.count, 9)
      self.assertTrue(ma.filled)
      self.assertEqual(ma.average, 11.0/5)

      ma.add(-12)
      self.assertEqual(ma.count, 10)
      self.assertTrue(ma.filled)
      self.assertEqual(ma.average, -12.0/5)

  unittest.main()

