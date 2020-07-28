import time
import smbus
import binascii


class I2C_EEPROM():
	# Get I2C bus
	bus = smbus.SMBus(1)

	# I2C address of the device
	EEPROM_DEFAULT_ADDRESS = 0x50
	EEPROM_DELAY = 0.005

	def read_byte(self, addr):
		""" byte 단위로 읽기  """
		return self.bus.read_byte_data(self.EEPROM_DEFAULT_ADDRESS, addr)

	def write_byte(self, addr, data):
		""" byte 단위로 쓰기 """
		result = self.bus.write_byte_data(self.EEPROM_DEFAULT_ADDRESS, addr, data)
		time.sleep(self.EEPROM_DELAY)
		#print ('write byte : ' + str(data))

	def read_data(self, addr, len):
		return self.bus.read_i2c_block_data(self.EEPROM_DEFAULT_ADDRESS, addr, len)

	def write_data(self, addr, data):
		self.bus.write_i2c_block_data(self.EEPROM_DEFAULT_ADDRESS, addr, data)
		time.sleep(self.EEPROM_DELAY)
		#print ('write data : ')
		#print ( data)


##################################################

eep = I2C_EEPROM()

for i in range(5):
	eep.write_byte(i, i*2)
	eep.read_byte(i)
	eep.write_byte(i, i*3)
	eep.read_byte(i)

	print ("------------------\r\n")

value = eep.read_data(0, 5)
print (value)

readVal = eep.read_data(0, 8)
print (readVal)

#euid(str)
euid = "b827ebfffe86b856"
print (euid)

#euid(list)
listVal = list(euid.encode())
print (listVal)

#write eeprom
idx = 0
for i in listVal:
	eep.write_byte(idx, i)
	idx += 1

#read eeprom
result = []
for idx in range(16):
	result.insert(idx, eep.read_byte(idx))

print (bytes(result).decode('utf-8'))


for i in range(256):
	print ("address[" + str(i) + "] : " + str(eep.read_byte(i)))
