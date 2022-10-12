import logging
import mysql.connector

CREATE_STATEMENT = """
CREATE TABLE IF NOT EXISTS environment (
  id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT,
  ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  air_temp DECIMAL(3,1),
  water_temp DECIMAL(3,1),
  uva DECIMAL(4) UNSIGNED,
  uvb DECIMAL(4) UNSIGNED,
  water_dist DECIMAL(3) UNSIGNED,
  PRIMARY KEY (id)
);
"""

INSERT_STATEMENT = 'INSERT INTO environment (air_temp, water_temp, uva, uvb, water_dist) VALUES (%s, %s, %s, %s, %s)'

class DataStore:
  def __init__(self):
    self._connection = mysql.connector.connect(read_default_file='/home/pi/.my.cnf')
    self._cursor = self._connection.cursor()
    self._cursor.execute(CREATE_STATEMENT)

  def add_data(self, air_temp, water_temp, uva, uvb, water_dist):
    try:
      data = (air_temp, water_temp, uva, uvb, water_dist)
      self._cursor.execute(INSERT_STATEMENT, data)
      self._connection.commit()
      logging.debug('Successfully added entry to database')
    except mysql.connector.Error as e:
      logging.error(f'Error adding entry to database: {e}')
      
  def close(self):
    self._connection.close()



if __name__ == "__main__":
  import argparse

  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--log-level',
      default=logging.INFO,
      type=lambda x: getattr(logging, x),
      help='Configure the logging level. default: INFO'
  )
  args = parser.parse_args()
  logging.basicConfig(level=args.log_level)

  ds = DataStore()
  ds.add_data(27.234, 24.982, 100.4, 125.8, 69.777)
  ds.add_data(26.123, 24.021, 98.4, 120.8, 70.77)
  ds.close()