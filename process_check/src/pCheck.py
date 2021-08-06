#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
import re
import sys
import time
import logging
import signal
import argparse
import subprocess
import RPi.GPIO as GPIO
import threading
import socket
import serial
import smbus
import shutil
import datetime
import binascii
import natsort

from operator import eq
from I2C_LCD_Class import lcd_Class
from I2C_EEPROM_Class import I2C_EEPROM

class ProcessChk:
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


	PROC_LIST = ['packet-forwarder', 'chirpstack-gateway-bridge', 'web_setting']

	mainThread_Cnt = 14

	MAIN_THREAD_PERIOD = 0.5		#0.3 => Real 0.5s
	SECOND_THREAD_PERIOD = 0.1	#0.1s => Real 0.2s
	THIRD_THREAD_PERIOD = 0.5		#0.3s => Real 0.5s

	#Reset Pin (Low Active)
	GPS_RESET = 27
	ETH_RESET = 34
	UART_RESET = 4

	#LORA_TX_LED = 22	#Lora-TX Pin과 Direct로 연결 되있어서 초기화 하면 Tx 안됨
	COMM_G = 6
	STAT_Y = 12
	DO = 38

	GPIO_A_ALL = [GPS_RESET, ETH_RESET, UART_RESET, COMM_G, STAT_Y, DO]

	LED_STATUS = [0,0]	#[Total_PROC_STAT, Internet]

	mThreadKill = 0
	dLcd = None
	th1 = None
	th2 = None
	th3 = None

	ledSeqIdx = 0

	#GEuid Path
	jsonPath = '/opt/semtech/packet_forwarder/lora_pkt_fwd/local_conf.json'

	#Process Path
	path = os.path.abspath(sys.argv[0])
	mainPath = path[0:path.rfind('/')]

	#Rs485
	rs485Flag = False
	rs485InitCnt = 500
	ser = None
	KEY_TIME_OUTt = 4	#Input Key TimeOut

	#PBA test Mode
	pbaTest = False
	ledStop = False

	#NTP Time Sync
	ntpCnt = 1900
	ntpPeriod = 2000

	#EEPROM Handle
	eepHandle = I2C_EEPROM()

	nicType = 0	#0:eth, 1:wi-fi, 2:LTE, 99:ALL
	pingCnt = 298

	#LTE Module Reset Wait Count
	lteResetWaitCnt = 0

	#Network Server Address
	nsFile = '/etc/chirpstack-gateway-bridge/chirpstack-gateway-bridge.toml'  #Chirpstack-gateway-bridge
	nsTag = "servers="
	nsAdd = ""

	#Msg Check
	bMsgLimit = 1000
	bMsgChkCnt = 0
	msgPath = '/opt/semtech/bMsg/'
	lastChkIdx = 0  #Last Check 된 파일 index
	delMsg = [b'up', b'\x00']
	prevFileCnt = 0
	delFileCnt = 0

	#wpa File
	wpaFile = "/etc/wpa_supplicant/wpa_supplicant.conf"

	#packet_forwarder gateway_id
	gwEuid = ""

	def __init__(self, log_file=None):
		self.logger = self.initLogger("pCheck", log_file)
		self.__stop = False

		signal.signal(signal.SIGINT, self.stop)
		signal.signal(signal.SIGTERM, self.stop)

		self.logger.info("ProcessChk Start===================>")

		#WPA Check
		self.setWifi()

		#copy TLS File
		self.copyTLSFile()

		#Gateway Euid Check (packet-forwarder)
		self.initGEuidCheck()

		#Join_Euid Check (chirpstack-gateway-bridge)
		self.bridgeSettingCheck()

		#LED Gpio Init
		self.gpio_Init()
		self.gpio_InitVal()

		#Gpio Reset
		self.softwareReset()

		#LCD Class Init
		self.dLcd = lcd_Class()

		#Read NetworkServer Address
		self.readNS()

		#Request NTP Server
		self.timeSync()

		#LED_STATUS(Process / Network) Check
		self.statusChk()

		#openVpn Service Start
		#os.system('sudo openvpn /etc/openvpn/SAM_DUCK.ovpn')
		#os.system('sudo /etc/openvpn/oVpn.sh &')

		self.logger.info("Start Check, PID {0}".format(os.getpid()))
		self.logger.info("Init Complete")

	def setWifi(self):
		try:
			ssid1 = self.getSSID1()
			ssid2 = self.getSSID2()

			self.logger.info("setWifi ssid : " + ssid1 + " / " + ssid2)

			lines = ["ctrl_interface=DIR=/var/run/wpa_supplicant\n", "update_config=1\n", "country=US\n", "\n"]

			if 0 < len(ssid1):
				passwd1 = self.getPASSWD1()
				self.logger.info(len(lines))

				lines.insert(len(lines), "network={\n")
				lines.insert(len(lines), "	ssid=\"" + ssid1 + "\"\n")
				lines.insert(len(lines), "	scan_ssid=0\n")
				lines.insert(len(lines), "	psk=\"" + passwd1 + "\"\n")
				lines.insert(len(lines), "	key_mgmt=WPA-PSK\n")
				lines.insert(len(lines), "	priority=100\n")
				lines.insert(len(lines), "}\n\n")

			if 0 < len(ssid2):
				passwd2 = self.getPASSWD2()
				lines.insert(len(lines), "network={\n")
				lines.insert(len(lines), "	ssid=\"" + ssid2 + "\"\n")
				lines.insert(len(lines), "	scan_ssid=0\n")
				lines.insert(len(lines), "	psk=\"" + passwd2 + "\"\n")
				lines.insert(len(lines), "	key_mgmt=WPA-PSK\n")
				lines.insert(len(lines), "	priority=90\n")
				lines.insert(len(lines), "}\n")

			fp = open(self.wpaFile, mode='w')
			fp.writelines(''.join(lines))
			fp.close()

			self.logger.info("!!!!!!!!!!!!s3")

			os.system("sudo systemctl restart dhcpcd")

		except:
			self.logger.info("Except_setWifi")


	def copyTLSFile(self):
		try:
