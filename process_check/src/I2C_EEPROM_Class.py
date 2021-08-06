import time
import smbus
import RPi.GPIO as GPIO


class I2C_EEPROM():

	#GPIO Set
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)

	GPIO.setup(40, GPIO.OUT)
	GPIO.output(40, GPIO.HIGH)	#EEPROM Write Protect


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
			print ("EEP_Read_byte_Err")
			return -1


	def write_byte(self, addr, data):
		""" byte 단위로 쓰기 """
		try:
			GPIO.output(40, GPIO.LOW)
			self.bus.write_byte_data(self.EEPROM_DEFAULT_ADDRESS, addr, data)
			time.sleep(self.EEPROM_DELAY)
			result = 1
			#print ('write byte : ' + str(data))
		except:
			result = -1
			print ("EEP_Write_Byte_Err")
		finally:
			GPIO.output(40, GPIO.HIGH)
			return result

	def read_data(self, addr, len):
		try:
			return self.bus.read_i2c_block_data(self.EEPROM_DEFAULT_ADDRESS, addr, len)
		except:
			print ("EEP_Read_data_Err")
			return -1

	def write_data(self, addr, data):
		try:
			GPIO.output(40, GPIO.LOW)
			self.bus.write_i2c_block_data(self.EEPROM_DEFAULT_ADDRESS, addr, data)
			time.sleep(self.EEPROM_DELAY)
			result = 1
			#print ('write data : ')
			#print ( data)

		except:
			result = -1
			print ("EEP_Write_data_Err")

		finally:
			GPIO.output(40, GPIO.HIGH)
			return result



##################################################
"""
eep = I2C_EEPROM()



for i in range(5):
	eep.write_byte(i, 0xff)

for i in range(5):
  print (eep.read_byte(i))

print ("------------------\r\n")

for i in range(5):
	eep.write_byte(i, i*3)

for i in range(5):
	print (eep.read_byte(i))

print ("------------------\r\n")


print (eep.read_data(0, 5))

list = [0xff, 0xf0, 0xe0]
eep.write_data(1, list)
print (eep.read_data(0, 5))

"""
