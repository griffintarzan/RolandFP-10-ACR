#!/usr/bin/python3
from bluepy import btle
import time
import pandas as pd
import logging

class Message():
    header_byte   = b""

    buf = b""

    lut = {
        "note_on"         : b'\x80',
        "note_off"        : b'\x90',
        "control_change"  : b'\xb0',
        "sysex_msg_start" : b'\xf0',
        "sysex_msg_end"   : b'\xf7',
        "roland_id"       : b'\x41\x10\x00\x00\x00\x28'
    }



    def __str__(self):
        buffer = ""
        buffer += f"buf: {self.buf.hex()}\n"
        buffer += f"header_byte: {self.header_byte}, timestamp_byte: {self.timestamp_byte}\n"
        buffer += f"status_byte: {self.status_byte}\n"

        for idx,_ in enumerate(self.notes):
            buffer += f"note: {self.notes[idx]}, velocity: {self.velocities[idx]}\n"

        return buffer
        

    def __init__(self):
        pass

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
        return [self.lut['note_on'], self.lut['note_off'], self.lut['control_change']]

    def isAudioMsg(self):
        return self.status_byte in self.getAudioStatusCodes()

    def isValidAudioMsg(self):
        return self.status_byte and self.notes and self.velocities
    
    def isSysExMsg(self):
        return self.status_byte == self.lut['sysex_msg_start']

    def timeStampChanged(self,data):
        return self.timestamp_byte != data[2:3]

    def sysExMsgEnded(self):
        return (self.lut['sysex_msg_end'] in self.buf)

    def validSysExMsgLength(self):
        # cmd (2) + address (8) + data (>=1) + checksum (1)
        return len(self.buf) >= (2+8+1+1)

    def isNewMsg(self, data):
        headerChanged = data[0:1] != self.header_byte
        isMidiMsg = len(data) == 5 and (data[2:3] in self.getAudioStatusCodes())
        return headerChanged or isMidiMsg

    def append(self,data):
        # print("GGGGGG")
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
            # print("FFFF")
            if self.isAudioMsg():

                # len is 5 + (n*4)
                # n is not larger than 2, so basically a message can hold 3 midi audio updates. 
                #TODO: write more elegantly

                if len(self.buf) == 2: # Contains one midi msg
                    try:
                        self.status_bytes = [self.status_byte]
                        self.notes     = [self.buf[0:1]]
                        self.velocities = [self.buf[1:2]]
                    except Exception:
                        return -1  # done, with errors
                elif len(self.buf) == 6: # Contains two midi msgs ('compressed')
                    try:
                        self.status_bytes = [self.status_byte, self.buf[3:4]]
                        self.notes     = [self.buf[0:1],self.buf[4:4+1]]
                        self.velocities = [self.buf[1:2],self.buf[5:5+1]]
                    except Exception:
                        return -1  # done, with errors
                return 1 # done
        else: 
            self.buf += data[1:] # append message
    
        if self.isSysExMsg() and self.sysExMsgEnded() and self.validSysExMsgLength():
            self.buf      = self.buf.split(b'\xf7')[0] # cut the message at the end
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
        return self.man_id == self.lut['roland_id'] and self.cmd and self.address and self.checksum == cmp_checksum and self.data


    def decode(self):
        if self.isAudioMsg():
            if self.isValidAudioMsg():
                for idx,_ in enumerate(self.notes):
                    log.debug(f"{self.status_bytes[idx].hex()} - note: {self.notes[idx].hex()}, velocity: {self.velocities[idx].hex()}")
                return 0

        elif self.isSysExMsg():
            if self.isValidRolandMsg():
                log.debug(f"address: {self.address.hex()}, data: {self.data.hex()}, cmd: {self.cmd.hex()}")
                return 0
        return -1


class MyDelegate(btle.DefaultDelegate):
    message = Message()
    def __init__(self, params = None):
        btle.DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        status = self.message.append(data)
        if status == 1:
            self.message.decode()
        elif status == -1:
            log.error("Not a valid message")
            log.error(self.message)

addressSizeMap = {  # consider implementing this to read all registers
    "sequencerMeasure" : 2,
    "sequencerTempoWO" : 2,
    "masterTuning"     : 2
}

def getAddressSize(addressName):
    if addressName in addressSizeMap:
        return addressSizeMap[addressName]
    else:
        return 1


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
    return int_to_byte(answer)