#			if True == os.path.exist("/dev/mmcblk0p2"):
			if False == os.path.isdir('/home/restore'): os.system("sudo mkdir /home/restore")

			os.system("sudo mount /dev/mmcblk0p2 /home/restore")
			os.system("sudo cp -r /home/restore/tls /opt/semtech/ampla")
			os.system("sudo umount /home/restore")
			os.system("sudo rm -r /home/restore")
			self.logger.info("TLS_File_Copy_Complete")

#			else:
#				self.logger.info("not_Exist_p2")

		except:
			self.logger.error("Except_copyTLSFile")

	def readValue(self, idx, length):
		try:
			eep = I2C_EEPROM()
			result = []
			for i in range(length):
				if 255 !=  eep.read_byte(idx + i):	result.insert(i, eep.read_byte(idx + i))
		except:	self.logger.error("Except_readValue")
		return bytes(result)

	def getEuidNum(self):
		try:
			result = []
			for i in range(self.EUID_LEN):	result.insert(i, self.eepHandle.read_byte(self.EUID_ADDR_OFFSET + i))
			result = bytes(result).decode('utf-8')
			#self.logger.info("find_Gateway_ID_EEP : " + result)
			return result
		except:
			self.logger.error("Except_getEuidNum")
			return None

	def getTLS(self):
		try:		return (self.readValue(self.TLS_ADDR_OFFSET, self.TLS_LEN).decode('utf-8'))
		except:	return None

	def getServ(self):
		try:		return self.readValue(self.SERV_ADDR_OFFSET, self.SERV_LEN).decode('utf-8')
		except:	return None

	def getPort(self):
		try:		return self.readValue(self.PORT_ADDR_OFFSET, self.PORT_LEN).decode('utf-8')
		except:	return None

	def getSSID1(self):
		try:		return self.readValue(self.SSID1_ADDR_OFFSET, self.SSID1_LEN).decode('utf-8')
		except:	return None

	def getPASSWD1(self):
		try:		return self.readValue(self.PASSWD1_ADDR_OFFSET, self.PASSWD1_LEN).decode('utf-8')
		except:	return None

	def getSSID2(self):
		try:		return self.readValue(self.SSID2_ADDR_OFFSET, self.SSID2_LEN).decode('utf-8')
		except:	return None

	def getPASSWD2(self):
		try:		return self.readValue(self.PASSWD2_ADDR_OFFSET, self.PASSWD2_LEN).decode('utf-8')
		except:	return None



	def bridgeSettingCheck(self):
		jeuiTag 		= "join_euis=["
		serverTag 	= "servers="
		usernameTag = "username="
		passwordTag = "password="
		caTag 			= "# on the server"
		certTag			= "# mqtt TLS certificate file"
		keyTag			= "# mqtt TLS key file"

		#Server Address Read
		try:
			fp = open(self.nsFile, mode='r')
			lines = fp.readlines()
			fp.close()

			serv = self.getServ()
			port = self.getPort()
			tls = self.getTLS()
			if "0" == tls:
				cmmnt = "#"
				scheme = "tcp://"
			else:
				cmmnt = ""
				scheme = "ssl://"

			self.logger.info("serv : " + serv + " / Port : " + port + " / TLS : " + tls)

			#File All Line Read
			for idx, val in enumerate(lines):
				#join_euis Check
				if 0 == val.find(jeuiTag):
					idxJeui = idx + 1
					jeuis = '	["0e37807256312278", "0e378072563122ff"],\n'
					if -1 == lines[idxJeui].find(jeuis):
						lines.insert(idxJeui, jeuis)

				#servers Check
				if -1 != val.find(serverTag):		lines[idx] = "		servers=[\"" + scheme + serv + ":" + port + "\"]\n"
				#username Check
				if -1 != val.find(usernameTag):	lines[idx] = "		username=\"" + self.gwEuid.lower() + "\"\n"
				#password Check
				if -1 != val.find(passwordTag):	lines[idx] = "		password=\"!" + self.gwEuid.lower() + "!\"\n"
				#ca Check
				if -1 != val.find(caTag):		lines[idx + 1] = cmmnt + "		ca_cert=\"/opt/semtech/ampla/tls/ca/ca.crt\""
				#cert Check
				if -1 != val.find(certTag):	lines[idx + 1] = cmmnt + "		tls_cert=\"/opt/semtech/ampla/tls/crt/client.crt\""
				#key Check
				if -1 != val.find(keyTag):	lines[idx + 1] = cmmnt + "		tls_key=\"/opt/semtech/ampla/tls/key/client.key\""

			#File Write & Bridge Restart
			fp = open(self.nsFile, mode='w')
			fp.write(''.join(lines))
			fp.close()

			self.logger.info("bridgeSettingCheck_Complete")
			os.system("sudo systemctl restart chirpstack-gateway-bridge.service")
			self.logger.info("bridge_Restart")

		except:
			self.logger.error("Except_bridgeSettingCheck")


	#NTP TimeSync Request
	#Time Sync Success	=> 60min
	#Time Sync Error		=> 5min
	def timeSync(self):
		try:
			tempFlag = 1

			#1차 시도 Server Address
			ntpServ = self.nsAdd
			#ntpServ = 'hsrnd02222.iptime.org'	#Test
			cmd = "sudo ntpdate -u " + ntpServ
			result = subprocess.getoutput(cmd)
			findVal = result.find("no server")
			#self.logger.info(findVal)

			#Server NTP Request 실패 시, time.nist.gov로 시도
			if -1 != result.find("no server"):
				tempFlag = 0
				#self.logger.info(result)

				ntpServ = 'time.nist.gov'
				cmd = "sudo ntpdate -u " + ntpServ
				result = subprocess.getoutput(cmd)
				#self.logger.info("++++++" + result)

				if -1 != result.find("time server"):	tempFlag = 1

			else:
				self.logger.info(result)

			if 1 == tempFlag:
				self.ntpPeriod = 12000	#60min
				self.logger.info("========== >> NTP Time Sync Success....." + ntpServ )
			else:
				self.ntpPeriod = 1000		#5min
				self.logger.error("========== >> NTP Time Sync Error")


		except:
			self.logger.error("Except_timeSync")

	#File 안에서 String 찾기(Find Name, Find Item)
	def findStrInFile(self, fName, fItem):
		try:
			fp = open(fName, mode='r')
			lines = fp.readlines()
			fp.close()

			result = ""
			for idx, val in enumerate(lines):
				if val.find(fItem) != -1:
					result = val

			return result
		except:
			self.logger.error("Except_findStrInFile")

	def readNS(self):
		#Server Address Read
		try:
			addList = self.findStrInFile(self.nsFile, self.nsTag).split('"')[1].split(':')
			tlsChk = "off"
			if addList[0] == "ssl": tlsChk = "on"
			self.nsAdd = sAdd = addList[1].replace('//', '')
			p_sPort = sPort = addList[2]
			p_tlsChk = tlsChk
			self.logger.info("tls:" + tlsChk + " / add:" + sAdd + " / port:" + sPort)
		except:
			self.logger.error("Except_readNS")

	def rs485Init(self):
		## lsusb 명령어를 통해서 device id를 가진 장치가 있는지 확인
		deviceID = "0403:6015"
		result = ""

		try:  result = subprocess.check_output("lsusb | grep " + deviceID, shell=True, stderr=subprocess.STDOUT)
		except subprocess.CalledProcessError as e : result = ""

		if(len(result) == 0):
			self.logger.info("장치가 발견되지 않았습니다.")
			self.rs485Flag = False
			return

		# 모든 포트 위치 검색
		try:
			result = subprocess.check_output("ls /dev/ttyUSB*", shell=True, stderr=subprocess.STDOUT)
			# 바이트 배열로 리턴되는 값을 문자열로 변경
			result = str(result)
			# 배열이 b'ABCD'의 형식이므로 앞, 뒤 불필요한 문자 제거
			# 다수의 행이 반환되므로 개행문자로 문자열 분리
			result = result[2:len(result)-1].split('\\n')
			found = False

			port = ""
			for path in result:
				# 포트 패턴 정규식
				portPattern = re.compile('^/dev/ttyUSB[0-9]+$')
				m = portPattern.match(path)
				print (m)

				if(m):
					#올라온 값이 포트값이면, 포트의 PRODUCT정보를 읽어서 장치값 비교
					try:
						result2 = str(subprocess.check_output("grep PRODUCT= /sys/bus/usb-serial/devices/"+path[4:]+"/../uevent", shell=True, stderr=subprocess.STDOUT))
						# 배열이 b'PRODUCT=1234/1234/100'과 같은 형식이므로 앞, 뒤 불필요 문자열 제거
						result2 = result2[10:len(result2)-1]
					except subprocess.CalledProcessError as e :
						result2 = "GGGG/GGGG\n"

					# 개행문자와 /으로 문자열 분리
					result2 = result2.split('\\n')[0].split('/')
					# 입력받은 device ID를 :으로 분리
					didHexList = deviceID.split(':')
					# 16진수로 변경
					if(int(result2[0],16)==int(didHexList[0],16) and int(result2[1],16)==int(didHexList[1],16)):
						port = path
						self.rs485Flag = True
						self.logger.info("장치의 포트를 찾았다(" + path + ")")
						break

			if self.rs485Flag == True:
				self.ser = serial.Serial(port, 115200, timeout=0.2)
				self.ser.close()
				self.ser.open()
				self.ser.readline()

		except subprocess.CalledProcessError as e :
			print ("Except : rs485Init")

	def rs485Trans(self, msg):
		msg += "\r\n"
		self.ser.write(str.encode(msg))

	keyTimeout = 0
	def rs485Process(self):
		try:
			totalStr = ""
			readStr = self.ser.readline()

			if readStr:
				self.keyTimeout = 0
				readStr = readStr.decode('utf-8')
				totalStr = "".join([totalStr, readStr])
				#print("totalStr : " + totalStr)

				idx = len(totalStr) - 1

				if totalStr[idx] == '\r' or totalStr[idx] == '\n':
					totalStr.replace('\r', '')
					totalStr.replace('\n', '')

					if -1 < totalStr.find("PBA_TEST"):
						self.rs485Trans("PBA Test Start")
						self.gpioTest()
						self.pingTest()
						#self.processCheck()
						#self.gpsCheck()
						self.rs485Trans("PBA Test End")

					elif -1 < totalStr.find("IP"):					self.ipCheck()
					elif -1 < totalStr.find("GET_EUID"):		self.getEuid()
					elif -1 < totalStr.find("GET_SERIAL"):	self.getSerialNum()
					elif -1 < totalStr.find("SET_SERIAL"):	self.setSerialNum(totalStr.split('=')[1].split())
					elif -1 < totalStr.find("DEL_SERIAL"):	self.delSerialNum()
					elif -1 < totalStr.find("_SSH_ON_"):	self.setSSH(22)
					elif -1 < totalStr.find("_SSH_OFF_"):  self.setSSH(0)

				self.ser.flushInput()

			else:
				self.keyTimeout += 1
				if self.keyTimeout > self.KEY_TIME_OUTt: #main에서 0.5ms 이므로 2sec
					self.keyTimeout = 0
					totalStr = ""

		except:
			print ("Except : rs485Process")

	#IP Address Check
	def ipCheck(self):
		try:
			ipList = subprocess.check_output(['hostname', '--all-ip-addresses']).split()
			msg = "ipAddress : "
			for i in ipList:	msg = msg + i.decode('utf-8') + ", "
			self.rs485Trans(msg)

		except:	print ("Except ipCheck")


	def deviceModelCheck(self, model, nic):
		try:
			print ("deviceModelCheck")

