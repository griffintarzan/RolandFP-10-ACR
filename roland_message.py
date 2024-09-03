import logging
from roland_address import RolandAddressMap
from roland_instruments import Instruments
from roland_instruments import instrument_lookup
log = logging.getLogger(__name__)


lut = {
    "note_on"         : b'\x90',
    "note_off"        : b'\x80',
    "control_change"  : b'\xb0',
    "sysex_msg_start" : b'\xf0',
    "sysex_msg_end"   : b'\xf7',
    "cmd_read"        : b'\x11',
    "cmd_write"       : b'\x12', 
    "id_roland"       : b'\x41\x10\x00\x00\x00\x28'
}
class Message():
    key_status           = {}
    sustained_key_status = {}
    sustain              = 0
    header_byte          = b""
    instrument           = None


    buf = b""
    def __str__(self):
        buffer = ""
        buffer += f"buf: {self.buf.hex()}\n"
        buffer += f"header_byte: {self.header_byte}, timestamp_byte: {self.timestamp_byte}\n"
        buffer += f"status_byte: {self.status_byte}\n"

        for idx,_ in enumerate(self.notes):
            buffer += f"note: {self.notes[idx]}, velocity: {self.velocities[idx]}\n"

        return buffer
        

    def __init__(self):
        for i in range(0,88+1):
            self.sustained_key_status[i] = 0
            self.key_status[i] = 0

    def reset(self):
        self.buf = b""
        self.header_byte    = None
        self.timestamp_byte = None
        self.status_byte    = None

        self.status_bytes   = None
        self.notes          = None
        self.velocities     = None
        self.instrument     = None

        self.man_id         = None
        self.cmd            = None
        self.address        = None
        self.data           = None
        self.checksum       = None
        return

    def getAudioStatusCodes(self):
        return [lut['note_on'], lut['note_off'], lut['control_change']]

    def isAudioMsg(self):
        return self.status_byte in self.getAudioStatusCodes()

    def isValidAudioMsg(self):
        return self.status_byte and self.notes and self.velocities
    
    def isSysExMsg(self):
        return self.status_byte == lut['sysex_msg_start']

    def timeStampChanged(self,data):
        return self.timestamp_byte != data[2:3]

    def sysExMsgEnded(self):
        return (lut['sysex_msg_end'] in self.buf)

    def validSysExMsgLength(self):
        # cmd (2) + address (8) + data (>=1) + checksum (1) 
        #return len(self.buf) >= (2+8+1+1)
        # manufacturerID(1) + 3 0bytes + model_id(1) + cmd (1) + address(4) + data(4) + checksum(1)
        return len(self.buf) >= 15

    def isNewMsg(self, data):
        headerChanged = data[0:1] != self.header_byte
        isMidiMsg = len(data) == 5 and (data[2:3] in self.getAudioStatusCodes())
        return headerChanged or isMidiMsg

    """
    Parse the packet data received(notified) from the piano and add the corresponding message(s) to the buffer 
    
    :param bytearray data: The content of packet in bytes
    :return: 1 If last message was fully finished / 0 if not... (the next packet will cover it) -1 if done with error
    """
    def append(self,data):
        if self.isNewMsg(data):
            # new message, discard old message
            self.reset()
            try:
                self.header_byte    = data[0:1]
                self.timestamp_byte = data[1:2]
                self.status_byte    = data[2:3]
                self.buf            = data[3:]
            except Exception:
                return -1 # done, with errors
            # If the message received is either note_on, note_off, control_change...
            if self.isAudioMsg():

                # len is 5 + ((n-1)*4)
                # n is not larger than 2, so basically a message can hold 3 midi audio updates. 
                #TODO: write more elegantly

                if len(self.buf) == 2: # Contains one midi msg
                    try:
                        print("1 midi message")
                        self.status_bytes = [self.status_byte]
                        self.notes     = [self.buf[0:1]]
                        self.velocities = [self.buf[1:2]]
                    except Exception:
                        return -1  # done, with errors
                elif len(self.buf) == 6: # Contains two midi msgs ('compressed')
                    try:
                        print("2 midi messages")
                        self.status_bytes = [self.status_byte, self.buf[3:4]]
                        self.notes     = [self.buf[0:1],self.buf[4:4+1]]
                        self.velocities = [self.buf[1:2],self.buf[5:5+1]]
                    except Exception:
                        return -1  # done, with errors
                else:
                    #TODO: There may be instances more than 2 midi messages, ex: 13 bytes for 3 midi, 17 bytes for 4 midi, but we dont handle here
                    print("more than 2 midi msgs")

                return 1 # done
        else: #if it's not a new message, we append it to the buffer
            self.buf += data[1:] # append message
    
        if self.isSysExMsg() and self.sysExMsgEnded() and self.validSysExMsgLength(): #If it's a sysex, extract info based on the message
            print("sysex")
            print(self.buf.hex())
            self.buf      = self.buf.split(lut['sysex_msg_end'])[0] # cut the message at the end
            self.man_id   = self.buf[0:6]
            self.cmd      = self.buf[6:6+1]
            self.address  = self.buf[7:7+4]
            l             = len(self.buf)
            self.checksum = self.buf[l-2:l-1] 
            self.data     = self.buf[11:l-2]
            return 1 # done succesfully
        else:
            return 0 # not done

    def get_checksum(self,addr,data):
        total = 0
        for b in addr:
            total += b
        for b in data:
            total += b        
        return int_to_byte(128 - (total % 128))  

    def isValidRolandMsg(self):
        cmp_checksum = self.get_checksum(self.address, self.data)
        correct_size = RolandAddressMap.get_address_size(RolandAddressMap.get_address_name(self.address)) == len(self.data)
        return self.man_id == lut['id_roland'] and self.cmd and self.address and self.checksum == cmp_checksum and correct_size

    """
    Records key, velocites, sustain values after we've gotten the full message(s) from the packet
    TODO: will be used for visualization if needed.
    """
    def decode(self):
        if self.isAudioMsg():
            if self.isValidAudioMsg():
                for idx,_ in enumerate(self.notes):
                    key = byte_to_int(self.notes[idx]) - 21
                    vel = byte_to_int(self.velocities[idx])

                    if self.status_bytes[idx]   == lut['note_on']:
                        self.key_status[key] = vel
                    elif self.status_bytes[idx] == lut['note_off']: #TODO: fix bug when sustain is released and note is not turned of
                        self.key_status[key] = 0
                    elif self.status_bytes[idx] == lut['control_change']:
                        self.sustain = vel

                    log.debug(f"key: {key}, vel: {vel}")
                    log.debug(f"{self.status_bytes[idx].hex()} - note: {self.notes[idx].hex()}, velocity: {self.velocities[idx].hex()}")
                    # key_recorder.debug(f"key: {key}, vel: {vel}")

                log.debug(list(self.key_status.values())[-10:])
                log.debug(f"sustain: {self.sustain}")    

                # # Handle sustain pedal
                if self.sustain == 0:
                    self.sustained_key_status = self.key_status.copy()
                else:
                    for k,_ in self.key_status.items(): 
                        if self.key_status[k] >= self.sustained_key_status[k]: 
                            self.sustained_key_status[k] = self.key_status[k]

                log.debug(list(self.sustained_key_status.values())[-10:])
                return 0

        elif self.isSysExMsg():
            if self.isValidRolandMsg():
                if self.address == RolandAddressMap.addresses["toneForSingle"]:
                    self.instrument = instrument_lookup.get(byte_to_int(self.data), None)
                    # print(instrument_lookup)
                # log.info(f"address: {self.address.hex()}, data: {self.data.hex()}, cmd: {self.cmd.hex()}")
                return 0
        return -1

def int_to_byte(num):
        return num.to_bytes(1,byteorder='big')

def byte_to_int(byte):
        return int.from_bytes(byte,byteorder='big')
    
    