class RolandPiano(btle.Peripheral):
    service_uuid        = "03b80e5a-ede8-4b33-a751-6ce34ec4c700"
    characteristic_uuid = "7772e5db-3868-4112-a1a9-f2669d106bf3"
    setup_data = b"\x01\x00"

    # http://www.chromakinetics.com/handsonic/rolSysEx.htm
    lut_midi = {
        'msg_start' : b'\xf0',
        'msg_end'   : b'\xf7',
        'id_roland' : b'\x41',
        'id_device' : b'\x10',
        'id_fp10'   : b'\x28', # This seems to be not bound to fp-10 actually
        'cmd_write' : b'\x12',
        'cmd_read'  : b'\x11',
    }

    lookup_status = {
        'note_on_ch0' : b'\x90'}
        

    def build_handle_table(self):
        cols = ['handle','uuid_bytes','uuid_str']
        rows = []
        for desc in self.getDescriptors():
            rows.append(pd.DataFrame([{'handle' : desc.handle, 'uuid_bytes' : desc.uuid, 'uuid_str' : str(desc.uuid)}],columns = cols))

        self.handle_table = pd.concat(rows)

    def get_checksum(self,addr,data):
        total = 0
        for b in addr:
            total += b
        for b in data:
            total += b        
        return int_to_byte(128 - (total % 128))        

    def read_register(self,addressName):
        addr = addresses[addressName]
        data = b"\x00\x00\x00" + int_to_byte(getAddressSize(addressName))
        ut        = self.get_unix_time()
        header    = self.get_header(ut)
        timestamp = self.get_timestamp(ut)

        checksum = self.get_checksum(addr,data)

        # TODO: lut best way to do this, seems overly configurable
        msg = header + timestamp + self.lut_midi['msg_start'] + \
            self.lut_midi['id_roland'] + \
            self.lut_midi['id_device'] + \
            b"\x00\x00\x00" + \
            self.lut_midi['id_fp10'] + \
            self.lut_midi['cmd_read'] + \
            addr + \
            data + \
            checksum  
        msg2 = header + timestamp + self.lut_midi['msg_end']


        self.writeCharacteristic(16,msg,withResponse=False)
        self.writeCharacteristic(16,msg2,withResponse=False)
        self.waitForNotifications(2.0)
        pass

    def write_register(self,addressName,data):
        addr = addresses[addressName]
        ut        = self.get_unix_time()
        header    = self.get_header(ut)
        timestamp = self.get_timestamp(ut)

        checksum = self.get_checksum(addr,data)

        msg = header + timestamp + self.lut_midi['msg_start'] + \
            self.lut_midi['id_roland'] + \
            self.lut_midi['id_device'] + \
            b"\x00\x00\x00" + \
            self.lut_midi['id_fp10'] + \
            self.lut_midi['cmd_write'] + \
            addr + \
            data + \
            checksum + \
            timestamp + \
            self.lut_midi['msg_end']

        self.writeCharacteristic(16,msg)
        self.waitForNotifications(2.0)
        pass

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
        force = int_to_byte(force)

        ut = self.get_unix_time()

        msg = self.get_header(ut) + self.get_timestamp(ut) + self.lookup_status['note_on_ch0'] + note + force
        self.writeCharacteristic(16,msg) # 16 is the handler of the midi characteristic

    def get_handle(self,uuid):
        return self.handle_table.loc[self.handle_table['uuid_str'].str.contains(uuid)].at[0,'handle']

    def get_uuid(self,handle):
        return self.handle_table.loc[self.handle_table['handle'] == handle].at[0,'uuid_bytes']

    def read_all_characteristics(self):
        for _,row in self.handle_table.iterrows():
            self.readCharacteristic(row['handle'])

    isInitialized = False
    def connect(self, mac_addr, max_attempts):
        for attempt_num in range(1,max_attempts+1):
            try:
                log.info(f"Attempt {attempt_num} to connect to {mac_addr}")
                if not self.isInitialized:
                    btle.Peripheral.__init__(self, mac_addr,"random")
                    self.isInitialized = True
                else:
                    btle.Peripheral.connect(self,mac_addr,"random")
                break
            except Exception:
                if attempt_num < max_attempts:
                    continue
                else:
                    log.error(f"Was not able to connect to {mac_addr} after {max_attempts} attempts..")
                    return False
        log.info(f"Connection with {mac_addr} established")
        return True
                    


    def __init__(self,mac_addr):
        self.connect(mac_addr,3)

        self.midi_ble_service = self.getServiceByUUID(self.service_uuid)
        self.midi_ble_characteristic = self.midi_ble_service.getCharacteristics(self.characteristic_uuid)[0]

        self.build_handle_table()

        self.read_all_characteristics()

        self.setDelegate(MyDelegate())
        
        self.writeCharacteristic(self.get_handle('2902'),self.setup_data,withResponse=False)
        if not self.readCharacteristic(self.get_handle('2902')) == self.setup_data:
            log.error("Notification not correctly set in descriptor")
        self.write_register('connection',b"\x01")

def int_to_metronome(i):
    return b"\x00" + int_to_byte(i)


def setup_logging():
    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    #console handler
    ch = logging.StreamHandler()
    # ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    log.addHandler(ch)

    #file handler
    fh = logging.FileHandler('main.log')
    # fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    log.addHandler(fh)

    return log



def main():
    mac_addr_roland_fp_10        = "c3:14:a9:3e:8f:77"  
    fp10 = RolandPiano(mac_addr_roland_fp_10)

    while True:
        try: 

            while True:
                fp10.read_register('sequencerTempoWO')
                fp10.read_register('masterVolume')
                fp10.waitForNotifications(1.0)

        except btle.BTLEDisconnectError:
            log.error("Disconnected from device, attemping to reconnect")
            if fp10.connect(mac_addr_roland_fp_10, 3):
                continue
            else:
                log.critical("Could not reconnect, exitting")
                break

    fp10.disconnect()


if __name__ == "__main__":
    log = setup_logging()
    main()


     

    


    