#			#nic 폴더가 있으면..
#			if os.path.isdir("/sys/class/net/" + nic) == True:
#				#up/down Check
#				cmd = "sudo cat /sys/class/net/" + nic + "/operstate"
#				if subprocess.getoutput(cmd) == "down":

		except:
			print ("Except deviceModelCheck")

	def getNicType(self):
		nicType = 0

		try:
			type = self.eepHandle.read_byte(3)

			if type == 90:    nicType = 99	#All
			elif type == 87:  nicType = 1		#Wifi
			elif type == 76:  nicType = 2		#LTE
			else: nicType = 0								#Eth

			print ("nicType : " + str(nicType))
			#self.logger.info("nicType : " + str(nicType))

		except:
			print ("Except : getNicType")
			#self.logger.error("Except : getNicType")

		self.nicType = nicType

	def initGEuidCheck(self):
		try:
			self.getNicType()

			#Get Gateway_EUID
			self.gwEuid = self.getEuidNum()
			self.logger.info("====> initGEuidCheck : " + self.gwEuid)

			self.writeGeuid(self.jsonPath, self.gwEuid)
			self.logger.info("initGEuidCheck complete")

		except:
			print ("Except initGEuidCheck")

	def setSSH(self, sel):
		if sel == 22:
			os.system("sudo systemctl restart ssh")
			self.rs485Trans("SSH_Enable")
		else:	os.system("sudo systemctl stop ssh")

	def getEuid(self):
		result = self.getEuidNum()
		self.rs485Trans("getEuid : " + str(result))

	def delSerialNum(self):
		print ("delSerialNum")

		#write eeprom - Serial Number
		for i in range(self.SERIAL_LEN):
			self.eepHandle.write_byte(i, 0x30)

		#write eeprom - Euid Number (EUID_ADDR_OFFSET)
		for i in range(self.EUID_LEN):
			self.eepHandle.write_byte(self.EUID_ADDR_OFFSET + i, 0x30)
			#print (rEuid[i].encode()[0])

		self.rs485Trans("DelEuid Complete ")


	def getSerialNum(self):
		#read eeprom
		result = []
		for i in range(self.SERIAL_LEN):	result.insert(i, self.eepHandle.read_byte(i))

		result = bytes(result).decode('utf-8')
		self.rs485Trans("getSerial : " + str(result))

	def setSerialNum(self, seri):
		try:
			serStr = seri[0].replace('-', '')
			serial = list(serStr)
			print (serial)

			rEuid = self.serial2Euid(serial)
			print (rEuid)

			if rEuid != None:
				#write eeprom - Serial Number
				for i in range(len(serial)):
					self.eepHandle.write_byte(i, serial[i].encode()[0])
					#print (serial[i].encode()[0])

				#write eeprom - Euid Number (EUID_ADDR_OFFSET)
				for i in range(self.EUID_LEN):
					self.eepHandle.write_byte(self.EUID_ADDR_OFFSET + i, rEuid[i].encode()[0])
					#print (rEuid[i].encode()[0])

				euid = "".join(rEuid)
				print (euid)
				#Packet_Forwarder_local_conf.json Write
				self.writeGeuid(self.jsonPath, euid)
				self.rs485Trans("input Serial Value Write Complete")

			else:
				self.rs485Trans("input Serial Value Wrong")

		except:
			self.rs485Trans("setSerialNum Fail")


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



