#!/usr/bin/env python
#-*- coding:utf-8 -*-

import threading
import serial
import time
import subprocess
import re


class rs485Func:
	TX_PERIOD = 2
	RX_PERIOD = 1
	ser = 0
	testCnt = 0
	rsReturnFlag = 0
	rsReturnMsg = ""

	def rs485Tx(self):
		#start()시 실제로 실행되는 부분이다
		#print ("Rs485TX_Start")
		try:
			#msg = "RS485 Transmit Data : " + str(self.testCnt) + "\r\n"
			if self.rsReturnFlag == 1:
				self.ser.write(str.encode(self.rsReturnMsg))
				self.rsReturnFlag = 0
				#print ("Send Message")

			threading.Timer(self.TX_PERIOD, self.rs485Tx).start()

		except KeyboardInterrupt:
			pass


	def rs485Rx(self):
		#start()시 실제로 실행되는 부분이다
		#print ("Rs485_Receive_Start")

		try:
			readStr = self.ser.readline()
			if readStr:
				self.rsReturnMsg = readStr.decode('utf-8')
				self.rsReturnFlag = 1
				#print ("RS485 Receive Data : " + readStr)

			threading.Timer(self.RX_PERIOD, self.rs485Rx).start()

		except KeyboardInterrupt:
			pass



	def init(self):
		## lsusb 명령어를 통해서 device id를 가진 장치가 있는지 확인
		deviceID = "0403:6015"
		result = ""

		try:  result = subprocess.check_output("lsusb | grep "+deviceID, shell=True, stderr=subprocess.STDOUT)
		except subprocess.CalledProcessError as e : result = ""

		if(len(result) == 0):
			print("장치가 발견되지 않았습니다.")
			exit(1)

		# 모든 포트 위치 검색
		try:
			result = subprocess.check_output("ls /dev/ttyUSB*", shell=True, stderr=subprocess.STDOUT)
			# 바이트 배열로 리턴되는 값을 문자열로 변경
			result = str(result)
			# 배열이 b'ABCD'의 형식이므로 앞, 뒤 불필요한 문자 제거
			result = result[2:len(result)-1]

		except subprocess.CalledProcessError as e :
			result = ""

		# 다수의 행이 반환되므로 개행문자로 문자열 분리
		result = result.split('\\n')
		found = False
		print (result)

		port = 0
		for path in result:
			# 포트 패턴 정규식
			portPattern = re.compile('^/dev/ttyUSB[0-9]+$')
			m = portPattern.match(path)
			print (m)

			if(m):
				#올라온 값이 포트값이면, 포트의 PRODUCT정보를 읽어서 장치값 비교
				try:
					result2 = subprocess.check_output("grep PRODUCT= /sys/bus/usb-serial/devices/"+path[4:]+"/../uevent", shell=True, stderr=subprocess.STDOUT)
					# 문자열로 변경
					result2 = str(result2)
					# 배열이 b'PRODUCT=1234/1234/100'과 같은 형식이므로 앞, 뒤 불필요 문자열 제거
					result2 = result2[10:len(result2)-1]
				except subprocess.CalledProcessError as e :
					result2 = "GGGG/GGGG\n"

				# 개행문자와 /으로 문자열 분리
				result2 = result2.split('\\n')[0].split('/')
				# 입력받은 device ID를 :으로 분리
				didHexList = deviceID.split(':')
				# 16진수로 변경하여 확
				if(int(result2[0],16)==int(didHexList[0],16) and int(result2[1],16)==int(didHexList[1],16)):
					print ("장치의 포트를 찾았다(" + path + ")")
					found = True
					port = path
					break;

		self.ser = serial.Serial(port, 115200, timeout=0.2)
		self.ser.close()
		self.ser.open()

		self.rs485Tx()
		self.rs485Rx()



#rs = rs485Func()
#rs.init()
