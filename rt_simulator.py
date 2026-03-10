import socket
from bc_data_link_layer import BC_Data_Link_Encoder, BC_Data_Link_Decoder


class RT_Simulator:
    def __init__(self, rt_address='02', drop_response=False):
        self.rt_address = rt_address
        self.drop_response = drop_response

        # Subaddress buffers - simulated avionics telemetry
        # Each value is a string of exactly N*2 characters (N data words * 2 bytes each)
        self.subaddress_buffers = {
            '01': 'HDG095', # Heading
            '02': 'ALT3200', # Altitude
            '03': 'SPD0480', # Airspeed
        }

        self.encoder = BC_Data_Link_Encoder()
        self.decoder = BC_Data_Link_Decoder()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", 2001))  


    def start(self):
        print(f"[RT {self.rt_address}] Listening on port 2001...")
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
            except OSError:
                break
            frame = data.decode('utf-8')
            print(f"[RT {self.rt_address}] Received frame: {frame}")
            self._handle_command(frame)

    def stop(self):
        self.sock.close()
    
    def _handle_command(self, frame):
        # Only handle command words — ignore data words at this level
        if frame[0:3] != '100':
            return
        
        # Decode the command word
        decoded = self.decoder.decode_command_word(frame)
        
        # Check if this command is addressed to us
        if decoded['rt_address'] != self.rt_address:
            print(f"[RT {self.rt_address}] Command not addressed to us, ignoring.")
            return
        
        # Read the T/R bit — position 8 in the frame
        tr_bit = frame[8]

        # Read the subaddress — MSB at position 9, nibble at positions 10:14
        sub_msb = frame[9]
        sub_nibble = frame[10:14]
        sub_address = sub_msb + hex(int(sub_nibble, 2))[2:]
        
        if tr_bit == '0':  # Receive — BC is sending data to us
            self._receive_data(sub_address)
        elif tr_bit == '1':  # Transmit — BC wants data from us
            self._transmit_data(sub_address)

    def _receive_data(self, sub_address):
        received_words = []
        
        # Listen for incoming data words
        while True:
            data, addr = self.sock.recvfrom(1024)
            frame = data.decode('utf-8')
            
            # Stop when we see a new command word
            if frame[0:3] == '100':
                break
                
            # Decode the data word and store it
            if frame[0:3] == '001':
                decoded = self.decoder.decode_data_word(frame)
                received_words.append(decoded)
        
        # Reassemble and write to subaddress buffer
        payload = bytes.fromhex(''.join(received_words)).decode('utf-8')
        self.subaddress_buffers[sub_address] = payload
        print(f"[RT {self.rt_address}] SA {sub_address} buffer updated: '{payload}'")
        
        # Send status word back to BC to acknowledge
        self._send_status()

    def _send_status(self):
        if self.drop_response:
            print(f"[RT {self.rt_address}] Dropping response (fault simulation)")
            return
        
        status_frame = self.encoder.build_status_word(
            rt_address_msb='0',
            rt_address_nibble=self.rt_address[1],
            message_error='0',
            busy=0,
            terminal_flag=0
        )

        self.sock.sendto(status_frame.encode('utf-8'), ("127.0.0.1", 2000))
        print(f"[RT {self.rt_address}] Sent status word")

    def _transmit_data(self, sub_address):
        # Check if there is data for this subaddress
        if sub_address not in self.subaddress_buffers:
            print(f"[RT {self.rt_address}] No data for subaddress {sub_address}")
            self._send_status()
            return
        
        # send status word first - always before data when RT is transmitting
        self._send_status()

        # get payload from subaddress buffer
        payload = self.subaddress_buffers[sub_address]

        # Pad to even length
        if len(payload) %2 != 0:
            payload += '.'
        
        #Encode and send data word
        for i in range(0, len(payload), 2):
            pair = payload[i:i+2]
            hex_payload = pair.encode('utf-8').hex()
            data_frame = self.encoder.build_data_word(hex_payload)
            self.sock.sendto(data_frame.encode('utf-8'), ("127.0.0.1", 2000))
            print(f"[RT {self.rt_address}] Sent data word: '{pair}'")