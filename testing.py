import bluepy
import time
device_address = "C4:68:F8:B2:78:56"
service_uuid = bluepy.btle.UUID("03b80e5a-ede8-4b33-a751-6ce34ec4c700")
characteristic_uuid = bluepy.btle.UUID("7772e5db-3868-4112-a1a9-f2669d106bf3")

def get_header(unix_time):
        mask_header    = b'\x7f'
        return ((mask_header[0]    & unix_time[0]) | b'\x80'[0]).to_bytes(1,byteorder='little') #0b10000000
def get_timestamp(unix_time):
        mask_timestamp = b'\x3f'
        return ((mask_timestamp[0] & unix_time[0]) | b'\x80'[0]).to_bytes(1,byteorder='little') #0b10000000

def get_unix_time():
	return int(bin(int(time.time()))[-8:],2).to_bytes(1,byteorder='little')

ut = get_unix_time()
print(ut)
header = get_header(ut)
timestamp = get_timestamp(ut)
sysex_start = b"\xf0"
sysex_end = b"\xf7"
write = b"\x12"
data = b"\x01"
register = b"\x01\x00\x05\x09"
id_bytes = b"\x41\x10\x00\x00\x00\x28"
checksum = b'p'
msg_base = header + timestamp + sysex_start + \
	id_bytes + \
	write + \
	register + \
	data + \
	checksum
print(msg_base)
msg = msg_base + timestamp + sysex_end
print(msg)
print(ut)
print(header)
print(timestamp)
try:
        peripheral = bluepy.btle.Peripheral(device_address, bluepy.btle.ADDR_TYPE_RANDOM)
        service = peripheral.getServiceByUUID(service_uuid)
        characteristic = service.getCharacteristics(characteristic_uuid)[0]
        peripheral.writeCharacteristic(16, msg)

finally:
	print("done")
#	peripheral.disconnect()