#main#######################################################
	#"eth0", "wlan0", "wwan0"
	#up/down, ipAddress, ping
	nicStatus = [[0 for col in range(3)] for row in range(3)]
	def nicDiscCheck(self):
		#tempNicStatus = self.nicStatus
		tempNicStatus = [[0 for col in range(3)] for row in range(3)]
		pingChkFlag = 0
		fiveMinFlag = 0
		pingCntLimit = 0

		try:
			#self.logger.info("====================================================================\r\n")
			#self.logger.info("nicDiscCheck")	#period Check Log

			#"eth0", "wlan0", "wwan0"
			nicList = ["eth0", "wlan0", "wwan0"]
			nicRestart = 0

			#네트웤 연결 중에는 5분마다 체크 / 끊어진 경우 1분 마다 체크
			#10s * 6 = 1min
			#10s * 30 = 5min
			if self.LED_STATUS[1] == 0:	pingCntLimit = 6
			else:	pingCntLimit = 30

			self.pingCnt += 1
			if self.pingCnt >= pingCntLimit:
				self.pingCnt = 0
				pingChkFlag = 1
				fiveMinFlag = 1

			#self.logger.info("++++++++++++++++++++++++++++++++++++++nicDiscCheck")
			#eth0, wlan0, wwan0 Check for문
			for i, nic in enumerate(nicList):
				try:
					#exist Check
					if os.path.isdir("/sys/class/net/" + nic) == False:
						self.nicStatus[i][0] = 0
						#self.logger.info("Not Exist " + nic)
						continue
					#else:	self.logger.info("Exist " + nic)

					#up/down Check
					cmd = "cat /sys/class/net/" + nic + "/operstate"
					#down 상태이면 Clear
					if subprocess.getoutput(cmd) == "down":
						tempNicStatus[i][0] = 0
						tempNicStatus[i][1] = 0
						tempNicStatus[i][2] = 0
						self.nicStatus[i] = tempNicStatus[i]
						#self.logger.info("Down Status " + nic)
						continue

					tempNicStatus[i][0] = 1
					self.nicStatus[i][0] = tempNicStatus[i][0]

					#ip Address Check
					nicStat = subprocess.getoutput("ifconfig " + nic + " | grep 'inet '")
					if nicStat == None:	tempNicStatus[i][1] = None
					else:	tempNicStatus[i][1] = nicStat.split()[1]
					#self.logger.info(nic + " : " + tempNicStatus[i][1] + " / " + str(self.nicStatus[i][1]))

					#ip 변경 발생
					if self.nicStatus[i][1] != tempNicStatus[i][1]:
						pingChkFlag = 1
						self.pingCnt = 0
						self.nicStatus[i][1] = tempNicStatus[i][1]

					#ping Check (5분 주기 또는 IP 변경 시 발생)
					#mainThread (10sec) * 30Cnt = 5min or IP Change
					if pingChkFlag == 1:
						#self.logger.info("=============================> " + nic + " pingChkFlag = 1")	#Occur Check Log
						result = subprocess.getoutput("fping -I " + nic + " -t 1000 -b 1 " + self.nsAdd)
						#self.logger.info(result)

						if result.find("alive") != -1:	tempNicStatus[i][2] = 1

						self.nicStatus[i][2] = tempNicStatus[i][2]
						#self.logger.info(nic + " Ping_Chk")

						#5min 마다 check, NIC Reset - Ethernet 끊기거나 할 때 재 연결 시도
						if fiveMinFlag == 1:
							chkFlag = 0

							#ssh 접속 중에는 NIC Reset 안함
							if i == 0:
								if self.nicStatus[i][1] == '192.168.2.1':
									self.logger.info("+++++++++++++++++++ 192.168.2.1 +++++++++++++++++++")
									chkFlag = 1

							else:
								try:		ipHead = self.nicStatus[i][1].split('.')[0]
								except:	ipHead = '169'
								if self.nicStatus[i][1] == '127.0.0.1' or ipHead == '169':	chkFlag = 1

							if chkFlag == 1:
								os.system("sudo ifconfig " + nic + " down")
								time.sleep(2)
								os.system("sudo systemctl restart dhcpcd")
								time.sleep(2)
								os.system("sudo ifconfig " + nic + " up")
								self.logger.info(nic + " Nic Restart")
							else:
								print (nic + " Nic Running")

				except:
					print ("Except For " + nic)

			print ("_____________________________________________")
			print (self.nicStatus)

		except:
			self.logger.error("Except nicDiscCheck " + nic)

		return 0

	def gpioTest(self):
		self.pbaTest = True
		while self.ledStop == True:	self.logger.info("Wait")

		time.sleep(2)
		self.rs485Trans("########################")
		self.rs485Trans("#  GPIO Test           #")
		self.rs485Trans("########################")
		msg = [" 1.Green LED Toggle      x 2", " 2.Yellow LED Toggle     x 2", " 3.Relay Toggle          x 2"]

		GPIO_ARRAY = [self.COMM_G, self.STAT_Y, self.DO]
		aLen = len(GPIO_ARRAY)
		SLEEP_TIME = 0.5

		# the same script as above but using BCM GPIO 00..nn numbers
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)

		idx = 0
		for pin in GPIO_ARRAY:
			GPIO.setup(pin, GPIO.OUT)
			self.rs485Trans(msg[idx])
			time.sleep(SLEEP_TIME)

			for i in range(2):
				GPIO.output(pin, GPIO.HIGH)
				time.sleep(SLEEP_TIME)
				GPIO.output(pin, GPIO.LOW)
				time.sleep(SLEEP_TIME)

			idx+=1

		GPIO.cleanup()
		self.rs485Trans("\r\n")

		self.pbaTest = False


	#NIC Ping Check
	def pingTest(self):
		self.rs485Trans("########################")
		self.rs485Trans("#  PING Test           #")
		self.rs485Trans("########################")

		msg = ["eth0", "wwan0", "wlan0"]
		space = ["  ", " ", " "]
		alive = [[" 1.","alive"], [" 2.","alive"], [" 3.","alive"]]
		idx = 0

		ipList = subprocess.check_output(['ifconfig', '-a']).split()
		readList = subprocess.check_output(['ip', 'addr', 'show']).decode('utf-8').split('\n')
		ipList = ["127.0.0.1", "127.0.0.1", "127.0.0.1"]
		ipListIdx = 0

		for v in readList:
			if v.find('inet ') > -1:
				tempList = v.split()
				if tempList[len(tempList) - 1] != "lo":
					msg[ipListIdx] = tempList[len(tempList) - 1]
					ipList[ipListIdx] = tempList[1].split('/')[0]
					print (msg[ipListIdx] + " : " + ipList[ipListIdx])
					ipListIdx += 1

		for idx in range(ipListIdx):
			try:
				subprocess.check_output(['fping', '-I', msg[idx], '-t', '1000', self.nsAdd]).decode('utf-8')
				alive[idx][1] = "alive"
			except:
				alive[idx][1] = "dead"

			#문자열 정렬
			result = alive[idx][0] + msg[idx] + space[idx] + ipList[idx]
			length = 25 - len(result)

			for i in range(length):	result += " "

			self.rs485Trans(result + "(" + alive[idx][1] + ")\r")
			idx += 1

		self.rs485Trans("\r\n")


	#File 을 개행 문자 별로 List에 담기(Find Name, Find String)
	def readFileList(self, fName):
		L = []
		fp = open(fName, mode='r')
		if fp != None:
			while(1):
				line=fp.readline()
				try:escape=line.index('\n')
				except:escape=len(line)

				if line:	L.append(line[0:escape])
				else:	break;
			fp.close()
		return L

	#List에서 특정 문자열이 있는 index 찾기
	def findStrList(self, listName, fStr):
		idx = 0

		try:
			for i in listName:
				tIdx = i.find(fStr)
				if tIdx == 0:	break;
				else:	idx += 1

			if len(listName) == idx:  return -1
			else: return idx

		except:
			print ("Except findStrList")

	def setHostName(self):
		try:
			host = os.popen('cat /etc/hostname').read().strip()
			#print ("host:" + hostName)
			#readStr = os.popen('cat /opt/semtech/ampla/version').read()
			#version = readStr[0:readStr.find("\n")].rstrip().replace('.', '')
			#hostName = "AMPLA " + version[version.find(':')+1:len(version)].strip()

			result = []
			for i in range(self.SERIAL_LEN):  result.insert(i, self.eepHandle.read_byte(i))
			result = bytes(result).decode('utf-8')
			hostName = "AMPLA-" + str(result[5:])
			self.logger.info("HostName : " + hostName + " / " + host)

			if host != hostName:
				self.logger.info("HostName Different")

				roPath = ''
				if True == os.path.isdir('/ro'):
					os.system("sudo mount -o remount,rw /ro")
					roPath = '/ro'

				f = open(roPath + '/etc/hostname', 'w')
				f.write(hostName)
				f.close()

				readList = self.readFileList(roPath + '/etc/hosts')
				findIdx = self.findStrList(readList, '127.0.1.1')
				self.logger.info("	find Idx " + str(findIdx))

				if findIdx > -1:
					readList[findIdx] = "127.0.1.1	" + hostName
					f = open(roPath + '/etc/hosts', 'w')
					f.write('\n'.join(readList))
					f.close()

				print (readList)

		except:
			print ("Except setHostName")


	#Thread ################################################################################################
	#Process Thread	(0.5s)
	lcdPrintCnt = 0
