import logging
import yaml
import time
import RolandPiano as rp

# Main loop to keep the program running
def main():
    
    
    piano = None
    try:
        piano = rp.RolandPiano("C4:68:F8:B2:78:56")
        
        piano.play_note_duration("C-5", 50, 1) #This is C4
        time.sleep(1)
        piano.play_note("C-5", 50)

            
    except KeyboardInterrupt:
        log.info("Exit cmd given by user, disconnecting..")
        if piano:
            
            piano.disconnect()


if __name__ == "__main__":
    import logging.config
    with open('logging.yaml') as f:
        config = yaml.safe_load(f)
        logging.config.dictConfig(config)
    log = logging.getLogger(__name__)
    main()
