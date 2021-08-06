#!/usr/bin/env python
#-*- coding:utf-8 -*-

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
import os
import re
import sys

from operator import eq
from I2C_LCD_Class import lcd_Class
from I2C_EEPROM_Class import I2C_EEPROM

class ProcessChk:
	PROC_LIST = ['packet-forwarder', 'chirpstack-gateway-bridge', 'web_setting']
	LOGGING_CNT = 60

	mainThread_Cnt = 9
	secondThread__Cnt = 0
	thirdThread_Cnt = 0

	MAIN_THREAD_PERIOD = 3			#3 => Real 5.0s
	SECOND_THREAD_PERIOD = 0.1	#0.1s => Real 0.2s
	THIRD_THREAD_PERIOD = 0.3		#0.3s => Real 0.5s

	#Reset Pin (Low Active)
	GPS_RESET = 27
	ETH_RESET = 34
	UART_RESET = 4

	#LORA_TX_LED = 22	#Lora-TX Pin과 Direct로 연결 되있어서 초기화 하면 Tx 안됨
	COMM_G = 6
	STAT_Y = 12
	DO = 38

	LED_T_COMM = 0
	LED_T_STAT = 1

	GPIO_A_ALL = [GPS_RESET, ETH_RESET, UART_RESET, COMM_G, STAT_Y, DO]

	LED_STATUS = [0,0]	#[Total_PROC_STAT, Internet]
	ledSelIdx = [0,0]
	ledToggle = [0,0]

	#bTestStatus = 0

	loggingCnt = 0
	mThreadKill = 0
	dLcd = None

	th1 = None
	th2 = None
	th3 = None

	seq = 0

	#GEuid Path
	jsonPath = '/opt/semtech/packet_forwarder/lora_pkt_fwd/local_conf.json'

	#Process Path
	path = os.path.abspath(sys.argv[0])
	mainPath = path[0:path.rfind('/')]

	#Rs485
	rs485Flag = False
	ser = None

	#PBA test Mode
	pbaTest = False
	ledStop = False

	SERIAL_LEN  = 14
	EUID_LEN = 16

	EUID_ADDR_OFFSET = 20

	nicType = 0	#0:eth, 1:wi-fi, 2:LTE, 99:ALL

	pingCnt = 298

	def __init__(self, log_file=None):
		global th1, th2

		self.logger = self.initLogger("pCheck", log_file)
		self.__stop = False

		signal.signal(signal.SIGINT, self.stop)
		signal.signal(signal.SIGTERM, self.stop)

		self.logger.info("ProcessChk Start===================>")

		#LED Gpio Init
		self.gpio_Init()
		self.gpio_InitVal()

		#Gpio Reset
		self.softwareReset()

		#LCD Class Init
		self.dLcd = lcd_Class()
		self.logger.info("Start Check, PID {0}".format(os.getpid()))

		#Read Host Name
		self.setHostName()

		#Gateway Euid Check
		self.initGEuidCheck()

		#ssh Disable
		#os.system("sudo systemctl disable ssh")

		self.logger.info("Init Complete")

	def rs485Init(self):
		## lsusb 명령어를 통해서 device id를 가진 장치가 있는지 확인
		deviceID = "0403:6015"
		result = ""

		try:  result = subprocess.check_output("lsusb | grep "+deviceID, shell=True, stderr=subprocess.STDOUT)
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
						self.processCheck()
						#self.gpsCheck()
						self.rs485Trans("PBA Test End")

					elif -1 < totalStr.find("IP"):					self.ipCheck()
					elif -1 < totalStr.find("GET_EUID"):		self.getEuidNum()
					elif -1 < totalStr.find("GET_SERIAL"):	self.getSerialNum()
					elif -1 < totalStr.find("SET_SERIAL"):	self.setSerialNum(totalStr.split('=')[1].split())
					elif -1 < totalStr.find("DEL_SERIAL"):	self.delSerialNum()
					elif -1 < totalStr.find("_SSH_ON_"):	self.setSSH(22)
					elif -1 < totalStr.find("_SSH_OFF_"):  self.setSSH(0)

				self.ser.flushInput()

			else:
				self.keyTimeout += 1
				if self.keyTimeout > 4: #main에서 0.5ms 이므로 2sec
					self.keyTimeout = 0
					totalStr = ""

		except:
			print ("Except : rs485Process")

	#IP Address Check
	def ipCheck(self):
		try:
			ipList = subprocess.check_output(['hostname', '--all-ip-addresses']).split()

			msg = "ipAddress : "
			for i in ipList:	msg = msg + i.decode('utf-8') + " "
			self.rs485Trans(msg)

		except:
			print ("Except ipCheck")


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
			eep = I2C_EEPROM()

			type = eep.read_byte(3)
			if type == 90:    nicType = 99	#All
			elif type == 87:  nicType = 1		#Wifi
			elif type == 76:  nicType = 2		#LTE
			else: nicType = 0								#Eth

			print ("nicType : " + str(nicType))

		except:
			print ("Except : getNicType")

		self.nicType = nicType

	def initGEuidCheck(self):
		try:
			#read eeprom
			eep = I2C_EEPROM()
			result = []

			self.getNicType()

			for i in range(self.EUID_LEN):
				result.insert(i, eep.read_byte(self.EUID_ADDR_OFFSET + i))
			eepEuid = bytes(result).decode('utf-8').split()[0]

			fp = open(self.jsonPath, mode='r')
			lines = fp.readlines()
			fp.close()

			for idx, val in enumerate(lines):
				if val.find("gateway_ID") != -1:
					jsonEuid = val.split(':')[1].replace("\"",'').replace(' ', '')
					jsonEuid = jsonEuid.split()[0]

			#print (jsonEuid)
			#print (eepEuid)

			if eepEuid != jsonEuid and len(eepEuid) == self.EUID_LEN and eepEuid != "":
				self.writeGeuid(self.jsonPath, eepEuid)
				print ("Difference")
			else:
				print ("Pass")

		except:
			print ("Except initGEuidCheck")

	def setSSH(self, sel):
		if sel == 22:
			os.system("sudo systemctl restart ssh")
			self.rs485Trans("SSH_Enable")
		else:	os.system("sudo systemctl stop ssh")

	def getEuidNum(self):
		#read eeprom
		eep = I2C_EEPROM()
		result = []
		for i in range(self.EUID_LEN):
			result.insert(i, eep.read_byte(self.EUID_ADDR_OFFSET + i))

		result = bytes(result).decode('utf-8')
		self.rs485Trans("getEuid : " + str(result))

	def delSerialNum(self):
		print ("delSerialNum")

		eep = I2C_EEPROM()
		#write eeprom - Serial Number
		for i in range(self.SERIAL_LEN):
			eep.write_byte(i, 0x30)

		#write eeprom - Euid Number (EUID_ADDR_OFFSET)
		for i in range(self.EUID_LEN):
			eep.write_byte(self.EUID_ADDR_OFFSET + i, 0x30)
			#print (rEuid[i].encode()[0])

		self.rs485Trans("DelEuid Complete ")


	def getSerialNum(self):
		#read eeprom
		eep = I2C_EEPROM()
		result = []
		for i in range(self.SERIAL_LEN):
			result.insert(i, eep.read_byte(i))

		result = bytes(result).decode('utf-8')
		self.rs485Trans("getSerial : " + str(result))

	def setSerialNum(self, seri):
		try:
			eep = I2C_EEPROM()

			serStr = seri[0].replace('-', '')
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
			#"eth0", "wlan0", "wwan0"
			nicList = ["eth0", "wlan0", "wwan0"]
			nicRestart = 0

			#네트웤 연결 중에는 5분마다 체크 / 끊어진 경우 1분 마다 체크
			if self.LED_STATUS[1] == 0:	pingCntLimit = 60
			else:	pingCntLimit = 300

			#mainThread (1sec) * 300Cnt = 5min
			self.pingCnt += 1
			if self.pingCnt >= pingCntLimit:
				self.pingCnt = 0
				pingChkFlag = 1
				fiveMinFlag = 1

			#print ("")
			#print ("")
			#print ("")
			#print ("")
			#self.logger.info("++++++++++++++++++++++++++++++++++++++nicDiscCheck")

			for i, nic in enumerate(nicList):
				try:
					#exist Check
					if os.path.isdir("/sys/class/net/" + nic) == False:
						self.nicStatus[i][0] = 0
						#self.logger.info("Exist Continue " + nic)
						continue

					#up/down Check
					cmd = "sudo cat /sys/class/net/" + nic + "/operstate"
					if subprocess.getoutput(cmd) == "down":
						tempNicStatus[i][0] = 0
						tempNicStatus[i][1] = 0
						tempNicStatus[i][2] = 0
						self.logger.info("Down " + nic)
						self.nicStatus[i] = tempNicStatus[i]
						continue
					else:	tempNicStatus[i][0] = 1

					self.nicStatus[i][0] = 1

					#ip Address Check
					cmd = "sudo ifconfig " + nic + " | grep 'inet '"
					nicStat = subprocess.getoutput(cmd)

					if nicStat == None:	tempNicStatus[i][1] = None
					else:	tempNicStatus[i][1] = nicStat.split()[1]

					print (nic + " : " + tempNicStatus[i][1] + " / " + str(self.nicStatus[i][1]))

					#ip 변경 발생
					if tempNicStatus[i][1] != self.nicStatus[i][1]:
						pingChkFlag = 1
						self.pingCnt = 0

					self.nicStatus[i][1] = tempNicStatus[i][1]

					#ping Check
					#mainThread (1sec) * 300Cnt = 5min or IP Change
					if pingChkFlag == 1:
						#pingChkFlag = 0
						print ("=============================> " + nic + " pingChkFlag = 1")

						result = subprocess.getoutput("sudo fping -I " + nic + " -t 1000 -b 1 8.8.8.8")
						self.logger.info(result)

						if result.find("alive") != -1:
							tempNicStatus[i][2] = 1
							print (nic + "------------------------------------->  Alive")

						self.nicStatus[i][2] = tempNicStatus[i][2]
						self.logger.info("Ping_Chk")

						#5min 마다 check
						if fiveMinFlag == 1:
							#ip 할당 못 받았을때...
							if self.nicStatus[i][1] == '127.0.0.1' or self.nicStatus[i][1] == '192.168.2.1' or self.nicStatus[i][1].split('.')[0] == '169':
								#Nic Restart
								os.system("sudo ifdown " + nic)
								time.sleep(2)
								os.system("sudo ifup " + nic + " &")
								self.logger.info(nic + " Nic Restart")
							else:
								print (nic + " Nic Running")

				except:
					print ("Except For " + nic)

			print ("_____________________________________________")
			print (self.nicStatus)

		except:
			self.logger.info("Except nicDiscCheck " + nic)

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
				subprocess.check_output(['fping', '-I', msg[idx], '-t', '1000', '8.8.8.8']).decode('utf-8')
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
			#hostName = os.popen('cat /etc/hostname').read().strip()
			#print ("host:" + hostName)
			readStr = os.popen('cat /opt/semtech/ampla/version').read()
			version = readStr[0:readStr.find("\n")].rstrip().replace('.', '')
			hostName = "AMPLA " + version[version.find(':')+1:len(version)].strip()
			print ("HostName : " + hostName)

			if hostName != hostName:
				print ("HostName Different")
				f = open('/etc/hostname', 'w')
				f.write(hostName)
				f.close()

				readList = self.readFileList('/etc/hosts')
				findIdx = self.findStrList(readList, '127.0.1.1')
				if findIdx > -1:
					readList[findIdx] = "127.0.1.1	" + hostName
					f = open('/etc/hosts', 'w')
					f.write('\n'.join(readList))
					f.close()

				print (readList)

		except:
			print ("Except setHostName")


	#Thread ################################################################################################
	#Process Thread	(1s)
	lcdPrintCnt = 0
	def main_Thread(self):
		if self.mThreadKill == 1:	return

		try:
			#Lcd_Status Print