#	threadStatus[3] = [0, 0, 0]
	def main_Thread(self):
		try:
			#Lcd_Status Print (3s)
			self.lcdPrintCnt += 1
			if self.lcdPrintCnt >= 4:
				self.lcdPrintCnt = 0
				self.dLcd.lcd_print()

			#10초 주기 - Check
			self.mainThread_Cnt += 1
			if self.mainThread_Cnt >= 17:	#10s
				self.mainThread_Cnt = 0

				#Nic Disccnect Check(eth0)
				self.nicDiscCheck()

				#LED_STATUS(Process / Network) Check
				self.statusChk()

				#LTE Init Check (10s)
				self.lteCheck()

				#Ram Disk Size Check
				self.rwSizeCheck()

#				self.logger.info("1st_Thread")

		except:
			self.logger.error("Except_1st_Thread")

		if self.mThreadKill == 1: return
		self.th1 = threading.Timer(self.MAIN_THREAD_PERIOD, self.main_Thread)
		self.th1.start()

	#Board Test Thread (0.3s)
	def second_Thread(self):
		try:
			#rs485 - Board Test
			if self.rs485Flag == False:
				self.rs485InitCnt += 1
				if self.rs485InitCnt >= 300:	#90Sec
					self.rs485InitCnt = 0
					self.rs485Init()
			else:
				self.rs485Process()

			#NTP Time Sync Request & mqtt Backup Message Limit Check
			self.ntpCnt += 1
			if self.ntpCnt >= self.ntpPeriod:
				self.ntpCnt = 0
				self.timeSync()

			#Backup Message Check
			self.bMsgChkCnt += 1
			if self.bMsgChkCnt >= 100:
				self.bMsgChkCnt = 0
				self.mqttBackCheck()


		except:
			self.logger.error("Except 2nd_Thread")

		if self.mThreadKill == 1: return
		self.th2 = threading.Timer(self.SECOND_THREAD_PERIOD, self.second_Thread)
		self.th2.start()

	thirdCnt = 0
	#LED Check Thread	(0.5s)
	def third_Thread(self):
		try:
			self.thirdCnt += 1
			if self.thirdCnt >= 20:
				self.thirdCnt = 0
				#self.logger.info("3nd_Thread") #10s

			#Status LED Blink
			if self.pbaTest == False:
				self.led_Func(self.LED_STATUS)

		except:
			self.logger.error("Except 3rd_Thread")

		if self.mThreadKill == 1: return
		self.th3 = threading.Timer(self.THIRD_THREAD_PERIOD, self.third_Thread)
		self.th3.start()

	def main(self):
		self.logger.info("Start Main Routine")

		#Read Host Name
		self.setHostName()

		#ssh Disable
		#os.system("sudo systemctl disable ssh")

		self.main_Thread()
		self.second_Thread()
		self.third_Thread()

	def stop(self, signum, frame):
		self.__stop = True
		self.mThreadKill = 1
		self.logger.info("Receive Signal {0}".format(signum))

		GPIO.cleanup()
		self.th1.cancel()
		self.th2.cancel()
		self.th3.cancel()
		self.dLcd.lcd_reset()
		self.logger.info("Waiting Thread Kill")
		self.logger.info("Stop Process Check")

	#File 안에서 String 찾기(Find Name, Find Item)
	def writeGeuid(self, fName, value):
		try:
			fp = open(fName, mode='r')
			lines = fp.readlines()
			fp.close()
			#print (lines)

			for idx, val in enumerate(lines):
				if val.find("gateway_ID") != -1:
					list = val.split(':')
					list[1] = "\"" + value + "\""
					lines[idx] = list[0] + ":" + list[1] + "\n"

			#print ("----------------------")
			#print (lines)

			fp = open(fName, mode='w')
			fp.write(''.join(lines))
			fp.close()

		except:
			self.logger.error("Except writeGeuid")

	def checkPid(self, processName):
		return subprocess.check_output("ps -eaf | grep " + processName + " | grep -v grep | awk '{print $2}'", shell=True).decode('utf-8').strip()

	def checkService(self, processName):
		cmd = 'systemctl status ' + processName

		try:
			result = subprocess.check_output([cmd], shell=True, encoding='utf-8')
			findVal = result.find('Active: active')
			#self.logger.info("checkService(" + str(findVal) + ")")

			if findVal == -1:	return 0
			else:	return 1

		except:
			return 0

	#LTE는Disconnect Check 외  Init Check 추가 진행
	# wwan0 Down 시=>  즉시 Reset
	# ip Address 할당 못 받거나 Ping Check 실패 시 => Ping Check 시도 후 Reset
	def lteCheck(self):
		try:
			step = 0
			resetFlag = 0

			self.getNicType()
			#self.logger.info("NIC Type (" + str(self.nicType) + ")\r\n")
			step = 1

			if 2 > self.nicType and 99 != self.nicType:	return
			if 0 < self.lteResetWaitCnt:
				self.lteResetWaitCnt -= 1
				return

			step = 2
			#wwan0 이 up 이지만, IP 할당을 못 받은 경우 Reset
			if self.nicStatus[2][0] == 1:

				self.logger.info("LTE_Ping_Step_2")

				if self.nicStatus[2][1] == 0 or self.nicStatus[2][1].split('.')[0] == '169' or self.nicStatus[2][2] == 0:
					self.logger.info("lteCheck==>Lte_Disconnect")

					#self.logger.info("ltechk_0")
					#Telit Module Exist Check
					lsusb = subprocess.check_output('lsusb').decode('utf-8')
					if -1 != lsusb.find('Telit'):
						#self.logger.info("ltechk_1")
						#wwan0 Ping Check - 실패 시, LTE Reset
						try:
							cmd = ['fping', '-I', 'wwan0', '-t', '1000', '-b', '1', self.nsAdd]
							result = subprocess.check_output(cmd).decode('utf-8')
							if result.find('alive') == -1:	resetFlag = 1

						except:
							resetFlag = 1

						if resetFlag == 1:
							#subprocess.run(['sudo', 'systemctl', 'restart', 'lte_setup.service'])
							subprocess.run(['systemctl', 'restart', 'lte_setup.service'])
							self.logger.info("lteCheck==>lte_Reset")
							self.lteResetWaitCnt = 2

						else:
							self.logger.info("lte_Alive")

