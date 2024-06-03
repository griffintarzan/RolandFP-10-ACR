from bluepy import btle
from enum import Enum
import time
import pandas as pd
import logging
import mido
log = logging.getLogger(__name__)
key_recorder = logging.getLogger("KeyRecorder")
#echo 35 | sudo tee /sys/kernel/debug/bluetooth/hci0/conn_max_interval

#According to ble-midi spec, connection should be established at the lowest possible (<15ms).
#I set /sys/kernel/debug/bluetooth/hci0/conn_max_interval to 12 and min to 8 to get 15ms.
#units of 1.25ms, 12 x 1.25 = 15ms, 8 x 1.25 = 10ms.
#min: 24 max: 40 originally

#Actually, I found out it doesn't work unless the max_interval is is >32x1.25 = 40ms...
#I am guessing the piano doesn't want to negotiate, sticking with 40ms (37.5ms actually).

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

class Instruments(Enum):
    GRAND_PIANO_1 = (0, 0)
    GRAND_PIANO_2 = (0, 1)
    GRAND_PIANO_3 = (0, 2)
    GRAND_PIANO_4 = (0, 3)
    E_PIANO = (0, 4)
    WURLY = (0, 5)
    CLAV = (0, 6)
    JAZZ_ORGAN_1 = (0, 7)
    PIPE_ORGAN = (0, 8)
    JAZZ_SCAT_1 = (0, 9)
    STRINGS_1 = (0, 10)
    PAD = (0, 11)
    CHOIR_1 = (0, 12)
    NYLON_STR_GTR = (0, 13)
    ABASS_CYMBAL = (0, 14)


    E_PIANO_1 = (1, 0)
    E_PIANO_2 = (1, 1)
    E_PIANO_3 = (1, 2)
    HARP = (1, 3)
    VIBRAPHONE = (1, 4) 
    CELESTA = (1, 5)
    SYNTH_BELL = (1, 6)
    STRINGS_2 = (1, 7)
    HARP_2 = (1, 8)
    JAZZ_ORGAN_2 = (1, 9)
    RANDOM_ORGAN = (1, 10)
    ACCORDION = (1, 11)
    STRINGS_3 = (1, 12)
    CHOIR_2 = (1, 13)
    DECAY_STRINGS = (1, 14)
    STEEL_STR_GTR = (1, 15)
    STRINGS_4 = (1, 16)
    SYNTH_PAD = (1, 17)
    RANDOM_GTR = (1, 18)
    CLAV_2 = (1, 19)
    JAZZ_SCAT_2 = (1, 20)



def int_to_byte(num):
    return num.to_bytes(1,byteorder='big')

def byte_to_int(byte):
    return int.from_bytes(byte,byteorder='big')

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
    parsers = {
        "sequencerTempoRO": lambda data: (data[1] & b"\x7F"[0]) | ((data[0] & b"\x7F"[0]) << 7),
        "keyTransposeRO"  : lambda x  : x[0]-64,
        "toneForSingle" : lambda x : Instruments((x[0],x[2]))
    }

    if addressName in parsers:
        return parsers[addressName]
    else:
        return byte_to_int

