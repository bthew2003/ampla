import RPi.GPIO as GPIO
import subprocess
import time
import signal
import sys

#Gpio(LED, DO) Check
def gpioTest():
	print ("########################")
	print ("#  GPIO Test           #")
	print ("########################")
	msg = [" 1. Green LED Toggle x 2", " 2. Yellow LED Toggle x 2", " 3. Relay Toggle x 2"]

#	#User Switch Test ###############################
#	USER = 1
#	GPIO.setmode(GPIO.BCM)
#	GPIO.setwarnings(False)
#	#GPIO.setup(USER, GPIO.IN, pull_up_down = GPIO.PUD_UP)
#	GPIO.setup(USER, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
#
#	userKey = GPIO.input(USER)
#	prevKey = userKey
#	str = ["Low", "High"]
#
#	while True:
#		userKey = GPIO.input(USER)
#		print (userKey)
#
#		if prevKey != userKey:
#			prevKey = userKey
#			print ("Switch " + str[userKey])
#		time.sleep(1)
##################################################



	LED_G = 6		#Green LED
	LED_Y = 12	#Yellow LED
	DOUT  = 38	#relay

	GPIO_ARRAY = [LED_G,LED_Y,DOUT]
	aLen = len(GPIO_ARRAY)
	SLEEP_TIME = 0.5

	time.sleep(SLEEP_TIME)

	# the same script as above but using BCM GPIO 00..nn numbers
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)

	idx = 0
	for pin in GPIO_ARRAY:
		GPIO.setup(pin, GPIO.OUT)
		GPIO.output(pin, GPIO.LOW)

		print (msg[idx])
		time.sleep(SLEEP_TIME)

		repeat = 0
		while repeat < 2:
			GPIO.output(pin, GPIO.HIGH)
			time.sleep(SLEEP_TIME)
			GPIO.output(pin, GPIO.LOW)
			time.sleep(SLEEP_TIME)
			repeat+=1

		idx+=1

	GPIO.cleanup()


	print ("\r\n")

#NIC Ping Check
def pingTest():
	print ("########################")
	print ("#  PING Test           #")
	print ("########################")
	msg = ["eth0", "wwan0", "wlan0"]
	alive = [[" 1.Ethe : ","alive"], [" 2.Wwan : ","alive"], [" 3.Wlan : ","alive"]]
	idx = 0

	ipList = subprocess.check_output(['hostname', '--all-ip-addresses']).split()
	for byteVal in ipList:
		ipList[idx] = byteVal.decode('utf-8')

		try:
			subprocess.check_output(['fping', '-I', msg[idx], '-t', '300', '8.8.8.8']).decode('utf-8')
			alive[idx][1] = "alive"
		except:
			alive[idx][1] = "dead"

		print (alive[idx][0] + ipList[idx] + "		(" + alive[idx][1] + ")\r")
		idx+=1

	print ("\r\n")

#Packet Forwarder Check
def processCheck():
	print ("########################")
	print ("#  Process Test        #")
	print ("########################")
	pName = ['packet-forwarder', 'mqtt_queue', 'process_check']
	#pName = ['packet-forwarder', 'mqtt_queue', 'chirpstack-network-server']
	msg = [[" 1.p-forwarder		","active"],[" 2.m-Queue		","active"],[" 3.p-Check		","active"]]

	idx = 0
	for name in pName:

		try:
			subprocess.check_output(['sudo','service',name,'status']).decode('utf-8')
			msg[idx][1] = "active"
		except:
			msg[idx][1] = "inactive"

		print (msg[idx][0] + "	(" + msg[idx][1] + ")")
		idx+=1

	print ("\r\n")


#GPS Check
def gpsCheck():
	print ("########################")
	print ("#  GPS Test            #")
	print ("########################")

	try:
		#subprocess.run(['sudo','cat','/dev/ttyAMA0'])
		#p = subprocess.Popen(['sudo','cat','/dev/ttyAMA0'], stdout=subprocess.PIPE, Shell=True)
		p = subprocess.Popen(['sudo','cat','/dev/ttyAMA0'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

		time.sleep(5)
		p.terminate()
		print ("kill")

	except:
		print ("Error_gps")


#main#######################################################
gpioTest()
pingTest()
processCheck()
gpsCheck()
