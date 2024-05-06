from time import sleep, time
import RPi.GPIO as GPIO

# Global variable to store the last button press time
last_button_time = 0
# Debounce time in seconds
debounce_time = 0.05  # 50 milliseconds

# Define the callback function for button press event
def button_callback(channel):
    global last_button_time
    current_time = time()
    
    # Check if the time difference since the last button press is greater than debounce time
    if (current_time - last_button_time) > debounce_time:
        print("Button Pressed!")
        # Your code to interact with the Roland piano goes here
        
    # Update the last button press time
    last_button_time = current_time

# Set up GPIO mode and pin
GPIO.setmode(GPIO.BOARD)
button1 = 3
GPIO.setup(button1, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Add event detection for rising edge on button1
GPIO.add_event_detect(button1, GPIO.RISING, callback=button_callback)

# Main loop to keep the program running
message = input("Press enter to quit\n\n")
GPIO.cleanup()