#			self.lcdPrintCnt += 1
#			if self.lcdPrintCnt >= 3:
#				self.lcdPrintCnt = 0
			self.dLcd.lcd_print()

#			#10초 주기 - Check
#			self.mainThread_Cnt += 1
#			if self.mainThread_Cnt >= 10:	#10s
#				self.mainThread_Cnt = 0
#				#self.logger.info("Main_Thread_Chk") #10s

			#Nic Disccnect Check(eth0)
			self.nicDiscCheck()

			#LED_STATUS(Process / Network) Check
			self.statusChk()

			#getNicType별 Up/Down
			self.getNicType()

			#LTE Init Check (10s)
			#wwan0 이 up 이지만, IP 할당을 못 받은 경우 Reset
			if ( self.nicType == 2 or self.nicType == 99 ) and self.nicStatus[2][0] == 1:
				#self.logger.info("Lte_Ping_Chk")
				if self.nicStatus[2][1] == '169' or self.nicStatus[2][2] == 0:
					self.logger.info("Lte_Stat_Chk(169.xxx.xxx.xxx)")
					self.ltePing()

		except:
			print ("Except mainThread")

		self.th1 = threading.Timer(self.MAIN_THREAD_PERIOD, self.main_Thread)
		self.th1.start()

	#Board Test Thread (0.2s)
	rs485InitCnt = 500
	def second_Thread(self):
		if self.mThreadKill == 1:	return

		#rs485 - Board Test
		if self.rs485Flag == False:
			self.rs485InitCnt += 1
			if self.rs485InitCnt > 300:	#1min
				self.rs485InitCnt = 0
				self.rs485Init()
		else:
			self.rs485Process()

		self.th2 = threading.Timer(self.SECOND_THREAD_PERIOD, self.second_Thread)
		self.th2.start()

	#LED Check Thread	(0.5s)
	def third_Thread(self):
		if self.mThreadKill == 1:	return

		#Status LED Blink
		if self.pbaTest == False:
			self.ledStop = True
			self.led_Func(self.LED_STATUS)
			self.ledStop = False

		self.th3 = threading.Timer(self.THIRD_THREAD_PERIOD, self.third_Thread)
		self.th3.start()

	def main(self):
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
			print (lines)

			for idx, val in enumerate(lines):
				if val.find("gateway_ID") != -1:
					list = val.split(':')
					list[1] = "\"" + value + "\""
					lines[idx] = list[0] + ":" + list[1] + "\n"
					print (lines[idx])
				else:
					print (val)

			print ("----------------------")
			print (lines)

			fp = open(fName, mode='w')
			fp.write(''.join(lines))
			fp.close()

		except:
			print ("Except writeGeuid")

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

	def checkWebServer(self):
		try:
