#!/usr/bin/env python
#-*- coding:utf-8 -*-

import time
import serial
import smbus
import binascii
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


class SNCHECK():
	SERIAL_LEN  = 14

	EUID_ADDR_OFFSET = 20
	EUID_LEN = 16

	DHCP_ADDR_OFFSET = 38
	DHCP_LEN = 1

	STATIC_ADDR_OFFSET = 41
	STATIC_LEN = 16

	TLS_ADDR_OFFSET = 58
	TLS_LEN = 1

	PORT_ADDR_OFFSET = 61
	PORT_LEN = 7

	SERV_ADDR_OFFSET = 70
	SERV_LEN = 40

	SSID1_ADDR_OFFSET = 112
	SSID1_LEN = 40
	PASSWD1_ADDR_OFFSET = 154
	PASSWD1_LEN = 20

	SSID2_ADDR_OFFSET = 174
	SSID2_LEN = 40
	PASSWD2_ADDR_OFFSET = 216
	PASSWD2_LEN = 20



	MAX_EEPROM_SIZE = 256

	def getEuidNum(self):
		#read eeprom
		eep = I2C_EEPROM()
		result = []
		for i in range(self.EUID_LEN):
			result.insert(i, eep.read_byte(self.EUID_ADDR_OFFSET + i))
		result = bytes(result).decode('utf-8')
		return result

	def getSerialNum(self):
		#read eeprom
		eep = I2C_EEPROM()
		result = []
		for i in range(self.SERIAL_LEN):
			result.insert(i, eep.read_byte(i))

		result = bytes(result).decode('utf-8')
		return result

	def setSerialNum(self, seri):
		eep = I2C_EEPROM()

		serStr = seri.replace('-', '')
		serial = list(serStr)
		rEuid = self.serial2Euid(serial)
		print (serial)
		print (rEuid)

		if rEuid != None and self.SERIAL_LEN == len(serial):
			#write eeprom - Serial Number
			for i in range(self.SERIAL_LEN):
				eep.write_byte(i, serial[i].encode()[0])
				print (serial[i].encode()[0])

			print ("S0===========")
			#write eeprom - Euid Number (EUID_ADDR_OFFSET)
			for i in range(self.EUID_LEN):
				eep.write_byte(self.EUID_ADDR_OFFSET + i, rEuid[i].encode()[0])
				print (rEuid[i].encode()[0])

#			print ("input Serial Value Write Complete")

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

	def writeValue(self, idx, length, value):
		try:
			eep = I2C_EEPROM()

			#print ("writeVal : " + str(range(length)))
			#print (value)

			strLen = len(value)
			for i in (range(length)):
				if i < strLen:	tempVal = value[i].encode()[0]
				else:	tempVal = 255
				eep.write_byte(idx + i, tempVal)
				#print ("[" + str(i) + "] " + str(tempVal))

