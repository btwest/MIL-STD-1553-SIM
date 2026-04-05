import socket
import threading
from bc_data_link_layer import BC_Data_Link_Encoder, BC_Data_Link_Decoder


class RT_Simulator:
    def __init__(self, rt_address='02', drop_response=False, drop_bus=None):
        self.rt_address = rt_address
        self.drop_response = drop_response  # True = drop on ALL buses
        self.drop_bus = drop_bus            # 'A' or 'B' = drop on one bus only

        # Subaddress buffers - simulated avionics telemetry
        # Each value is a string of exactly N*2 characters (N data words * 2 bytes each)
        self.subaddress_buffers = {
            '01': 'HDG095',   # Heading
            '02': 'ALT32000', # Altitude
            '03': 'SPD04800', # Airspeed
        }

        self.encoder = BC_Data_Link_Encoder()
        self.decoder = BC_Data_Link_Decoder()

        self.sock_a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock_a.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.sock_b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock_b.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


    def start(self):
        self.sock_a.bind(("", 2001))
        self.sock_b.bind(("", 2003))
        print(f"[RT {self.rt_address}] Listening on Bus A (port 2001) and Bus B (port 2003)...")

        # Bus B runs on its own daemon thread; Bus A runs on the caller's thread
        bus_b_thread = threading.Thread(
            target=self._listen_bus,
            args=(self.sock_b, 'B', 2002),
            daemon=True
        )
        bus_b_thread.start()

        self._listen_bus(self.sock_a, 'A', 2000)

    def _listen_bus(self, sock, bus, reply_port):
        """Receive loop for a single bus. Runs until the socket is closed."""
        while True:
            try:
                data, addr = sock.recvfrom(1024)
            except OSError:
                break
            if not data:
                break  # shutdown() on UDP returns b'' instead of raising OSError
            frame = data.decode('utf-8')
            print(f"[RT {self.rt_address}] Bus {bus} received frame: {frame}")
            self._handle_command(frame, sock=sock, bus=bus, reply_port=reply_port)

    def stop(self):
        for sock in (self.sock_a, self.sock_b):
            try:
                sock.shutdown(socket.SHUT_RDWR)  # unblocks any thread stuck in recvfrom
            except OSError:
                pass  # already closed or never bound
            sock.close()

    def _handle_command(self, frame, sock, bus, reply_port):
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
        sub_msb    = frame[9]
        sub_nibble = frame[10:14]
        sub_address = sub_msb + hex(int(sub_nibble, 2))[2:]

        # Read the word count
        wc_msb    = int(frame[14])
        wc_nibble = int(frame[15:19], 2)
        word_count = wc_msb * 16 + wc_nibble
        if word_count == 0:
            word_count = 32  # Per MIL-STD-1553: 00000 encodes 32 data words

        if tr_bit == '0':  # Receive — BC is sending data to us
            self._receive_data(sub_address, word_count, sock=sock, bus=bus, reply_port=reply_port)
        elif tr_bit == '1':  # Transmit — BC wants data from us
            self._transmit_data(sub_address, sock=sock, bus=bus, reply_port=reply_port)

    def _receive_data(self, sub_address, word_count, sock, bus, reply_port):
        received_words = []

        # Loop through expected data words
        for _ in range(word_count):
            data, addr = sock.recvfrom(1024)
            frame = data.decode('utf-8')

            # Decode the data word and store it
            if frame[0:3] == '001':
                decoded = self.decoder.decode_data_word(frame)
                received_words.append(decoded)

        # Reassemble and write to subaddress buffer
        payload = bytes.fromhex(''.join(received_words)).decode('utf-8')
        self.subaddress_buffers[sub_address] = payload
        print(f"[RT {self.rt_address}] SA {sub_address} buffer updated: '{payload}'")

        # Send status word back to BC to acknowledge
        self._send_status(sock=sock, bus=bus, reply_port=reply_port)

    def _send_status(self, sock, bus, reply_port):
        if self.drop_response or self.drop_bus == bus:
            print(f"[RT {self.rt_address}] Dropping status on Bus {bus} (fault simulation)")
            return
        try:
            status_frame = self.encoder.build_status_word(
                rt_address_msb='0',
                rt_address_nibble=self.rt_address[1],
                message_error=0,
                busy=0,
                terminal_flag=0
            )
            sock.sendto(status_frame.encode('utf-8'), ("127.0.0.1", reply_port))
            print(f"[RT {self.rt_address}] Sent status word on Bus {bus}")
        except OSError:
            pass

    def _transmit_data(self, sub_address, sock, bus, reply_port):
        if self.drop_response or self.drop_bus == bus:
            print(f"[RT {self.rt_address}] Dropping response on Bus {bus} (fault simulation)")
            return

        # Check if there is data for this subaddress
        if sub_address not in self.subaddress_buffers:
            print(f"[RT {self.rt_address}] No data for subaddress {sub_address}")
            self._send_status(sock=sock, bus=bus, reply_port=reply_port)
            return

        # Send status word first — always before data when RT is transmitting
        self._send_status(sock=sock, bus=bus, reply_port=reply_port)

        # Get payload from subaddress buffer
        payload = self.subaddress_buffers[sub_address]

        # Pad to even length
        if len(payload) % 2 != 0:
            payload += '.'

        try:
            # Encode and send each data word
            for i in range(0, len(payload), 2):
                pair = payload[i:i+2]
                hex_payload = pair.encode('utf-8').hex()
                data_frame = self.encoder.build_data_word(hex_payload)
                sock.sendto(data_frame.encode('utf-8'), ("127.0.0.1", reply_port))
                print(f"[RT {self.rt_address}] Sent data word on Bus {bus}: '{pair}'")
        except OSError:
            pass
