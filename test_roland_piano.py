import logging
import yaml
import time
import RolandPiano as rp
import mido
from pathlib import Path
import RPi.GPIO as GPIO
from RPLCD.gpio import CharLCD
import random

import config as cfg

BUTTON_PIN_1 = 3
BUTTON_PIN_2 = 5
BUTTON_PIN_3 = 7
BUTTON_PIN_4 = 11
BUTTON_PIN_5 = 13


class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
        self.prev = None

# current_instrument_index = 0
instrumentList = [instrument for instrument in rp.Instruments]
modeList = ["instrument", "recorder", "midiFile", "midiPlayAll"]
def create_linked_list(list):
    head = Node(list[0])
    current = head
    for data in list[1:]:
        new_node = Node(data)
        current.next = new_node
        new_node.prev = current
        current = new_node
    # Make the list circular
    current.next = head
    head.prev = current
    return head
instrument_head = create_linked_list(instrumentList)
mode_head = create_linked_list(modeList)
current_mode_node = mode_head
piano_instrument_node = instrument_head
current_instrument_node = instrument_head

def initialize_lcd_display():
    lcd = CharLCD(pin_rs = 40, pin_rw = None, pin_e = 38, pins_data = [35,33,31,29], 
              numbering_mode = GPIO.BOARD, cols=16, rows=2, dotsize=8)
    music = (
        0b00011,
        0b00010,
        0b00010,
        0b00010,
        0b00010,
        0b01110,
        0b11110,
        0b01110
    )
    lcd.create_char(0, music)
    return lcd

def display_message(lcd, message):
    lcd.clear()
    lcd.write_string(message)

