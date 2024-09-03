from bluepy import btle
from enum import Enum
import time
import pandas as pd
import logging
import RPi.GPIO as GPIO
from roland_message import Message
from roland_address import RolandAddressMap
from roland_instruments import Instruments
import config as cfg



log = logging.getLogger(__name__)
key_recorder = logging.getLogger("KeyRecorder")
#echo 35 | sudo tee /sys/kernel/debug/bluetooth/hci0/conn_max_interval

#According to ble-midi spec, connection should be established at the lowest possible (<15ms).
#I set /sys/kernel/debug/bluetooth/hci0/conn_max_interval to 12 and min to 8 to get 15ms.
#units of 1.25ms, 12 x 1.25 = 15ms, 8 x 1.25 = 10ms.
#min: 24 max: 40 originally

#Actually, I found out it doesn't work unless the max_interval is is >32x1.25 = 40ms...
#I am guessing the piano doesn't want to negotiate, sticking with 40ms (37.5ms actually).

#Yes, I found it. "You should always give a Roland module about 40 milliseconds to process 
# a "Data Set 1" message that you send it, before subsequently sending another MIDI message 
# (including another "Data Set 1") to the module. If you don't, the module may report an error."

# TODO: yaml files?
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

# dictionary of key : bytesarray  value : corresponding class(Instruments)




def note_string_to_midi(midstr):
    notes = [["C"],["C#","Db"],["D"],["D#","Eb"],["E"],["F"],["F#","Gb"],["G"],["G#","Ab"],["A"],["A#","Bb"],["B"]]
    answer = 0
    i = 0
    #Note
    letter = midstr.split('-')[0].upper()
    for note in notes:
        for form in note:
            if letter.upper() == form:
                answer = i
                break
        i += 1
    #Octave
    answer += (int(midstr[-1]))*12
    print(f"note in int : {answer}") #C2 36 C3 48 C4(mid) 60
    #TODO: Key in log starts from 0, where in midi it starts from 21 (-1 A)
    return int_to_byte(answer)



fields = {}

def int_to_byte(num):
    return num.to_bytes(1, byteorder="big")

def data_as_bytes(data_as_int):
    parsers = {
        "sequencerTempoWO": lambda x: int_to_byte((x & 0xFF80) >> 7) + int_to_byte(x & 0x7F),
        "keyTransposeRO": lambda x: int_to_byte(x + 64),
        "toneForSingle": lambda x: int_to_byte((x & 0xFF000) >> 16) + b"\00" + int_to_byte(x & 0xFF),
    }
    ret = parsers["toneForSingle"](data_as_int)
    return ret


# categoryNo: parseInt(data.substr(0, 2), 16),
# number: parseInt(data.substr(2, 2), 16) * 128 + parseInt(data.substr(4, 2), 16)

def get_parser(addressName):
    pass
    """parsers = {
        "sequencerTempoRO": lambda data: (data[1] & b"\x7F"[0]) | ((data[0] & b"\x7F"[0]) << 7),
        "keyTransposeRO"  : lambda x  : x[0]-64,
        "toneForSingle" : lambda x : Instruments((x[0],x[2]))
    }

    if addressName in parsers:
        return parsers[addressName]
    else:
        return byte_to_int"""




midi_data = bytearray()
class MyDelegate(btle.DefaultDelegate):
    message = Message()
    def __init__(self, params = None):
        btle.DefaultDelegate.__init__(self)
        

    def handleNotification(self, cHandle, data):
        status = self.message.append(data)
        # prefix; the length in bytes for the following midi message
        midi_data.extend(len(data).to_bytes(1, byteorder="little")) 
        midi_data.extend(data)
        print(f"data : {data.hex()}")
        if status == 1:
            self.message.decode()
        elif status == -1:
            log.error("Not a valid message")
            log.error(self.message)
        

