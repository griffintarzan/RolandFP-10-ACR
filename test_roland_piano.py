import logging
import yaml
import time
import RolandPiano as rp
import mido
from pathlib import Path
import RPi.GPIO as GPIO
from RPLCD.gpio import CharLCD

BUTTON_PIN_1 = 3


lcd = CharLCD(pin_rs = 40, pin_rw = None, pin_e = 38, pins_data = [35,33,31,29], 
              numbering_mode = GPIO.BOARD, cols=16, rows=2, dotsize=8)
number = 0
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

current_instrument_index = 0
instrumentList = [instrument.name for instrument in rp.Instruments]

def setup_buttons():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(BUTTON_PIN_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def initialize_midi_playlist(directory='/home/pi/Documents/Dev/RolandPianoControl/midiFiles'):
    midi_playlist = []
    midi_files = Path(directory).glob('*.mid')
    for file in midi_files:     
        midi_playlist.append((mido.MidiFile(file.resolve()), file.name))
    return midi_playlist
midi_playlist = initialize_midi_playlist()
# Define the callback function for button press event
def button_callback(channel, piano):
    if channel == BUTTON_PIN_1:
        handle_button_1(piano)

def handle_button_1(piano):
    for mid, song_name in midi_playlist:
        lcd.clear()
        song_name = song_name.replace("_", " ")
        lcd.write_string("Playing"+ " \x00 " + song_name[:22])
        piano.play_mid(mid)
        lcd.clear()
        time.sleep(3)

# Main loop to keep the program running
def main(): 
    piano = None
    try:
        setup_buttons()
        piano = rp.RolandPiano("C4:68:F8:B2:78:56")
        # piano.instrument(rp.Instruments.JAZZ_SCAT_2)
        GPIO.add_event_detect(BUTTON_PIN_1, GPIO.RISING, callback=lambda channel: button_callback(channel, piano), bouncetime=300)
        
        while True:
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
                
            piano.save_to_file("recording.txt")
            time.sleep(1)
            piano.parse_midi("recording.txt")
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