addresses = {
    # 010000xx
    "serverSetupFileName":            b"\x01\x00\x00\x00",
    # 010001xx
    "songToneLanguage":               b"\x01\x00\x01\x00",
    "keyTransposeRO":                 b"\x01\x00\x01\x01",
    "songTransposeRO":                b"\x01\x00\x01\x02",
    "sequencerStatus":                b"\x01\x00\x01\x03",
    "sequencerMeasure":               b"\x01\x00\x01\x05",
    "sequencerTempoNotation":         b"\x01\x00\x01\x07",
    "sequencerTempoRO":               b"\x01\x00\x01\x08",
    "sequencerBeatNumerator":         b"\x01\x00\x01\x0A",
    "sequencerBeatDenominator":       b"\x01\x00\x01\x0B",
    "sequencerPartSwAccomp":          b"\x01\x00\x01\x0C",
    "sequencerPartSwLeft":            b"\x01\x00\x01\x0D",
    "sequencerPartSwRight":           b"\x01\x00\x01\x0E",
    "metronomeStatus":                b"\x01\x00\x01\x0F",
    "headphonesConnection":           b"\x01\x00\x01\x10",
    # 010002xx
    "keyBoardMode":                   b"\x01\x00\x02\x00",
    "splitPoint":                     b"\x01\x00\x02\x01",
    "splitOctaveShift":               b"\x01\x00\x02\x02",
    "splitBalance":                   b"\x01\x00\x02\x03",
    "dualOctaveShift":                b"\x01\x00\x02\x04",
    "dualBalance":                    b"\x01\x00\x02\x05",
    "twinPianoMode":                  b"\x01\x00\x02\x06",
    "toneForSingle":                  b"\x01\x00\x02\x07",
    "toneForSplit":                   b"\x01\x00\x02\x0A",
    "toneForDual":                    b"\x01\x00\x02\x0D",
    "songNumber":                     b"\x01\x00\x02\x10",
    "masterVolume":                   b"\x01\x00\x02\x13",
    "masterVolumeLimit":              b"\x01\x00\x02\x14",
    "allSongPlayMode":                b"\x01\x00\x02\x15",
    "splitRightOctaveShift":          b"\x01\x00\x02\x16",
    "dualTone1OctaveShift":           b"\x01\x00\x02\x17",
    "masterTuning":                   b"\x01\x00\x02\x18",
    "ambience":                       b"\x01\x00\x02\x1A",
    "headphones3DAmbience":           b"\x01\x00\x02\x1B",
    "brilliance":                     b"\x01\x00\x02\x1C",
    "keyTouch":                       b"\x01\x00\x02\x1D",
    "transposeMode":                  b"\x01\x00\x02\x1E",
    "metronomeBeat":                  b"\x01\x00\x02\x1F",
    "metronomePattern":               b"\x01\x00\x02\x20",
    "metronomeVolume":                b"\x01\x00\x02\x21",
    "metronomeTone":                  b"\x01\x00\x02\x22",
    "metronomeDownBeat":              b"\x01\x00\x02\x23",
    # 010003xx
    "applicationMode":                b"\x01\x00\x03\x00",
    "scorePageTurn":                  b"\x01\x00\x03\x02",
    "arrangerPedalFunction":          b"\x01\x00\x03\x03",
    "arrangerBalance":                b"\x01\x00\x03\x05",
    "connection":                     b"\x01\x00\x03\x06",
    "keyTransposeWO":                 b"\x01\x00\x03\x07",
    "songTransposeWO":                b"\x01\x00\x03\x08",
    "sequencerTempoWO":               b"\x01\x00\x03\x09",
    "tempoReset":                     b"\x01\x00\x03\x0B",
    # 010004xx
    "soundEffect":                    b"\x01\x00\x04\x00",
    "soundEffectStopAll":             b"\x01\x00\x04\x02",
    # 010005xx
    "sequencerREW":                   b"\x01\x00\x05\x00",
    "sequencerFF":                    b"\x01\x00\x05\x01",
    "sequencerReset":                 b"\x01\x00\x05\x02",
    "sequencerTempoDown":             b"\x01\x00\x05\x03",
    "sequencerTempoUp":               b"\x01\x00\x05\x04",
    "sequencerPlayStopToggle":        b"\x01\x00\x05\x05",
    "sequencerAccompPartSwToggle":    b"\x01\x00\x05\x06",
    "sequencerLeftPartSwToggle":      b"\x01\x00\x05\x07",
    "sequencerRightPartSwToggle":     b"\x01\x00\x05\x08",
    "metronomeSwToggle":              b"\x01\x00\x05\x09",
    "sequencerPreviousSong":          b"\x01\x00\x05\x0A",
    "sequencerNextSong":              b"\x01\x00\x05\x0B",
    # 010006xx
    "pageTurnPreviousPage":           b"\x01\x00\x06\x00",
    "pageTurnNextPage":               b"\x01\x00\x06\x01",
    # 010007xx
    "uptime":                         b"\x01\x00\x07\x00",
    # 010008xx
    "addressMapVersion":              b"\x01\x00\x08\x00"}

