import logging
import yaml
import time
import RolandPiano as rp
def main():
    piano = None
    num = 0
    print(num.to_bytes(1, byteorder="big"))
    try:

        piano = rp.RolandPiano("C4:68:F8:B2:78:56")
        field_timer = 0
        fields = ['toneForSingle'] # 'masterVolume','sequencerTempoRO',
        # piano.write_register("metronomeSwToggle", b'\x00')
        
        log.info(f"Setting instrument to {rp.Instruments.CHOIR_2}")
        # piano.instrument(rp.Instruments.JAZZ_SCAT_2)
        # status = piano.read_register("toneForSingle")
        # log.info(f"instrument status : {status}")
        for instrument in rp.Instruments:
            logging.info(f"Setting instrument to {instrument}")
            piano.instrument(instrument)
            time.sleep(10)
                
        while True:
            break
            # Update state of the key_status
            piano.write_register("metronomeSwToggle", b'\x00')
            for k,v in piano.delegate.message.sustained_key_status.items():
                if v > 0 : piano.delegate.message.sustained_key_status[k] -= 1


            piano.idle()

            piano.print_fields(fields, onlyUpdates=True)

            if field_timer == 5:
                field_timer = 0
                piano.update_fields(fields)
                break
            else:
                field_timer += 1

            
    except KeyboardInterrupt:
        log.info("Exit cmd given by user, disconnecting..")
        if ambiPiano:
            ambiPiano.kill()
        if piano:
            piano.disconnect()


if __name__ == "__main__":
    import logging.config
    with open('logging.yaml') as f:
        config = yaml.safe_load(f)
        logging.config.dictConfig(config)
    log = logging.getLogger(__name__)
    main()
