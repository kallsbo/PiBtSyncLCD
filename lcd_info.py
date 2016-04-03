#!/usr/bin/python
#
# lcd_info.py
# Script for displaying status for Btsync client running on a Raspberry or Banana Pi.
#
# Author: Kristofer Källsbo
# Date: 2016-04-02
# http://www.hackviking.com
#
# LCD code based on Matt Hawkins lcd_i2c.py
# https://bitbucket.org/MattHawkinsUK/rpispy-misc/raw/master/python/lcd_i2c.py
#
# Copyright 2016 Kristofer Källsbo
# Copyright 2015 Matt Hawkins
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#--------------------------------------
import smbus
import time
import socket
import fcntl
import struct
import os
import subprocess
import os.path
import requests
import json
from lxml import html

# Configuration - LCD
LCD_BUS = 2 # The bus that the LCD is connected to. (Raspberry Pi usually 1, Banana Pi usually 2 - can be checked with i2cdetect)
LCD_I2C_ADDR = 0x27 # I2C device address of the LCD, use i2cdetect to find your displays address
LCD_WIDTH = 20 # Number of characters that each line can handle
LCD_BACKLIGHT  = 0x08  # On
#LCD_BACKLIGHT = 0x00  # Off

# Enviorment config
NETWORK_NIC = "eth0" # Network card used
TRUECRYPT_MOUNT_PATH = "/mnt/tc_disk" # path where the truecrypt disk is mounted
BTSYNC_SRV_NAME = "btsync" # name of the btsync service
BTSYNC_URL = "https://localhost:8888/gui/" # Web GUI address for btsync
BTSYNC_CRED_FILE = "/mnt/tc_disk/btsync_cred.json" # JSON file with btsync credentials

# Define BTSYNC vars
BTSYNC_USR = ""
BTSYNC_PSW = ""
BTSYNC_TOKEN = ""
BTSYNC_SESSION = requests.Session()

# Define some device constants
LCD_CHR = 1 # Mode - Sending data
LCD_CMD = 0 # Mode - Sending command

LCD_LINE_1 = 0x80 # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0 # LCD RAM address for the 2nd line
LCD_LINE_3 = 0x94 # LCD RAM address for the 3rd line
LCD_LINE_4 = 0xD4 # LCD RAM address for the 4th line

LCD_BACKLIGHT  = 0x08  # On
#LCD_BACKLIGHT = 0x00  # Off

ENABLE = 0b00000100 # Enable bit

# Timing constants
E_PULSE = 0.0005
E_DELAY = 0.0005

#Open I2C interface
bus = smbus.SMBus(LCD_BUS) # Rev 2 Pi uses 1

def lcd_init():
  # Initialise display
  lcd_byte(0x33,LCD_CMD) # 110011 Initialise
  lcd_byte(0x32,LCD_CMD) # 110010 Initialise
  lcd_byte(0x06,LCD_CMD) # 000110 Cursor move direction
  lcd_byte(0x0C,LCD_CMD) # 001100 Display On,Cursor Off, Blink Off 
  lcd_byte(0x28,LCD_CMD) # 101000 Data length, number of lines, font size
  lcd_byte(0x01,LCD_CMD) # 000001 Clear display
  time.sleep(E_DELAY)

def lcd_byte(bits, mode):
  # Send byte to data pins
  # bits = the data
  # mode = 1 for data
  #        0 for command

  bits_high = mode | (bits & 0xF0) | LCD_BACKLIGHT
  bits_low = mode | ((bits<<4) & 0xF0) | LCD_BACKLIGHT

  # High bits
  bus.write_byte(LCD_I2C_ADDR, bits_high)
  lcd_toggle_enable(bits_high)

  # Low bits
  bus.write_byte(LCD_I2C_ADDR, bits_low)
  lcd_toggle_enable(bits_low)

def lcd_toggle_enable(bits):
  # Toggle enable
  time.sleep(E_DELAY)
  bus.write_byte(LCD_I2C_ADDR, (bits | ENABLE))
  time.sleep(E_PULSE)
  bus.write_byte(LCD_I2C_ADDR,(bits & ~ENABLE))
  time.sleep(E_DELAY)