def get_address_name(address):
    return list(addresses.keys())[list(addresses.values()).index(address)]

def get_address_size(addressName):
    addressSizeMap = {  # consider implementing this to read all registers
        "sequencerMeasure" : 2,
        "sequencerTempoRO" : 2,
        "masterTuning"     : 2,
        "toneForSingle"    : 3
    }

    if addressName in addressSizeMap:
        return addressSizeMap[addressName]
    else:
        return 1


class Message():
    key_status           = {}
    sustained_key_status = {}
    sustain              = 0
    header_byte          = b""

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
        return len(self.buf) >= (2+8+1+1)

    def isNewMsg(self, data):
        headerChanged = data[0:1] != self.header_byte
        isMidiMsg = len(data) == 5 and (data[2:3] in self.getAudioStatusCodes())
        return headerChanged or isMidiMsg

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
            if self.isAudioMsg():

                # len is 5 + (n*4)
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
                    print("more than 2 midi msgs")
                return 1 # done
        else: #if the timestampbyte (first byte) is the same, we treat as the same packet?
            print("not audio msg")
            self.buf += data[1:] # append message
    
        if self.isSysExMsg() and self.sysExMsgEnded() and self.validSysExMsgLength():
            print("sysex")
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

    #My version of append()
    def appendNew(self,data):
        if self.isNewMsg(data):
            print("new msg")
        else:
            print("same timestamp as prev + more than 1 midimsg")
        # new message, discard old message
        self.reset()
        try:
            self.header_byte    = data[0:1]
            self.timestamp_byte = data[1:2]
            self.status_byte    = data[2:3]
            self.buf            = data[3:]
        except Exception:
            return -1 # done, with errors
        if self.isAudioMsg():
            # len is 5 + (n*4)
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
                print("more than 2 midi msgs")
            return 1 # done
    
        if self.isSysExMsg() and self.sysExMsgEnded() and self.validSysExMsgLength():
            print("sysex")
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
        correct_size = get_address_size(get_address_name(self.address)) == len(self.data)
        return self.man_id == lut['id_roland'] and self.cmd and self.address and self.checksum == cmp_checksum and correct_size


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
                    key_recorder.debug(f"{self.status_bytes[idx].hex()} - note: {self.notes[idx].hex()}, velocity: {self.velocities[idx].hex()}")

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
                log.debug(f"address: {self.address.hex()}, data: {self.data.hex()}, cmd: {self.cmd.hex()}")
                fields[get_address_name(self.address)] = (self.data,True)
                return 0
        return -1


