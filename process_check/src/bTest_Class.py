import RPi.GPIO as GPIO
import time
import signal
import sys
import serial
import re
#import smbus

from I2C_EEPROM_Class import I2C_EEPROM

class serialClass:
	SERIAL_LEN  = 14
	EUID_LEN = 16
	EUID_ADDR_OFFSET = 20

	#GEuid Path
	jsonPath = '/opt/semtech/packet_forwarder/lora_pkt_fwd/local_conf.json'


	def serial2Euid(self, serial):
		gwConst = ['B', 'A', 'D', 'F', 'B', 'E', 'C']

		try:
			serialLen = len(serial)
			if serialLen == self.SERIAL_LEN:
				year = int(serial[7]) * 10 + int(serial[8])
				yearStr = format(year, 'X')

				euid = ['A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A']
				euid[0] = gwConst[0]  #B
				euid[1] = serial[5]   #2
				euid[2] = serial[6]   #0
				euid[3] = gwConst[1]  #A
				euid[4] = yearStr     #6
				euid[5] = gwConst[2]  #D
				euid[6] = serial[9]   #1
				euid[7] = serial[10]  #0
				euid[8] = gwConst[3]  #F
				euid[9] = serial[13]  #0
				euid[10] = gwConst[4] #B
				euid[11] = gwConst[4] #B
				euid[12] = serial[12] #2
				euid[13] = gwConst[5] #E
				euid[14] = serial[11] #0
				euid[15] = gwConst[6] #C
				return euid

			else:
				return None

		except:
			print ("Except serial2Euid")
			return None

	#File 안에서 String 찾기(Find Name, Find Item)
	def writeGeuid(self, fName, value):
		try:
			fp = open(fName, mode='r')
			lines = fp.readlines()
			fp.close()

			for idx, val in enumerate(lines):
				if val.find("gateway_ID") != -1:
					list = val.split(':')
					list[1] = "\"" + value + "\""
					lines[idx] = list[0] + ":" + list[1] + "\n"
					#print (lines[idx])
				else:
					print (val)

			print ("----------------------")
			print (lines)

			fp = open(fName, mode='w')
			fp.write(''.join(lines))
			fp.close()

		except:
			print ("Except writeGeuid")

	def getSerialNum(self):
		eep = I2C_EEPROM()

		#read eeprom
		result = []
		for idx in range(self.SERIAL_LEN):
			result.insert(idx, eep.read_byte(idx))

		result = bytes(result).decode('utf-8')
		#print ("getSerial : " + result)
		print ("getSerial : " + str(result))


	def setSerialNum(self, seri):
		try:
			eep = I2C_EEPROM()

			serStr = seri.replace('-', '')
			serial = list(serStr)
			print (serial)

			rEuid = self.serial2Euid(serial)
			print (rEuid)

			if rEuid != None:
				#write eeprom - Serial Number
				for i in range(len(serial)):
					eep.write_byte(i, serial[i].encode()[0])
					#print (serial[i].encode()[0])

				#write eeprom - Euid Number (EUID_ADDR_OFFSET)
				for i in range(self.EUID_LEN):
					eep.write_byte(self.EUID_ADDR_OFFSET + i, rEuid[i].encode()[0])
					#print (rEuid[i].encode()[0])

				#Packet_Forwarder_local_conf.json Write
				self.writeGeuid(self.jsonPath, "".join(rEuid))
				print ("input Serial Value Write Complete")

			else:
				print ("input Serial Value Wrong")

		except:
			print ("setSerialNum Fail")



#main#######################################################
s = serialClass()

s.getSerialNum()
#s.setSerialNum("GWKZ0200729001")
s.getSerialNum()
