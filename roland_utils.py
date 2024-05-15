import time
#TODO:Should the timestamp value of a subsequent
# MIDI message in the same packet overflow/wrap (i.e., the timestampLow is smaller than a
# preceding timestampLow), the receiver is responsible for tracking this by incrementing the
# timestampHigh by one (the incremented value is not transmitted, only understood as a result of the
# overflow condition).  Only one may occur.
#Header Byte :6 MSBit(timestampHigh) of timestamp + 0 + 1
def get_header(unix_time):
        mask_header    = b'\x7f'
        return ((mask_header[0]    & unix_time[0]) | b'\x80'[0]).to_bytes(1,byteorder='little') #0b10000000

#TimeStamp Byte : 7 LSBit(timestampLow) of time stamp + 1
def get_timestamp(unix_time):
    mask_timestamp = b'\x3f'
    return ((mask_timestamp[0] & unix_time[0]) | b'\x80'[0]).to_bytes(1,byteorder='little') #0b10000000




def get_unix_time():
    return int(bin(int(time.time()))[-8:],2).to_bytes(1,byteorder='little')

print(get_unix_time()[0])