import RPi.GPIO as GPIO
import time

# to use Raspberry Pi board pin numbers
GPIO.setmode(GPIO.BCM)

#set up the GPIO channels - one input and one output
#GPIO.setup(11, GPIO.IN)
#GPIO.setup(12, GPIO.OUT)

#input from pin 11
#input_value = GPIO.input(11)

#output to pin 12
#GPIO.output(12, GPIO.HIGH)

togg=1

# the same script as above but using BCM GPIO 00..nn numbers
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

SLEEP_TIME = 0.5

LORA_TX_LED = 22
COMM_R = 5
COMM_B = 6
COMM_G = 24
STAT_R = 26
STAT_B = 12
STAT_G = 13
DO = 38
GPIO_ARRAY = [LORA_TX_LED,COMM_R,STAT_R,COMM_B,STAT_B,COMM_G,STAT_G,DO]

for v in GPIO_ARRAY:
	GPIO.setup(v, GPIO.OUT)
	GPIO.output(v, GPIO.LOW)


aLen = len(GPIO_ARRAY)
print(aLen)

i = 0
contrNum = 0

GPIO.output(COMM_R, GPIO.HIGH)
GPIO.output(COMM_G, GPIO.HIGH)
GPIO.output(COMM_B, GPIO.HIGH)

time.sleep(5)

while True:
	contrNum = GPIO_ARRAY[i]
#	contrNum = 38
	GPIO.output(contrNum, GPIO.HIGH)
	time.sleep(SLEEP_TIME)
	print("High(" + str(contrNum) + ")")
	GPIO.output(contrNum, GPIO.LOW)
	time.sleep(SLEEP_TIME)
	print("Low(" + str(contrNum) + ")")

	i+=1
	if i >= aLen:
		i = 0
