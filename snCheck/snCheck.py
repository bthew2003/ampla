#!/usr/bin/env python
#-*- coding:utf-8 -*-

import time
import serial
import smbus
import RPi.GPIO as GPIO

#from I2C_EEPROM_Class import I2C_EEPROM

class I2C_EEPROM():
	#GPIO Set
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)

	GPIO.setup(40, GPIO.OUT)
	GPIO.output(40, GPIO.HIGH)  #EEPROM Write Protect

	# Get I2C bus
	bus = smbus.SMBus(1)

	# I2C address of the device
	EEPROM_DEFAULT_ADDRESS = 0x50
	EEPROM_DELAY = 0.005

	def read_byte(self, addr):
		""" byte 단위로 읽기  """
		try:
			return self.bus.read_byte_data(self.EEPROM_DEFAULT_ADDRESS, addr)
		except:
			return -1

	def write_byte(self, addr, data):
		""" byte 단위로 쓰기 """
		try:
			GPIO.output(40, GPIO.LOW)
			self.bus.write_byte_data(self.EEPROM_DEFAULT_ADDRESS, addr, data)
			time.sleep(self.EEPROM_DELAY)
			result = 1
		except:
			result = -1
		finally:
			GPIO.output(40, GPIO.HIGH)
			return result

	def read_data(self, addr, len):
		try:
			return self.bus.read_i2c_block_data(self.EEPROM_DEFAULT_ADDRESS, addr, len)
		except:
			return -1

	def write_data(self, addr, data):
		try:
			GPIO.output(40, GPIO.LOW)
			self.bus.write_i2c_block_data(self.EEPROM_DEFAULT_ADDRESS, addr, data)
			time.sleep(self.EEPROM_DELAY)
			result = 1
		except:
			result = -1
		finally:
			GPIO.output(40, GPIO.HIGH)
			return result

##################################################


class serialChk:

	SERIAL_LEN  = 14
	EUID_LEN = 16

	EUID_ADDR_OFFSET = 20

	def getEuidNum(self):
		#read eeprom
		eep = I2C_EEPROM()
		result = []
		for i in range(self.EUID_LEN):
			result.insert(i, eep.read_byte(self.EUID_ADDR_OFFSET + i))

		result = bytes(result).decode('utf-8')
		print ("Euid=" + str(result))

	def getSerialNum(self):
		#read eeprom
		eep = I2C_EEPROM()
		result = []
		for i in range(self.SERIAL_LEN):
			result.insert(i, eep.read_byte(i))

		result = bytes(result).decode('utf-8')
		print ("Serial=" + str(result))

	def setSerialNum(self, seri):
		eep = I2C_EEPROM()

		serStr = seri[0].replace('-', '')
		print ("s0")

		serial = list(serStr)
		print (serial)

		rEuid = self.serial2Euid(serial)
		print (rEuid)

		if rEuid != None:
			#write eeprom - Serial Number
			for i in range(len(serial)):
				eep.write_byte(i, serial[i].encode()[0])
				print (serial[i].encode()[0])

			print ("S0===========")
			#write eeprom - Euid Number (EUID_ADDR_OFFSET)
			for i in range(self.EUID_LEN):
				eep.write_byte(self.EUID_ADDR_OFFSET + i, rEuid[i].encode()[0])
				print (rEuid[i].encode()[0])

			print ("input Serial Value Write Complete")

		else:
			print ("input Serial Value Wrong")


	def serial2Euid(self, serial):
		gwConst = ['B', 'A', 'D', 'F', 'B', 'E', 'C']

		try:
			serialLen = len(serial)
			if serialLen == self.SERIAL_LEN:
				year = int(serial[7]) * 10 + int(serial[8])
				yearStr = format(year, 'X')

				euid = ['A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A']
				euid[0] = gwConst[0]	#B
				euid[1] = serial[5]		#2
				euid[2] = serial[6]		#0
				euid[3] = gwConst[1]	#A
				euid[4] = yearStr			#6
				euid[5] = gwConst[2]	#D
				euid[6] = serial[9]		#1
				euid[7] = serial[10]	#0
				euid[8] = gwConst[3]	#F
				euid[9] = serial[13]	#0
				euid[10] = gwConst[4]	#B
				euid[11] = gwConst[4] #B
				euid[12] = serial[12] #2
				euid[13] = gwConst[5]	#E
				euid[14] = serial[11]	#0
				euid[15] = gwConst[6]	#C
				return euid

			else:
				return None

		except:
			print ("Except year")
			return None



s = serialChk()
s.getEuidNum()
#s.getSerialNum()
