import logging
import yaml
import time
import RolandPiano as rp
import mido

# from time import sleep, time
import RPi.GPIO as GPIO

current_instrument_index = 0
instrumentList = [instrument.name for instrument in rp.Instruments]
# Define the callback function for button press event
def button_callback(channel, piano):
    global last_button_time

    global current_instrument_index
    current_instrument_index += 1
    if current_instrument_index >= len(instrumentList):
        current_instrument_index = 0
    print(current_instrument_index)
    new_instrument = rp.Instruments[instrumentList[current_instrument_index]]
    #TODO: Read instrument first and change it based on that 
    piano.instrument(new_instrument)
    logging.info(f"Instrument changed to {new_instrument}")
    # Check if the time difference since the last button press is greater than debounce time
    # Update the last button press time

# Main loop to keep the program running
def main():
    mid = mido.MidiFile('midiFiles/Plastic_Love_-_Mariya_Takeuchi.mid')
    # mid = mido.MidiFile('midiFiles/Ocean_Waves_I_Can_Hear_the_sea.mid')
    # mid = mido.MidiFile('midiFiles/TalesWeaver_OST_Reminiscence.mid')
    # mid = mido.MidiFile('midiFiles/The_name_of_lifeInochi_No_Namae-Joe_Hisaishi.mid')
    # mid = mido.MidiFile('midiFiles/YOUNHA_-__Event_horizon_Piano_ver.mid')
    # mid = mido.MidiFile('midiFiles/A_Town_with_an_Ocean_View_Kikis_Delivery_Service__Joe_Hisaishi.mid')
    # mid = mido.MidiFile('midiFiles/Disney_Opening_Theme.mid')
    piano = None
    num = 0
    print(num.to_bytes(1, byteorder="big"))
    try:

        piano = rp.RolandPiano("C4:68:F8:B2:78:56")
        # piano.instrument(rp.Instruments.JAZZ_SCAT_2)
        piano.play_mid(mid)
        # time.sleep(250)
        while True:
            # print("hi")
            piano.idle()
            
            # piano.play_note("C-3", 50) #This is C2
            # time.sleep(1)
        field_timer = 0
        fields = ['toneForSingle'] # 'masterVolume','sequencerTempoRO',
        # piano.write_register("metronomeSwToggle", b'\x00')
        # Set up GPIO mode and pin
        # GPIO.setmode(GPIO.BOARD)
        button1 = 3
        # GPIO.setup(button1, GPIO.IN, pull_up_down=GPIO.PUD_UP)

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
            time.sleep(60)
            piano.disconnect()
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    import logging.config
    with open('logging.yaml') as f:
        config = yaml.safe_load(f)
        logging.config.dictConfig(config)
    log = logging.getLogger(__name__)
    main()