#				else:
#					self.logger.info("LTE_Ping_Step_3")

			#wwan0 Down Status
			else:
				step = 3
				subprocess.run(['systemctl', 'restart', 'lte_setup.service'])
				self.logger.info("lteCheck==>lte_Reset")
				self.lteResetWaitCnt = 2

		except:
			self.logger.error("Except lteCheck (" + str(step) + ")")


	#LED Func ############################################################################
	def gpio_Init(self):
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)

		for v in self.GPIO_A_ALL:
			GPIO.setup(v, GPIO.OUT)

	def gpio_InitVal(self):
		for v in self.GPIO_A_ALL:
			GPIO.output(v, GPIO.HIGH)

	def led_Func(self, status):
		self.ledStop = True

		try:

			setVal = [GPIO.LOW, GPIO.HIGH]
			ledSequence = [[1,0,1,0,0,0], [1,1,1,0,0,0]]  #비정상[0], 정상[1] - 500ms 기준..

			GPIO.setmode(GPIO.BCM)
			GPIO.setwarnings(False)
			GPIO.setup(self.STAT_Y, GPIO.OUT)
			GPIO.setup(self.COMM_G, GPIO.OUT)

			GPIO.output(self.STAT_Y, setVal[ledSequence[status[0]][self.ledSeqIdx]])
			GPIO.output(self.COMM_G, setVal[ledSequence[status[1]][self.ledSeqIdx]])

			#self.logger.info("Serq : " + str(self.ledSeqIdx) + " / " + str(status[0]) + str(status[1]))

			self.ledSeqIdx += 1
			if self.ledSeqIdx >= len(ledSequence[0]):	self.ledSeqIdx = 0

		except:
			self.logger.error("led_Status_Except : GPIO pin is in use in Board Test")

		self.ledStop = False

	#LED Func End ########################################################################

	def softwareReset(self):
		#Software Reset
