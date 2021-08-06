#!/usr/bin/python --------------------------------------
#    ___ ___ _ ____ / _ \/ _ \(_) __/__ __ __ / , _/ ___/ /\ \/ _ \/ // / /_/|_/_/ /_/___/ .__/\_, /
#                /_/ /___/
#
#  lcd_i2c.py LCD test script using I2C backpack. Supports 16x2 and 20x4 screens.
#
# Author : Matt Hawkins Date : 20/09/2015
#
# http://www.raspberrypi-spy.co.uk/
#
# Copyright 2015 Matt Hawkins
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------
import smbus
import time
import string
import socket, fcntl, struct
import subprocess
import os

from I2C_EEPROM_Class import I2C_EEPROM

class lcd_Class:

	# Define some device parameters
	I2C_ADDR = 0x27 # I2C device address
	I2C_ADDR = 0x3f # I2C device address
	LCD_WIDTH = 16 # Maximum characters per line

	# Define some device constants
	LCD_CHR = 1 # Mode - Sending data
	LCD_CMD = 0 # Mode - Sending command

	LCD_LINE_1 = 0x80 # LCD RAM address for the 1st line
	LCD_LINE_2 = 0xC0 # LCD RAM address for the 2nd line
	LCD_LINE_3 = 0x94 # LCD RAM address for the 3rd line
	LCD_LINE_4 = 0xD4 # LCD RAM address for the 4th line

	LCD_BACKLIGHT = 0x08 # On
	#LCD_BACKLIGHT = 0x00 # Off

	ENABLE = 0b00000100 # Enable bit

	# Timing constants
	E_PULSE = 0.0005
	E_DELAY = 0.0005

	#Open I2C interface
	#bus = smbus.SMBus(0) # Rev 1 Pi uses 0
	bus = smbus.SMBus(1) # Rev 2 Pi uses 1

	flag = 0
	lcd_Status = 0

	network_Status = [0,0,0]
	readStr = os.popen('cat /opt/semtech/ampla/version').read()
	version = readStr[0:readStr.find("\n")].rstrip()
	version = version[version.find(':')+1:len(version)].strip()
	#print ("version:" + version)

	date = readStr[readStr.find("\n")+1:len(readStr)].rstrip()
	date = date[date.find(':')+1:len(date)].strip()
	#print ("date:" + date)

	#EEPROM Handle
	eepHandle = I2C_EEPROM()
	SERIAL_LEN  = 14
	EUID_LEN = 16
	EUID_ADDR_OFFSET = 20
	serialNum = ""

	def lcd_init(self):
		# Initialise display
		self.lcd_byte(0x33,0) # 110011 Initialise
		self.lcd_byte(0x32,0) # 110010 Initialise
		self.lcd_byte(0x06,0) # 000110 Cursor move direction
		self.lcd_byte(0x0C,0) # 001100 Display On,Cursor Off, Blink Off
		self.lcd_byte(0x28,0) # 101000 Data length, number of lines, font size
		self.lcd_byte(0x01,0) # 000001 Clear display
		time.sleep(self.E_DELAY)

		self.serialNum = self.getSerialNum()

	def lcd_byte(self, bits, mode):
		# Send byte to data pins
		# bits = the data
		# mode = 1 for data
		#        0 for command
		bits_high = mode | (bits & 0xF0) | self.LCD_BACKLIGHT
		bits_low = mode | ((bits<<4) & 0xF0) | self.LCD_BACKLIGHT

		# High bits
		self.bus.write_byte(self.I2C_ADDR, bits_high)
		self.lcd_toggle_enable(bits_high)

		# Low bits
		self.bus.write_byte(self.I2C_ADDR, bits_low)
		self.lcd_toggle_enable(bits_low)

	def lcd_toggle_enable(self, bits):
		# Toggle enable
		time.sleep(self.E_DELAY)
		self.bus.write_byte(self.I2C_ADDR, (bits | self.ENABLE))
		time.sleep(self.E_PULSE)
		self.bus.write_byte(self.I2C_ADDR,(bits & ~self.ENABLE))
		time.sleep(self.E_DELAY)

	def lcd_string(self, message,line):
		# Send string to display
		message = message.ljust(self.LCD_WIDTH," ")
		self.lcd_byte(line, self.LCD_CMD)
		for i in range(self.LCD_WIDTH):
			self.lcd_byte(ord(message[i]), self.LCD_CHR)

	def get_ipAddr(self, network):
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		try:
			#ipaddr = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', network[:15]))[20:24])
			ipaddr = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8917, struct.pack('256s', bytes(network[:15], 'utf-8')))[20:24])  #python3
		except IOError:
			ipaddr = "127.0.0.1"
		s.close()
		return ipaddr

	def get_macAddr(self):
		mac = open('/sys/class/net/eth0/address').read()
		return mac

	def ipcheck(self):
		return check_output(['hostname', '-I'])

	def process_chk(self, pName):
		result = 0
		try:
			result = subprocess.check_output('pgrep ' + pName, shell=True)
			#result = subprocess.check_output(pName, shell=True)
		except subprocess.CalledProcessError as e:
			result = 0
		return result


	def getEuidNum(self):
		#read eeprom
		result = []
		for i in range(self.EUID_LEN):  result.insert(i, self.eepHandle.read_byte(self.EUID_ADDR_OFFSET + i))

		result = bytes(result).decode('utf-8')
		self.rs485Trans("getEuid : " + str(result))
		return result

	def getSerialNum(self):
		#read eeprom
		result = []
		for i in range(self.SERIAL_LEN):  result.insert(i, self.eepHandle.read_byte(i))
		result = bytes(result).decode('utf-8')
		return result

	def lcd_print(self):
		lcd_1Str = ""
		lcd_2Str = ""

		#eth0 Mac Address Read
		mac = self.get_macAddr()
		macAdd = " " + "{0:>14}".format(mac.replace(":", "")[0:12])

		#Gateway status Check
		proc = self.process_chk("lora_pkt_fwd")
		if proc == 0: lcd_2Str = " P- "
		else: lcd_2Str = " P+ "

		proc = self.process_chk("chirpstack-net")
		if proc == 0: lcd_2Str += "N- "
		else: lcd_2Str += "N+ "

		proc = self.process_chk("chirpstack-app")
		if proc == 0: lcd_2Str += "A- "
		else: lcd_2Str += "A+ "

		#eth0 IP Address Read
		ipEth = self.get_ipAddr('eth0').strip()
		ipEth0 = "E " + "{0:>14}".format(ipEth)

		if ipEth == "127.0.0.1":	self.network_Status[0] = 0
		else:											self.network_Status[0] = 1

		#wLan0 Ip Address Read
		ipwLan = self.get_ipAddr('wlan0').strip()
		ipwLan = "W " + "{0:>14}".format(ipwLan)

		if ipwLan == "127.0.0.1":
			ipwLan = self.get_ipAddr('wlan1')
			self.network_Status[1] = 0
		else:
			self.network_Status[1] = 1

		#wWan0 Ip Address Read
		ipwWan = self.get_ipAddr('wwan0').strip()
		ipwWan = "L " + "{0:>14}".format(ipwWan)

		if ipwWan == "127.0.0.1":	self.network_Status[2] = 0
		else:											self.network_Status[2] = 1

		cTempStr = os.popen('cat /sys/class/thermal/thermal_zone0/temp').read()
		cTemp = str(round(int(cTempStr) / 1000, 1))
		lcd_2Str += cTemp

		#Lcd Init & Print
		try:
			#print ("try")
			if self.lcd_Status == 0:
				self.lcd_init()
				self.lcd_Status = 1

			lcd_1Str = "                "
			lcd_2Str = "                "

			if self.flag == 0:
				self.flag += 1
				lcd_1Str = ipEth0
				lcd_2Str = "       ver " + self.version
			elif self.flag == 1:
				self.flag += 1
				lcd_1Str = ipwLan
				lcd_2Str = "   date " + self.date
			else:
				self.flag = 0
				lcd_1Str = ipwWan
				lcd_2Str = "  " + self.serialNum

			self.lcd_string(lcd_1Str[0:16], self.LCD_LINE_1)
			self.lcd_string(lcd_2Str[0:16], self.LCD_LINE_2)

		except:
			self.lcd_Status = 0
			#print ("except_LCD")


	def lcd_reset(self):
		self.lcd_init()

		lcd_1Str = " Ampla GW Reset "
		lcd_2Str = " 30s Wait..     "
		self.lcd_string(lcd_1Str[0:16], self.LCD_LINE_1)
		self.lcd_string(lcd_2Str[0:16], self.LCD_LINE_2)


#if __name__ == '__main__':
#	t1 = lcd_Class()
#	print (t1.get_macAddr())
#
#	while True:
#		t1.lcd_print()
#		time.sleep(1)
#		print ("while")



