#!/usr/bin/env python
#-*- coding:utf-8 -*-

import threading
import serial
import time
import subprocess
import re


SEND_PERIOD = 2
ser = None


class Rs485TX(threading.Thread):
	#클래스 생성시 threading.Thread를 상속받아 만들면 된다
	testCnt = 0

	def __init__(self):
		#__init__ 메소드 안에서 threading.Thread를 init한
		threading.Thread.__init__(self)

	def run(self):
		#start()시 실제로 실행되는 부분이다
		#print ("Rs485TX_Start")

		try:
			msg = "RS485 Transmit Data : " + str(self.testCnt) + "\r\n"
			ser.write(str.encode(msg))
			self.testCnt+=1
			if self.testCnt > 100: self.testCnt = 0

			#print ("Send Message")
			threading.Timer(SEND_PERIOD, self.run).start()

		except KeyboardInterrupt:
			pass


class Rs485RX(threading.Thread):
	#클래스 생성시 threading.Thread를 상속받아 만들면 된다

	def __init__(self):
		#__init__ 메소드 안에서 threading.Thread를 init한
		threading.Thread.__init__(self)

	def run(self):
		#start()시 실제로 실행되는 부분이다
		print ("Rs485_Receive_Start")

		while(1):
			try:
				readStr = ser.readline()
				if readStr:
					readStr = readStr.decode('utf-8')
					print ("RS485 Receive Data : " + readStr)
				time.sleep(0.01)

#				readChar = ser.read()

			except KeyboardInterrupt:
				ser.close()







## lsusb 명령어를 통해서 device id를 가진 장치가 있는지 확인
deviceID = "0403:6015"
result = ""

try:
	result = subprocess.check_output("lsusb | grep "+deviceID, shell=True, stderr=subprocess.STDOUT)

except subprocess.CalledProcessError as e :
	result = ""

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

for path in result:
	# 포트 패턴 정규식
#	portPattern = re.compile('/ttyUSB[0-9]+$')
	portPattern = re.compile('^/dev/ttyUSB[0-9]+$')

	m = portPattern.match(path)
	print (m)

	if(portPattern.match(path)):
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
			#print ("장치의 포트를 찾았다(" + path + ")")
			found = True
			break



if found == True:
	port = path
	ser = serial.Serial(port, 115200, timeout=0.2)
	ser.close()
	ser.open()

	testCnt = 0

	tx = Rs485TX()
	tx.start()

	rx = Rs485RX()
	rx.start()