#			print ("EEPROM Value Write Complete")

		except:
			print ("Except_writeValue")

	def readValue(self, idx, length):
		try:
			eep = I2C_EEPROM()
			result = []
			for i in range(length):
				if 255 !=  eep.read_byte(idx + i):
					result.insert(i, eep.read_byte(idx + i))
		except:
			print ("Except_readValue")

		return bytes(result)

	def readAllEeprom(self):
		try:
			eepromVal = []
			eep = I2C_EEPROM()
			for i in range(self.MAX_EEPROM_SIZE):
				eepromVal.insert(i, eep.read_byte(i))
			print (eepromVal)
		except:
			print ("Except_readAllEeprom")


	#get/set DHCP
	def getDHCP(self):
		try:
			result = (self.readValue(self.DHCP_ADDR_OFFSET, self.DHCP_LEN))
			return (result.decode('utf-8'))
		except: print ("Except_getDHCP")

	def setDHCP(self, value):
		try:
			if self.DHCP_LEN == len(value):	self.writeValue(self.DHCP_ADDR_OFFSET, self.DHCP_LEN, value)
			else:	print ("Set Value Wrong")
		except:	print ("Except_setDHCP")

	#get/set StaticIp
	def getStaticIp(self):
		try:
			result = self.readValue(self.STATIC_ADDR_OFFSET, self.STATIC_LEN)
			return (result.decode('utf-8'))
		except: print ("Except_getStaticIP")

	def setStaticIp(self, value):
		try:
			if self.STATIC_LEN >= len(value): self.writeValue(self.STATIC_ADDR_OFFSET, self.STATIC_LEN, value)
			else: print ("Set Value Wrong")
		except:	print ("Except_setStaticIp")

	#get/set TLS
	def getTLS(self):
		try:
			result = self.readValue(self.TLS_ADDR_OFFSET, self.TLS_LEN)
			return (result.decode('utf-8'))
		except: print ("Except_getTLS")

	def setTLS(self, value):
		try:
			if self.TLS_LEN == len(value): self.writeValue(self.TLS_ADDR_OFFSET, self.TLS_LEN, value)
			else: print ("Set Value Wrong")
		except:	print ("Except_setTLS")

	#get/set Port
	def getPort(self):
		try:
			result = (self.readValue(self.PORT_ADDR_OFFSET, self.PORT_LEN))
			return (result.decode('utf-8'))
		except: print ("Except_getPort")

	def setPort(self, value):
		try:
			if self.PORT_LEN >= len(value): self.writeValue(self.PORT_ADDR_OFFSET, self.PORT_LEN, value)
			else: print ("Set Value Wrong")
		except: print ("Except_setPORT")

	#get/set Server Address
	def getServ(self):
		try:
			result = (self.readValue(self.SERV_ADDR_OFFSET, self.SERV_LEN))
			return (result.decode('utf-8'))
		except: print ("Except_getServ")

	def setServ(self, value):
		try:
			if self.SERV_LEN >= len(value): self.writeValue(self.SERV_ADDR_OFFSET, self.SERV_LEN, value)
			else: print ("Set Value Wrong")
		except: print ("Except_setSERV")

	#get/set wifi#1 SSID
	def getSSID1(self):
		try:
			result = (self.readValue(self.SSID1_ADDR_OFFSET, self.SSID1_LEN))
			return (result.decode('utf-8'))
		except: print ("Except_getSSID1")

	def setSSID1(self, value):
		try:
			if self.SSID1_LEN >= len(value): self.writeValue(self.SSID1_ADDR_OFFSET, self.SSID1_LEN, value)
			else: print ("Set Value Wrong")
		except: print ("Except_setSSID1")

	#get/set wifi#1 PASSWD
	def getPASSWD1(self):
		try:
			result = (self.readValue(self.PASSWD1_ADDR_OFFSET, self.PASSWD1_LEN))
			return (result.decode('utf-8'))
		except: print ("Except_getPASSWD1")

	def setPASSWD1(self, value):
		try:
			if self.PASSWD1_LEN >= len(value): self.writeValue(self.PASSWD1_ADDR_OFFSET, self.PASSWD1_LEN, value)
			else: print ("Set Value Wrong")
		except: print ("Except_setPASSWD1")

	#get/set wifi#2 SSID
	def getSSID2(self):
		try:
			result = (self.readValue(self.SSID2_ADDR_OFFSET, self.SSID2_LEN))
			return (result.decode('utf-8'))
		except: print ("Except_getSSID2")

	def setSSID2(self, value):
		try:
			if self.SSID2_LEN >= len(value): self.writeValue(self.SSID2_ADDR_OFFSET, self.SSID2_LEN, value)
			else: print ("Set Value Wrong")
		except: print ("Except_setSSID2")

	#get/set wifi#2 PASSWD
	def getPASSWD2(self):
		try:
			result = (self.readValue(self.PASSWD2_ADDR_OFFSET, self.PASSWD2_LEN))
			return (result.decode('utf-8'))
		except: print ("Except_getPASSWD2")

	def setPASSWD2(self, value):
		try:
			if self.PASSWD2_LEN >= len(value): self.writeValue(self.PASSWD2_ADDR_OFFSET, self.PASSWD2_LEN, value)
			else: print ("Set Value Wrong")
		except: print ("Except_setPASSWD2")




################################################################


#main (Test)
#s = SNCHECK()
#print ("EUID : " + s.getEuidNum())
#print ("SERIAL : " + s.getSerialNum()

#s.setSerialNum("GWKZ0200729007")

#s.setDHCP("2")
#print ("DHCP :" + s.getDHCP())

#s.setStaticIp("192.168.0.9")
#print ("IP : " + s.getStaticIp())

#s.setServ("hsrnd02.iptime.org")
#print ("Server : " + s.getServ())

#s.setPort("1883")
#print ("Port : " + s.getPort())

#s.setSSID1("hsrnd")
#print ("ssid#1 : " + s.getSSID1())

#s.setPASSWD1("hsrnd000")
#print ("passwd#1 : " + s.getPASSWD1())

#s.setSSID2("hsrnd1")
#print ("ssid#2 : " + s.getSSID2())

#s.setPASSWD2("hsrnd111")
#print ("passwd#2 : " + s.getPASSWD2())

#s.readAllEeprom()

