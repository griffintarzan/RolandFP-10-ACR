import RPi.GPIO as GPIO 
import time
from RPLCD.gpio import CharLCD

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

while True:
    try:
        lcd.clear()
        
        
        # song_name = "T.B.H"
        # song_name = song_name.replace("_", " ")
        # print(song_name)
        # # print(song_name[:16])
        
        # lcd.write_string("Playing"+ " \x00 " + song_name[:22])
        # lcd.write_string("Recording...")
        lcd.write_string("Tone: Jazz_SCAT")
        time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped")
        lcd.close(clear=True) 
        GPIO.cleanup()