#			result = self.tcpping('127.0.0.1', 5050, 3)
			#print("Result : " + str(result))

			if result == False:	return 0
			else:	return 1

		except:
			return 0

	def tcpping(self, host, port, timeout):
		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.settimeout(timeout)
			s.connect((host, int(port)))
			s.shutdown(socket.SHUT_RD)
			return True
		except:
			pass
			return False

	def ltePing(self):
		try:
			alive = 1
			lteModule = 1

			#cmd = ['lsusb', '|', 'grep', 'Telit']
			lsusb = subprocess.check_output('lsusb').decode('utf-8')
			if lsusb.find('Telit') == -1:	lteModule = 0

			print ("lteModule(" + str(lteModule) + ")")

			if lteModule == 1:
				cmd = ['fping', '-I', 'wwan0', '-t', '1000', '-b', '1', '8.8.8.8']
				result = subprocess.check_output(cmd).decode('utf-8')

				if result.find('alive') == -1:
					alive = 1
				else:
					self.logger.info("lte_Alive")
					return True

		except:
			alive = 0
			self.logger.info("Except ltePing")

		if alive == 0:
			print ("lte_reset")
			subprocess.run(['sudo', 'systemctl', 'restart', 'lte_setup.service'])
			self.logger.info("==>(lte_Reset)")
			time.sleep(20)

		return False


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
		try:
			setVal = [GPIO.LOW, GPIO.HIGH]
			ledSequence = [[1,0,1,0,0,0], [1,1,1,0,0,0]]  #비정상[0], 정상[1] - 500ms 기준..

			GPIO.setmode(GPIO.BCM)
			GPIO.setwarnings(False)
			GPIO.setup(self.STAT_Y, GPIO.OUT)
			GPIO.setup(self.COMM_G, GPIO.OUT)

			GPIO.output(self.STAT_Y, setVal[ledSequence[status[0]][self.seq]])
			GPIO.output(self.COMM_G, setVal[ledSequence[status[1]][self.seq]])

			#self.logger.info("Serq : " + str(self.seq) + " / " + str(status[0]) + str(status[1]))

			self.seq += 1
			if self.seq >= len(ledSequence[0]):	self.seq = 0

		except:
			print ("led_Status_Except : GPIO pin is in use in Board Test")
	#LED Func End ########################################################################