class RolandPiano(btle.Peripheral):
    service_uuid        = "03b80e5a-ede8-4b33-a751-6ce34ec4c700"
    characteristic_uuid = "7772e5db-3868-4112-a1a9-f2669d106bf3"
    setup_data = b"\x01\x00" #data we need to write to enable notification on a certain characteristic
    def save_to_file(self, filename):
        # Write the MIDI data to a file
        with open(filename, 'wb') as midi_file:
            midi_file.write(midi_data)

    def parse_midi(self, filename):
        with open(filename, "rb") as midi_file:
            while True:
                # Read the length byte
                length_byte = midi_file.read(1)
                if not length_byte:
                    # If the length byte is empty, we have reached the end of the file
                    break
                # Convert the length byte to an integer to determine the size of the MIDI message
                length = ord(length_byte)
                print(f"length of midi msg: {length}")
                if length == 13:
                    midi_message = midi_file.read(9)
                    ts_byte = midi_message[0:1]
                    print(f"midi message: {midi_message}")
                    self.writeCharacteristic(16, midi_message, withResponse=False)
                    midi_message = midi_file.read(4)
                    print(f"midi message: {ts_byte+midi_message}")
                    self.writeCharacteristic(16, ts_byte+midi_message, withResponse=False)
                else:    
                    midi_message = midi_file.read(length)
                    print(f"midi message: {midi_message}")
                    
                    self.writeCharacteristic(16, midi_message, withResponse=False)

    """
    Returns the instrument of the piano currently set to piano
    """
    def get_instrument(self):
        # print(self.read_register("toneForSingle"))
        self.read_register("toneForSingle")
        self.instrument = MyDelegate.message.instrument
        # return self.read_register("toneForSingle")
        return self.instrument

    """
    Sets the instrument of the piano to params: inst
    """
    def set_instrument(self, inst: Instruments):
        value = (inst.value[0] << 16) | inst.value[1]
        self.instrument = inst
        self.write_register('toneForSingle', data_as_bytes(value))

        
    def build_handle_table(self):
        cols = ['handle','uuid_bytes','uuid_str']
        rows = []