def lcd_string(message,line):
  # Send string to display

  message = message.ljust(LCD_WIDTH," ")

  lcd_byte(line, LCD_CMD)

  for i in range(LCD_WIDTH):
    lcd_byte(ord(message[i]),LCD_CHR)

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

def is_truecrypt_mounted(path):
    if os.path.ismount(path):
        return "OK"
    else:
        return "NO"

def is_service_running(srv_name):
    output = subprocess.check_output(['ps', '-A'])
    if srv_name in output:
        return "OK"
    else:
        return "NO"

def get_btsync_cred():
    global BTSYNC_USR
    global BTSYNC_PSW
    
    if not os.path.isfile(BTSYNC_CRED_FILE):
        return "Err: CF NF"
    
    with open(BTSYNC_CRED_FILE, "r") as credFile:
	data = credFile.read()
	cred = json.loads(data)
        BTSYNC_USR = cred['BTSYNC_USR']
        BTSYNC_PSW = cred['BTSYNC_PSW']
        credFile.close()

def get_btsync_token():
    global BTSYNC_TOKEN
    authResponse = None
    
    try:
        authResponse = BTSYNC_SESSION.get(BTSYNC_URL + "token.html", auth=(BTSYNC_USR, BTSYNC_PSW), verify=False)
        tree = html.fromstring(authResponse.content)
        token_result = tree.xpath('//div[@id="token"]/text()')
    except:
        return "Err: Token"
    finally:
        if not (authResponse is None):
            authResponse.close()
        
    if len(token_result) > 0:
        BTSYNC_TOKEN = token_result[0]
    else:
        return "Err: No Token"
    
def get_btsync_info(LLforSpeed, LLforFiles):
  url = BTSYNC_URL + "?token=" + BTSYNC_TOKEN +"&action=getsyncfolders&discovery=1&t=" + str(int(time.time()))
  response = None
  
  try:
    # Get info
    response = BTSYNC_SESSION.get(url, auth=(BTSYNC_USR, BTSYNC_PSW), verify=False)
    info = json.loads(response.content)

    # Get speed
    downspeed = float(info['speed']['downspeed']) / 1024 / 1024
    upspeed = float(info['speed']['upspeed']) / 1024 / 1024

    # Get files
    files = 0
    files_down = 0
    
    for folder in info['folders']:
      files += int(folder['files'])

      if 'peers' in folder.keys():
        for peer in folder['peers']:
          if 'downfiles' in peer.keys():
            files_down += int(peer['downfiles'])
  except:
    return "Err: Get info"
  finally:
    if not (response is None):
      response.close()
    
  lcd_string("D:" + str("%.1f" % downspeed) + "M/s" + " U:" + str("%.1f" % upspeed) + "M/s", LLforSpeed)
  lcd_string("F:" + str(files) + " FD:" + str(files_down), LLforFiles)

def main():
  # Main program block

  # Initialise display
  lcd_init()

  # Define update counter
  update = 16
  
  while True:
    if update > 15:
      # Set ip & Service status
      lcd_string("IP: " + get_ip_address(NETWORK_NIC), LCD_LINE_1)
      lcd_string("TCM: " + is_truecrypt_mounted(TRUECRYPT_MOUNT_PATH) + "   BTSYNC: " + is_service_running(BTSYNC_SRV_NAME), LCD_LINE_2)
      # Connect to BTSYNC
      cred = get_btsync_cred()
      token = get_btsync_token()
      # Reset update counter
      update = 0
    
    if cred != None and token != None:
      lcd_string(cred, LCD_LINE_3)
      lcd_string(token, LCD_LINE_4)
    else:
      get_btsync_info(LCD_LINE_4, LCD_LINE_3)
    update += 1
    time.sleep(3)
  


if __name__ == '__main__':

  try:
    main()
  except KeyboardInterrupt:
    pass
  finally:
    lcd_byte(0x01, LCD_CMD)