midi_data = bytearray()
class MyDelegate(btle.DefaultDelegate):
    message = Message()
    def __init__(self, params = None):
        btle.DefaultDelegate.__init__(self)
        

    def handleNotification(self, cHandle, data):
        status = self.message.appendNew(data)
        # prefix; the length in bytes for the following midi message
        midi_data.extend(len(data).to_bytes(1, byteorder="little")) 
        midi_data.extend(data)
        print(f"data : {data}")
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


    def instrument(self) -> Instruments:
        return self.read_register("toneForSingle")

    def instrument(self, instrument: Instruments):
        value = (instrument.value[0] << 16) | instrument.value[1]
        # print("value is")
        # print(value)
        logging.info(f"value is {value}")
        logging.info(f"in bytes : {data_as_bytes(value)}")
        # self.write_register('toneForSingle', data_as_bytes(value))
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

        addr      = addresses[addressName]
        ut        = self.get_unix_time()
        header    = self.get_header(ut)
        timestamp = self.get_timestamp(ut)      

        if data == None: # Read register
            data      = b"\x00\x00\x00" + int_to_byte(get_address_size(addressName))
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
            msg_pt2 = header + timestamp + lut['sysex_msg_end']
            self.writeCharacteristic(16,msg_base,withResponse=False)
            self.writeCharacteristic(16,msg_pt2,withResponse=False)
        else:
            msg = msg_base + timestamp + lut['sysex_msg_end']
            self.writeCharacteristic(16,msg)

        self.waitForNotifications(2.0)


    def read_register(self,addressName):
        self.access_register(addressName)

    def write_register(self,addressName,data):
        self.access_register(addressName,data)


    def read_field(self,field):
        if field in fields:
            (data,isNew) = fields[field]
            if isNew:
                fields[field] = (data,False)
            return (data, isNew)
        else:
            return ("", False)

    def print_fields(self,fields, onlyUpdates = False):
        for field in fields:
            (data,isNew) = self.read_field(field)
            if onlyUpdates and not isNew:
                continue
            else:
                parser = get_parser(field)
                log.info(f"{field}: {parser(data)}")

    def update_fields(self,fields):
        for field in fields:
            self.read_register(field)

    def get_header(self,unix_time):
        mask_header    = b'\x7f'
        return ((mask_header[0]    & unix_time[0]) | b'\x80'[0]).to_bytes(1,byteorder='little') #0b10000000
    
    def get_timestamp(self,unix_time):
        mask_timestamp = b'\x3f'
        return ((mask_timestamp[0] & unix_time[0]) | b'\x80'[0]).to_bytes(1,byteorder='little') #0b10000000

    def get_unix_time(self):
        return int(bin(int(time.time()))[-8:],2).to_bytes(1,byteorder='little')

    def play_note(self,note, force):
        note  = note_string_to_midi(note)
        print(f"note : {note.hex()}")
        force = int_to_byte(force)

        ut = self.get_unix_time()

        msg = self.get_header(ut) + self.get_timestamp(ut) + lut['note_on'] + note + force
        self.writeCharacteristic(16,msg) # 16 is the handler of the midi characteristic

    # Play note for a time duration
    def play_note_duration(self, note, force, duration):
        note  = note_string_to_midi(note)
        print(f"note : {note.hex()}")
        force = int_to_byte(force)
        ut = self.get_unix_time()
        utLater = int(bin(int(time.time())+duration)[-8:],2).to_bytes(1,byteorder='little')
        noteOnMsg = self.get_header(ut) + self.get_timestamp(ut) + lut['note_on'] + note + force
        noteOffMsg = self.get_header(utLater) + self.get_timestamp(utLater) + lut['note_off'] + note + force
        self.writeCharacteristic(16,noteOnMsg) # 16 is the handler of the midi characteristic
        self.writeCharacteristic(16,noteOffMsg)
    

    def create_ble_midi_header(self, time_ms):
        header = 0x80 | ((time_ms >> 7) & 0x3F)  # MSB of the timestamp goes into header
        timestamp = 0x80 | ((time_ms) & 0x7F)  # Remaining 7 bits for timestamp
        return header, timestamp
    
    #header byte : 0x80 (128) to 0xBF(191)
    #timestamp byte : 0x80 (128) to 0xFF (255)
    def increment_timestamp(self, b, increment):
         # Convert bytearray to a list of integers
        int_list = list(b)
        
        # Start from the last byte and increment
        for i in range(len(int_list) - 1, -1, -1):
            if int_list[i] < 255:
                int_list[i] += 1
                break
            else:
                int_list[i] = 0
                if i == 0:
                    int_list.insert(0, 1)
        
        return int_list

    def play_mid(self, mid):
        ut = 0
        input_time_ms = ut
        for count, msg in enumerate(mid.play()):
            input_time_ms = int((input_time_ms + msg.time * 1000) % 8192)          
            midi_msg = msg.bin()
            if (msg.type == 'program_change'):
                midi_msg[1] = 1
            header, timestamp = self.create_ble_midi_header(input_time_ms)
            self.writeCharacteristic(16, header.to_bytes(1,byteorder='little') 
                                     + timestamp.to_bytes(1,byteorder='little') + midi_msg )
            print(header.to_bytes(1,byteorder='little') 
                  + timestamp.to_bytes(1,byteorder='little') + midi_msg)
            print(str(msg))

        # ut = self.get_ut()
        # ut = 0
        # bytelength = 0
        # # start_time = ut
        # input_time_ms = ut
        # prev_msg = None
        # waitForResp = True
        # total_time_ms = 0
        # for msg in mid:
        #     total_time_ms = int((total_time_ms + msg.time * 1000))
        #     if prev_msg is not None and msg.time == 0: # if delta time is 0, we merge midi messages            
        #         first_midi_msg = prev_msg.bin()
        #         input_time_ms = int((input_time_ms + prev_msg.time * 1000) % 8192) 
        #         header, timestamp = self.create_ble_midi_header(input_time_ms)
        #         if isinstance(prev_msg, mido.MetaMessage):
        #             prev_msg = msg
        #             continue
        #         if isinstance(msg, mido.MetaMessage):
        #             ble_midi_msg = (header.to_bytes(1,byteorder='little') + 
        #                         timestamp.to_bytes(1,byteorder='little') + midi_msg)
        #             if bytelength > 8500 and waitForResp:
        #                 print(f"sleeping {int(total_time_ms)/1000} seconds...")
        #                 time.sleep(int(total_time_ms)/1000)
        #                 self.writeCharacteristic(16, ble_midi_msg, withResponse=False)
        #                 waitForResp = False
        #             else:
        #                 self.writeCharacteristic(16, ble_midi_msg, withResponse=False)
        #             print(time.asctime()+ ble_midi_msg.hex())
        #             prev_msg = msg
        #             bytelength = bytelength + len(ble_midi_msg)
        #             print(f"bytelength : {bytelength}")
        #             # time.sleep(0.01)
        #             continue
        #         second_midi_msg = msg.bin()
        #         ble_midi_msg = (header.to_bytes(1,byteorder='little') + 
        #                         timestamp.to_bytes(1,byteorder='little') + first_midi_msg + 
        #                         timestamp.to_bytes(1, byteorder='little') + second_midi_msg)
        #         prev_msg = None
        #     elif prev_msg is None: # first element or when prev is meta message or was merged
        #         prev_msg = msg
        #         continue 
        #     else: # next msg's delta time is not 0, so we just send prev_msg as 1 midi message.
        #         midi_msg = prev_msg.bin()
        #         input_time_ms = int((input_time_ms + prev_msg.time * 1000) % 8192) 
        #         header, timestamp = self.create_ble_midi_header(input_time_ms)
        #         if isinstance(prev_msg, mido.MetaMessage):
        #             prev_msg = msg
        #             continue
        #         ble_midi_msg = (header.to_bytes(1,byteorder='little') + 
        #                         timestamp.to_bytes(1,byteorder='little') + midi_msg)
        #         prev_msg = msg
        #     if bytelength > 8500 and waitForResp:
        #         print(f"sleeping {int(total_time_ms)/1000} seconds...")
        #         time.sleep(int(total_time_ms)/1000)
        #         self.writeCharacteristic(16, ble_midi_msg, withResponse=False)
        #         waitForResp = False
        #     else:
        #         self.writeCharacteristic(16, ble_midi_msg, withResponse=False)
        #     bytelength = bytelength + len(ble_midi_msg)
            
        #     print(time.asctime()+ ble_midi_msg.hex())
        #     print(f"bytelength : {bytelength}")
        
            #here
            # time.sleep(0.01)
            # time.sleep(0.005)

            # if isinstance(msg, mido.MetaMessage):
            #     continue
            # if msg.is_cc(64):
            #     print("pedal skipping")
            #     continue
            # self.writeCharacteristic(16, header.to_bytes(1,byteorder='little') 
            #                          + timestamp.to_bytes(1,byteorder='little') + midi_msg, withResponse=False)
            # print((header.to_bytes(1,byteorder='little') 
            #       + timestamp.to_bytes(1,byteorder='little') + midi_msg).hex())
            # prev_msg = msg
            
        

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

