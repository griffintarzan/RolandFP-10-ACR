import mido
import time
#TODO: Change it to seconds and try it on ble midi
mid = mido.MidiFile('midiFiles/Plastic_Love_-_Mariya_Takeuchi.mid')
print(mid.ticks_per_beat)

print(len(mid.tracks))
print(mid.type)
def get_unix_time():
    return int(bin(int(time.time()))[-8:],2).to_bytes(1,byteorder='little')
# for msg in mid.play():
#     print(str(get_unix_time()) + " " + str(msg))
# for i, track in enumerate(mid.tracks):
    # with open('midi_reading.txt', "a") as f:
    #     print('Track {}: {}'.format(i, track.name))
    #     f.write('Track {}: {}\n'.format(i, track.name))
    #     for msg in track:
            
    #         f.write(str(msg))
            
    #         f.write(f" {msg.time}")
            
    #         f.write('\n')
    #         f.write(msg.hex())
    #         f.write("\n")
for msg in mid:
    with open('midi_reading.txt', "a") as f:       
        f.write(str(msg))
        f.write(f" {msg.time}")
        
        f.write('\n')
        f.write(msg.hex())
        f.write("\n")

def create_ble_midi_header(delta_ms, last_timestamp_ms):
    # Masking the header to fit within 6 bits (0x3F) and 7 bits (0x7F) for the timestamp
    time_ms = (last_timestamp_ms + delta_ms) % 8192
    header = 0x80 | ((time_ms >> 7) & 0x3F)  # MSB of the timestamp goes into header
    timestamp = 0x80 | ((time_ms) & 0x7F)  # Remaining 7 bits for timestamp
    return header, timestamp

# Function to encode a single MIDI message into BLE-MIDI format
def encode_midi_to_ble_midi(midi_message, delta_ms, last_timestamp_ms):
    header, timestamp = create_ble_midi_header(delta_ms, last_timestamp_ms)
    ble_midi_packet = header + timestamp + midi_message
    return ble_midi_packet

# with open('TalesWeaver_OST_Reminiscence.mid', "rb") as f:
#     content = f.read(14)
#     firstTrackChunk = f.read(8)
#     print(content)
#     print(firstTrackChunk)