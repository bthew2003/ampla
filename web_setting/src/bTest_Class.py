import RPi.GPIO as GPIO
import time
import signal
import sys
import serial
import re
#import smbus

from I2C_EEPROM_Class import I2C_EEPROM

class serialClass:
	SERIAL_LEN = 14

	def getSerialNum(self):
		eep = I2C_EEPROM()

		#read eeprom
		result = []
		for idx in range(self.SERIAL_LEN):
			result.insert(idx, eep.read_byte(idx))

		result = bytes(result).decode('utf-8')
		#print ("getSerial : " + result)
		print ("getSerial : " + str(result))

	def setSerialNum(self, euid):
		eep = I2C_EEPROM()

		#euid(str)
		#euid = "b827ebfffe86b856"
		bEuid = euid[0].encode()
		print (bEuid)

		#write eeprom - eeprom Start Address
		inputLen = len(bEuid)

		if inputLen == self.SERIAL_LEN:
			idx = 0
			for i in range(inputLen):
				eep.write_byte(idx, bEuid[i])
				idx += 1



#main#######################################################
s = serialClass()
s.getSerialNum()
