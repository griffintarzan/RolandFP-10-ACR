from enum import Enum
class Instruments(Enum):
    GRAND_PIANO_1 = (0, 0, 0, 68, 1)
    GRAND_PIANO_2 = (0, 1, 16, 67, 1)
    GRAND_PIANO_3 = (0, 2, 4, 64, 1)
    GRAND_PIANO_4 = (0, 3, 8, 66, 2)
    E_PIANO = (0, 4, 16, 67, 5)
    WURLY = (0, 5, 25, 65, 5) #not sure 25, 64, 5? or 65
    CLAV = (0, 6, 0, 67, 8) #works.
    JAZZ_ORGAN_1 = (0, 7, 0, 70, 19)
    PIPE_ORGAN = (0, 8, 8, 70, 20) #this was pipe_organ_2
    JAZZ_SCAT = (0, 9, 0, 65, 55)
    STRINGS_1 = (0, 10, 0, 71, 50)
    PAD = (0, 11, 1, 71, 90) #not sure Correct
    CHOIR_1 = (0, 12, 8, 64, 53)
    NYLON_STR_GTR = (0, 13, 0, 0, 25)
    ABASS_CYMBAL = (0, 14, 0, 66, 33)


    RAGTIME_PIANO = (1, 0, 0, 64, 4)
    HARPSICHORD_1 = (1, 1, 0, 66, 7)
    HARPSICHORD_2 = (1, 2, 8, 66, 7)
    E_PIANO_2 = (1, 3, 0, 70, 6)
    VIBRAPHONE = (1, 4, 0, 0, 12) 
    CELESTA = (1, 5, 0, 0, 9)
    SYNTH_BELL = (1, 6, 0, 68, 99)  
    STRINGS_2 = (1, 7, 0, 64, 49)
    HARP = (1, 8, 0, 68, 47)
    JAZZ_ORGAN_2 = (1, 9, 0, 69, 19)
    PIPE_ORGAN2 = (1, 10, 8, 70, 20) #not sure GOT IT
    ACCORDION = (1, 11, 0, 68, 22)
    CHOIR_2 = (1, 12, 8, 66, 53)
    CHOIR_3 = (1, 13, 8, 68, 53)
    SYNTH_PAD = (1, 14, 0, 64, 90)
    STEEL_STR_GTR = (1, 15, 0, 0, 26)
    DECAY_STRINGS = (1, 16, 1, 65, 50)
    DECAY_CHOIR = (1, 17, 1, 64, 53)
    ACOUSTIC_BASS = (1, 18, 0, 0, 33)
    FINGERED_BASS = (1, 19, 0, 0, 34)
    THUM_VOICE = (1, 20, 0, 66, 54)

instrument_lookup = {
            (instrument.value[0] << 16) | instrument.value[1]: instrument
            for instrument in Instruments
        }