def setup_buttons():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(BUTTON_PIN_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTON_PIN_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTON_PIN_3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTON_PIN_4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTON_PIN_5, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def initialize_midi_playlist(directory='/home/pi/Documents/Dev/RolandPianoControl/midiFiles'):
    midi_playlist = []
    midi_files = Path(directory).glob('*.mid')
    for file in midi_files:     
        midi_playlist.append((mido.MidiFile(file.resolve()), file.name))
    return midi_playlist

midi_playlist = initialize_midi_playlist()
midiFile_head = create_linked_list(midi_playlist)
current_midiFile_node = midiFile_head

# Define the callback function for button press event
def button_callback(channel, piano, lcd):
    if channel == BUTTON_PIN_1:
        handle_button_1(piano, lcd)
    elif channel == BUTTON_PIN_2:
        handle_button_2(piano, lcd)
    elif channel == BUTTON_PIN_3:
        handle_button_3(piano, lcd)
    elif channel == BUTTON_PIN_4:
        handle_button_4(piano, lcd)
    elif channel == BUTTON_PIN_5:
        handle_button_5(piano, lcd)

#Escape
def handle_button_1(piano, lcd):
    cfg.escape_pressed = True
    time.sleep(1)
    global current_instrument_node
    global current_mode_node
    if current_mode_node.data == "instrument":
        instrument_string = str(piano.get_instrument())
        #string : Instruments.XXXX
        # print(instrument_string)
        instrument_string = instrument_string[12:]
        # print(instrument_string)
        #recover instrument_node 
        current_instrument_node = piano_instrument_node
        print("Instrument:"+instrument_string)
        display_message(lcd, "Instrument:"+instrument_string)
    elif current_mode_node.data == "recorder":
        print("Recorder: Not implmented")
        display_message(lcd, "Recorder:")
    elif current_mode_node.data== "midiFile":
        display_message(lcd, "Midi Player:")
        time.sleep(1)
        song_name = current_midiFile_node.data[1].replace("_", " ")
        print("MIDFile"+ " \x00 " + song_name[:22])
        display_message(lcd, "MIDFile"+ " \x00 " + song_name[:22])
    elif current_mode_node.data == "midiPlayAll":
        display_message(lcd, "Midi Play ALL")
    cfg.escape_pressed = False

# Change Mode (Instrument / Recorder / MIDI Play)
def handle_button_2(piano, lcd):
    global current_instrument_node
    global current_mode_node
    current_mode_node = current_mode_node.next
    if current_mode_node.data == "instrument":
        instrument_string = str(piano.get_instrument())
        #string : Instruments.XXXX
        # print(instrument_string)
        instrument_string = instrument_string[12:]
        # print(instrument_string)
        #recover instrument_node 
        current_instrument_node = piano_instrument_node
        print("Instrument:"+instrument_string)
        display_message(lcd, "Instrument:"+instrument_string)
    elif current_mode_node.data == "recorder":
        print("Recorder: Not implemented")
        display_message(lcd, "Recorder:")
    elif current_mode_node.data== "midiFile":
        display_message(lcd, "Midi Player:")
        time.sleep(1)
        song_name = current_midiFile_node.data[1].replace("_", " ")
        print("MIDFile"+ " \x00 " + song_name[:22])
        display_message(lcd, "MIDFile"+ " \x00 " + song_name[:22])
    elif current_mode_node.data == "midiPlayAll":
        display_message(lcd, "Midi Play ALL")
    

# go next
def handle_button_3(piano, lcd):
    global current_instrument_node
    global current_midiFile_node
    if current_mode_node.data == "instrument":
        current_instrument_node = current_instrument_node.next
        display_message(lcd, current_instrument_node.data.name)
    elif current_mode_node.data == "recorder":
        pass
    elif current_mode_node.data == "midiFile":
        current_midiFile_node = current_midiFile_node.next
        song_name = current_midiFile_node.data[1].replace("_", " ")
        display_message(lcd, "MIDFile"+ " \x00 " + song_name[:22])
    

# go previous
def handle_button_4(piano, lcd):
    global current_instrument_node
    global current_midiFile_node
    if current_mode_node.data == "instrument":
        current_instrument_node = current_instrument_node.prev
        display_message(lcd, current_instrument_node.data.name)
    elif current_mode_node.data == "recorder":
        pass
    elif current_mode_node.data == "midiFile":
        current_midiFile_node = current_midiFile_node.prev
        song_name = current_midiFile_node.data[1].replace("_", " ")
        display_message(lcd, "MIDFile"+ " \x00 " + song_name[:22])
    

# Select
def handle_button_5(piano, lcd):
    global current_instrument_node
    global piano_instrument_node
    if current_mode_node.data == "instrument":
        piano.set_instrument(current_instrument_node.data)
        piano_instrument_node = current_instrument_node
    elif current_mode_node.data == "recorder":
        pass
    elif current_mode_node.data == "midiFile":
        mid, song_name = current_midiFile_node.data
        song_name = song_name.replace("_", " ")
        display_message(lcd, "Playing"+ " \x00 " + song_name[:22])
        piano.play_mid(mid)
    elif current_mode_node.data == "midiPlayAll":
        display_message(lcd, "Midi Play ALL")
        shuffled_playlist = sorted(midi_playlist, key=lambda x: random.random())
        for mid, song_name in shuffled_playlist:
            song_name = song_name.replace("_", " ")
            display_message(lcd, "Playing"+ " \x00 " + song_name[:22])
            piano.play_mid(mid)
            time.sleep(5)
        piano.disconnect()
        lcd.close(clear=True)
        GPIO.cleanup()
        exit()
        

        
# Main loop to keep the program running
#TODO: First connection should find instrument for sure.. or else it won't locate bank_msb lsb
# and break the play_mid
def main():
    piano = None
    try:
        #TODO: Connecting... msg, initial display with instrument, recording feature,ESC button
        setup_buttons()
        lcd = initialize_lcd_display()
        display_message(lcd, "Connecting...")
        piano = rp.RolandPiano("C4:68:F8:B2:78:56")
        # piano.idle()
        
        # piano.instrument(rp.Instruments.E_PIANO)
        
        # piano.instrument(rp.Instruments.JAZZ_SCAT_2)
        GPIO.add_event_detect(BUTTON_PIN_1, GPIO.FALLING, callback=lambda channel: button_callback(channel, piano, lcd), bouncetime=300)
        GPIO.add_event_detect(BUTTON_PIN_2, GPIO.FALLING, callback=lambda channel: button_callback(channel, piano, lcd), bouncetime=300)
        GPIO.add_event_detect(BUTTON_PIN_3, GPIO.FALLING, callback=lambda channel: button_callback(channel, piano, lcd), bouncetime=300)
        GPIO.add_event_detect(BUTTON_PIN_4, GPIO.FALLING, callback=lambda channel: button_callback(channel, piano, lcd), bouncetime=300)
        GPIO.add_event_detect(BUTTON_PIN_5, GPIO.FALLING, callback=lambda channel: button_callback(channel, piano, lcd), bouncetime=300)
        display_message(lcd, "Connected!")
        time.sleep(1)
        global current_instrument_node
        instrument_string = str(piano.get_instrument())
        instrument_string = instrument_string[12:]
        current_instrument_node = piano_instrument_node
        display_message(lcd, "Instrument:"+instrument_string)

        while True:
            
            # piano.idle()
            # if GPIO.event_detected(BUTTON_PIN_1):
            #     print("Event detected!!!")
            #     cfg.escape_pressed = True
            
            time.sleep(1)
            # print("hi")
            # piano.idle()
            
            # piano.play_note("C-3", 50) #This is C2
            # time.sleep(1)
        field_timer = 0
        fields = ['toneForSingle'] # 'masterVolume','sequencerTempoRO',
        # piano.write_register("metronomeSwToggle", b'\x00')
        # Set up GPIO mode and pin
        # GPIO.setmode(GPIO.BOARD)

        # Add event detection for rising edge on button1
        # GPIO.add_event_detect(button1, GPIO.RISING, callback=lambda channel: button_callback(channel, piano), bouncetime=50)
        
        # while True:
            # pass

        # log.info(f"Setting instrument to {rp.Instruments.CHOIR_2}")
        # piano.instrument(rp.Instruments.JAZZ_SCAT_2)
        # status = piano.read_register("toneForSingle")
        # log.info(f"instrument status : {status}")
        # for instrument in rp.Instruments:
        #     logging.info(f"Setting instrument to {instrument}")
        #     piano.instrument(instrument)
        #     time.sleep(3)
            # piano.play_note("D-6",50)
            # time.sleep(0.8)
            # piano.play_note("D-5",50)
            # time.sleep(0.2)
            # piano.play_note("A-5",50)
            # time.sleep(0.4)
            # piano.play_note("G-5",50)
            # time.sleep(0.4)
            # piano.play_note("D-5",50)
            # time.sleep(0.4)
            # piano.play_note("D-6",50)
            # time.sleep(0.4)
            # piano.play_note("A-6",50)
            # time.sleep(3)
                
        # while True:
        #     break
        #     # Update state of the key_status
        #     piano.write_register("metronomeSwToggle", b'\x00')
        #     for k,v in piano.delegate.message.sustained_key_status.items():
        #         if v > 0 : piano.delegate.message.sustained_key_status[k] -= 1


        #     piano.idle()

        #     piano.print_fields(fields, onlyUpdates=True)

        #     if field_timer == 5:
        #         field_timer = 0
        #         piano.update_fields(fields)
        #         break
        #     else:
        #         field_timer += 1

            
    except KeyboardInterrupt:
        log.info("Exit cmd given by user, disconnecting..")
        if piano:    
            # piano.save_to_file("recording.txt")
            # time.sleep(1)
            # piano.parse_midi("recording.txt")
            # time.sleep(60)
            piano.disconnect()
       
    finally:
        lcd.close(clear=True)
        GPIO.cleanup()

if __name__ == "__main__":
    import logging.config
    with open('logging.yaml') as f:
        config = yaml.safe_load(f)
        logging.config.dictConfig(config)
    log = logging.getLogger(__name__)
    main()