#	def networkPrioritySet(self):
#		networkpath = '/etc/dhcpcd.conf'
#		netPriorityTag = "#network_Priority"
#
#		readList = self.readFileList(networkpath)
#		nPriIdx = self.findStrList(readList, netPriorityTag)
#
#		idx = '0'
#		if nPriIdx >= 0:
#			readVal = readList[nPriIdx][18:len(readList[nPriIdx])]
#			idx = int(readVal)
#
#		metric = [202, 202, 202]
#		metric[idx] = 101
#
#		os.system('sudo ifmetric eth0 ' + str(metric[0]))
#		os.system('sudo ifmetric wlan0 ' + str(metric[1]))
#		os.system('sudo ifmetric wwan0 ' + str(metric[2]))
#
#		self.logger.info("priority Set {0}".format(idx))

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

			#LES_STATUS(network) Check
			upStatus = self.nicStatus[0][0] + self.nicStatus[1][0] + self.nicStatus[2][0]
			pingStatus = self.nicStatus[0][2] + self.nicStatus[1][2] + self.nicStatus[2][2]

			#for i, nic in enumerate(self.nicStatus):	print (nic)

			if upStatus > 0 and pingStatus > 0:	result2 = 1
			else:	result2 = 0

		except:
			self.logger.info("Except processChk")

		self.LED_STATUS[0] = result1
		self.LED_STATUS[1] = result2


#		return result

	#Logger #############################################################################################
	def initLogger(self, processName, file):
		#Logging
		logArray = ["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
		logLevel = logging.WARNING  #Log Level Default Warning

		#Config Read
		if os.path.isfile(self.mainPath + "/" + processName + ".conf"):
			list = self.readFileList(self.mainPath + "/" + processName + ".conf")
			level = list[self.findStrList(list, 'logLevel')].replace('\n','').split('=')[1]
			print ("file Found")

			lIdx = 0
			for val in logArray:
				if val == level:
					self.logLevel = lIdx * 10
				lIdx+=1

		else:
			print ("No file Found")

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


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("--log", help="log filename", default=None)
	args = parser.parse_args()

	p_chk = ProcessChk(args.log)
	p_chk.main()