#         handle                            uuid_bytes                              uuid_str
# 0       1  00002800-0000-1000-8000-00805f9b34fb  00002800-0000-1000-8000-00805f9b34fb
# 0       2  00002803-0000-1000-8000-00805f9b34fb  00002803-0000-1000-8000-00805f9b34fb
# 0       3  00002a00-0000-1000-8000-00805f9b34fb  00002a00-0000-1000-8000-00805f9b34fb
# 0       4  00002803-0000-1000-8000-00805f9b34fb  00002803-0000-1000-8000-00805f9b34fb
# 0       5  00002a01-0000-1000-8000-00805f9b34fb  00002a01-0000-1000-8000-00805f9b34fb
# 0       6  00002803-0000-1000-8000-00805f9b34fb  00002803-0000-1000-8000-00805f9b34fb
# 0       7  00002a04-0000-1000-8000-00805f9b34fb  00002a04-0000-1000-8000-00805f9b34fb
# 0       8  00002800-0000-1000-8000-00805f9b34fb  00002800-0000-1000-8000-00805f9b34fb
# 0       9  00002800-0000-1000-8000-00805f9b34fb  00002800-0000-1000-8000-00805f9b34fb
# 0      10  00002803-0000-1000-8000-00805f9b34fb  00002803-0000-1000-8000-00805f9b34fb
# 0      11  00002a29-0000-1000-8000-00805f9b34fb  00002a29-0000-1000-8000-00805f9b34fb
# 0      12  00002803-0000-1000-8000-00805f9b34fb  00002803-0000-1000-8000-00805f9b34fb
# 0      13  00002a50-0000-1000-8000-00805f9b34fb  00002a50-0000-1000-8000-00805f9b34fb
# 0      14  00002800-0000-1000-8000-00805f9b34fb  00002800-0000-1000-8000-00805f9b34fb
# 0      15  00002803-0000-1000-8000-00805f9b34fb  00002803-0000-1000-8000-00805f9b34fb
# 0      16  7772e5db-3868-4112-a1a9-f2669d106bf3  7772e5db-3868-4112-a1a9-f2669d106bf3
# 0      17  00002902-0000-1000-8000-00805f9b34fb  00002902-0000-1000-8000-00805f9b34fb
        # service = self.getServiceByUUID(self.service_uuid)
        # character = service.getCharacteristics(self.characteristic_uuid)[0]
        # for c in service.getCharacteristics(self.characteristic_uuid):
        #     print(c)
        # Basically, the service we are interested in has 1 characteristic 7772e5db... with an 
        # additioanl descriptor for CCCD (enabling/disabling notification for that characteristic).
        for desc in self.getDescriptors(): #service.getDescriptors() give handles 16 and 17.
            rows.append(pd.DataFrame([{'handle' : desc.handle, 'uuid_bytes' : desc.uuid, 'uuid_str' : str(desc.uuid)}],columns = cols))

        self.handle_table = pd.concat(rows)

    def get_checksum(self,addr,data):
        total = 0
        for b in addr:
            total += b
        for b in data:
            total += b        
        return int_to_byte(128 - (total % 128))        

    def access_register(self,addressName,data=None):
        readRegister = False

        addr      = RolandAddressMap.addresses[addressName]
        # ut        = self.get_unix_time()
        # header    = self.get_header(ut)
        # timestamp = self.get_timestamp(ut)    
        ut = self.get_time_ms()
        header, timestamp = self.create_ble_midi_header(ut)
        header = header.to_bytes(1,byteorder='little')
        timestamp = timestamp.to_bytes(1,byteorder='little')  

        if data == None: # Read register
            data      = b"\x00\x00\x00" + int_to_byte(RolandAddressMap.get_address_size(addressName))
            #TODO: Change this data to size of bytes represented in 4 bytes. Currently Assuming limited size(represented by 1 byte) here..
            readRegister = True

        checksum = self.get_checksum(addr,data)
        cmd      = lut['cmd_read'] if readRegister else lut['cmd_write']

        msg_base = header + timestamp + lut['sysex_msg_start'] + \
            lut['id_roland'] + \
            cmd + \
            addr + \
            data + \
            checksum  

        if readRegister:
            # I need to split packets since the size of msg is 21 bytes (>20bytes)
            first_packet = msg_base
            second_packet = header + timestamp + lut['sysex_msg_end']
            print(f"msg for requesting : {(first_packet + second_packet).hex() }")
            self.writeCharacteristic(16,first_packet,withResponse=False)
            self.writeCharacteristic(16,second_packet,withResponse=False)
            self.waitForNotifications(2.0) #twice as 1 waitfornotification waits for one notify.
            #The sysex we get may be consisted of more than 1 packets..
        else:
            msg = msg_base + timestamp + lut['sysex_msg_end']
            print(self.start_time)
            print(f"Msg i am writing : {msg.hex()}")
            self.writeCharacteristic(16,msg)

        self.waitForNotifications(2.0)


    def read_register(self,addressName):
        self.access_register(addressName)

    def write_register(self,addressName,data):
        self.access_register(addressName,data)
    
    def get_time_ms(self):
        return int((time.time() - self.start_time) * 1000) % 8192
    
    #header byte : 0x80 (128) to 0xBF(191)
    #timestamp byte : 0x80 (128) to 0xFF (255)
    def create_ble_midi_header(self, time_ms):
        header = 0x80 | ((time_ms >> 7) & 0x3F)  # MSB of the timestamp goes into header
        timestamp = 0x80 | ((time_ms) & 0x7F)  # Remaining 7 bits for timestamp
        return header, timestamp
    
    # This function plays a pre-downloaded midiFile mid on the piano
    def play_mid(self, mid):
        # inst = self.get_instrument() maybe inefficient?
        inst = self.instrument
        print(f"inst for this midi player : {str(inst)}")
        bank_msb = inst.value[2]
        bank_lsb = inst.value[3]
        pc = inst.value[4] - 1
        ut = 0
        input_time_ms = ut
        for count, msg in enumerate(mid.play()):
            if not GPIO.input(3):
                return
            input_time_ms = int((input_time_ms + msg.time * 1000) % 8192)          
            midi_msg = msg.bin()
            # if (msg.type == 'program_change'):
            #     # extract channel number nibble(4-bits) ex) 0xb0's 0 and 0xb1's 1.
            #     msg_channel = (midi_msg[0] & 0xF)
                
            #     # bank_msb = 16
            #     # bank_lsb = 67
            #     # pc = 0
            #     # calculate the 2 cc messages to send for bank select
            #     # First : BnH 00H msbH 
            #     # Second : BnH 20H lsbH
            #     bank_select_msb = (0xb0 | msg_channel).to_bytes(1, byteorder='big') + b'\x00' + bank_msb.to_bytes(1, byteorder='big')
            #     bank_select_lsb = (0xb0 | msg_channel).to_bytes(1, byteorder='big') + b'\x20' + bank_lsb.to_bytes(1, byteorder='big')
            #     pc_msg = (0xc0 | msg_channel).to_bytes(1, byteorder='big') + pc.to_bytes(1, byteorder='big')
            #     #pack 3 midi msgs into one packet
            #     header, timestamp = self.create_ble_midi_header(input_time_ms)
            #     header = header.to_bytes(1, byteorder='big')
            #     timestamp = timestamp.to_bytes(1, byteorder='big')
            #     full_pc_msg = (header + timestamp + bank_select_msb
            #               + timestamp + bank_select_lsb
            #               + timestamp + pc_msg)
            #     print(f"full_pc_msg : {full_pc_msg.hex()}")
            #     print(midi_msg.hex())
            #     self.writeCharacteristic(16, full_pc_msg)
            #     continue
            #     midi_msg[1] = 1
            header, timestamp = self.create_ble_midi_header(input_time_ms)      
            self.writeCharacteristic(16, header.to_bytes(1,byteorder='little') 
                                     + timestamp.to_bytes(1,byteorder='little') + midi_msg )
            # print(header.to_bytes(1,byteorder='little') 
            #       + timestamp.to_bytes(1,byteorder='little') + midi_msg)
            # print(str(msg))


            
    def get_handle(self,uuid):
        return self.handle_table.loc[self.handle_table['uuid_str'].str.contains(uuid)].at[0,'handle']

    def get_uuid(self,handle):
        return self.handle_table.loc[self.handle_table['handle'] == handle].at[0,'uuid_bytes']

    def read_all_characteristics(self):
        for _,row in self.handle_table.iterrows():
            self.readCharacteristic(row['handle'])

    isInitialized = False
    def connect(self, max_attempts):
        for attempt_num in range(1,max_attempts+1):
            try:
                log.info(f"Attempt {attempt_num} to connect to {self.mac_addr}")
                if not self.isInitialized:
                    btle.Peripheral.__init__(self, self.mac_addr,"random")
                    self.isInitialized = True
                else:
                    btle.Peripheral.connect(self,self.mac_addr,"random")                    
                break
            except Exception:
                if attempt_num < max_attempts:
                    continue
                else:
                    log.error(f"Was not able to connect to {self.mac_addr} after {max_attempts} attempts..")
                    return False
        log.info(f"Connection with {self.mac_addr} established")
        return True

    def __init__(self,mac_addr):
        self.mac_addr = mac_addr
        self.connect(3)
        self.midi_ble_service = self.getServiceByUUID(self.service_uuid)
        self.midi_ble_characteristic = self.midi_ble_service.getCharacteristics(self.characteristic_uuid)[0]

        self.build_handle_table()
        self.start_time = time.time()
        self.read_all_characteristics()
        self.setDelegate(MyDelegate())
        # attribute with UUID 0x2902 is CCCD
        
        self.writeCharacteristic(self.get_handle('2902'),self.setup_data,withResponse=False)
        
        #print(self.get_handle('2902')) #This returns attribute handle 17
        if not self.readCharacteristic(self.get_handle('2902')) == self.setup_data:
            log.error("Notification not correctly set in descriptor")
        self.write_register('connection',b"\x01")
        #print(self.handle_table)
        log.info("Initialisation sequence completed")
        self.instrument = self.get_instrument()
        if self.instrument == None:
            print("yes it's none")

    def idle(self):
        try:
            self.waitForNotifications(0.0166)
            return
        except btle.BTLEDisconnectError:
            log.error("Disconnected from device, attemping to reconnect")
            if self.connect(3):
                return
            else:
                log.critical("Could not reconnect, exitting")
                raise     