#		gpioList = [self.GPS_RESET, self.ETH_RESET, self.UART_RESET]
		gpioList = [self.GPS_RESET, self.UART_RESET]

		for gpio in gpioList:
			GPIO.output(gpio, GPIO.LOW)
			time.sleep(0.01)  #10ms
			GPIO.output(gpio, GPIO.HIGH)
			time.sleep(0.1)    #100ms

		time.sleep(2)

	def statusChk(self):
		procSum = 0
		result1 = self.LED_STATUS[0]
		result2 = self.LED_STATUS[1]

		try:
			#LED_STATUS(Process) Check
			for n in self.PROC_LIST:	procSum += self.checkService(n)
			if procSum == len(self.PROC_LIST):	result1 = 1
			else:	result1 = 0

			#LED_STATUS(network) Check
			upStatus = self.nicStatus[0][0] + self.nicStatus[1][0] + self.nicStatus[2][0]
			pingStatus = self.nicStatus[0][2] + self.nicStatus[1][2] + self.nicStatus[2][2]

			#for i, nic in enumerate(self.nicStatus):	print (nic)

			if upStatus > 0 and pingStatus > 0:	result2 = 1
			else:	result2 = 0

			#self.logger.info("____statusChk")

		except:
			self.logger.error("Except processChk")

		self.LED_STATUS[0] = result1
		self.LED_STATUS[1] = result2

	def rwSizeCheck(self):
		try:
			if True == os.path.isdir('/rw'):	diskLabel = '/rw'
			else:	diskLabel = '/'

			total, used, free = shutil.disk_usage(diskLabel)
			ratio = used / total * 100
			if ratio > 70:
				os.system("sudo find /var/log -name '*.1' -type f -exec rm {} \;")
				os.system("sudo find /var/log -name '*.2' -type f -exec rm {} \;")
				os.system("sudo find /var/log -name '*.log.*' -type f -exec rm {} \;")
				os.system("sudo find /var/log -name '*.gz' -type f -exec rm {} \;")
				os.system("sudo apt clean")
				os.system("sudo logrotate -f /etc/logrotate.conf")

				if '/rw' == diskLabel:
					os.system("sudo rm -r /var/cache/*")
					os.system("sudo rm -r /var/lib/apt/*")

				#os.system("sudo rm -r " + diskLabel + "/var/log/*.1")
				#os.system("sudo rm -r " + diskLabel + "/var/log/*.gz")
				self.logger.info("reSizeCheck - over Ratio (" + str(ratio) + " / " + str(used) + " / " + str(total) + ")")

		except:
			self.logger.error("Except reSizeCheck")


	#Mqtt Backup Check ############################################################
	def getFileList(self, path):
		try:
			fList = os.scandir(path)
			bList = []

			#name, path, inode(), is_dir(), is_file(), is_symlink(), stat
			for idx, file in enumerate(fList):
				stat = file.stat()
				#print (str(idx) + ' %20s' % file.name + ' | %10s' % str(stat.st_size) + ' bytes | %30s' % time$

				line = []
				line.append(file.name)            #File Name
				line.append(int(stat.st_mtime))   #File Modify Time
				line.append(0)
				bList.append(line)

			#print (bList)
			bList = sorted(bList, key=lambda tStamp: tStamp[1])
			#for l in bList: print (l)
			return bList

		except:
			self.logger.error("Except_getFileList")

	def msgCheck(self, filePath, fileName):
		result = 0
		try:
			with open(filePath + fileName, 'rb') as f:
				readVal = f.read()
			f.close()

			try:
				if 44 < len(readVal):
					topic = readVal[36:38]
					mType = readVal[42:43]

					if self.delMsg[0] == topic and self.delMsg[1] == mType:
						reName = filePath + "del_" + fileName
						#print (reName)
						os.rename(filePath + fileName, reName)
						self.delFileCnt = self.delFileCnt + 1

				else:	print ("ReadVal Len < 44")
			except:	print ("Except_msgCheck")
		except:	self.logger.error("Except_readFile")

		return result

	#Folder 내부 파일 개수 체크(find가 ls 보다 2배 정도 빠름)
	def fileCount(self):
		#os.system('find /opt/semtech/bMsg -type f | wc -l')
		cmd = 'find ' + self.msgPath + ' -type f | wc -l'
		result = subprocess.getoutput(cmd)
		return  result

	def mqttBackCheck(self):
		try:
			outputList = []

			#Start Time
			sTime = datetime.datetime.now()

			fCnt = self.fileCount()
			#self.logger.info("!!! " + str(self.prevFileCnt) + " / " + str(fCnt) + "!!!")

			if self.prevFileCnt != self.fileCount():
				self.delFileCnt = 0
				fList = self.getFileList(self.msgPath)

				#Join-Req Msg Check
				for lst in fList:
					if 0 == self.msgCheck(self.msgPath, lst[0]):
						outputList.append(lst)

				#Delete
				if 0 < self.delFileCnt:
					self.logger.info("======================>>>> delFileCnt : " + str(self.delFileCnt))
					os.system('sudo rm ' + self.msgPath + 'del_*')

				#Delete 후 Folder 내 file Count
				self.prevFileCnt = self.fileCount()

				#Over File Delete
				size = len(outputList)
				self.logger.info("리스트 길이 " + str(size))

				if self.bMsgLimit <= size:
					natsort.natsorted(outputList, reverse=True)
					delCnt = size - self.bMsgLimit
					for i, fName in enumerate(outputList):
						if delCnt < i:  break
						reName = self.msgPath + "del_" + fName[0]
						os.rename(self.msgPath + fName[0], reName)

					os.system('sudo rm ' + self.msgPath + 'del_*')

				#End Time
				gTime = datetime.datetime.now() - sTime
				self.logger.info("elapsed Time " + str(gTime) + " ms")

		except:
			self.logger.error("Except_mqttBackCheck")


	#Logger #############################################################################################
	def initLogger(self, processName, file):
		#Logging
		logArray = ["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
		logLevel = logging.WARNING  #Log Level Default Warning

		#Config Read
		if os.path.isfile(self.mainPath + "/" + processName + ".conf"):
			list = self.readFileList(self.mainPath + "/" + processName + ".conf")
			level = list[self.findStrList(list, 'logLevel')].replace('\n','').split('=')[1]
			#self.timeSel = list[self.findStrList(list, 'timeSel')].replace('\n','').split('=')[1]
			#print ("file Found")

			lIdx = 0
			for val in logArray:
				if val == level:
					self.logLevel = lIdx * 10
				lIdx+=1

		else:
			fName = self.mainPath + "/" + processName + ".conf"
			f = open(fName, 'w')
			f.write("logLevel=ERROR\n")
			#f.write("timeSel=1")
			f.close()
			print ("Make File")

		logger = logging.getLogger(processName)
		fmt = logging.Formatter('[%(asctime)-15s] %(name)-s : %(levelname)-s) %(message)s')

		stream_handler = logging.StreamHandler()
		stream_handler.setFormatter(fmt)
		logger.addHandler(stream_handler)
		logger.setLevel(level=self.logLevel)
		#logger.setLevel(level=logging.DEBUG)

		if file:
			file_handler = logging.FileHandler(file)
			file_handler.setFormatter(fmt)
			logger.addHandler(file_handler)
			print ("InitLogger")
		return logger


#if __name__ == '__main__':
#	parser = argparse.ArgumentParser()
#	parser.add_argument("--log", help="log filename", default=None)
#	args = parser.parse_args()

#	p_chk = ProcessChk(args.log)
#	p_chk.main()