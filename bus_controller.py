from bc_message_layer import BC_Message_Decoder, BC_Message_Encoder
from bc_physical_layer import BC_Sender, BC_Listener
import threading
import time

class Bus_Controller:
    """
    Simulated MIL-STD-1553 Bus Controller (BC)

    This class represents the BC role in a MIL-STD-1553 communication setup.
    It handles:
        - Message creation and encoding (Message Layer)
        - Transmission and reception of frames (Physical Layer)
        - Continuous background listening for RT responses

    The BC acts as the *master node* on the bus - it initiates all communication
    by sending command words and expects RTs (Remote Terminals) to respond with status and/or data words.
    """

    # ----------------------------- PRIVATE METHODS -----------------------------

    def __init__(self):
        self.sender = BC_Sender()
        self.listener = BC_Listener()
        self.received_messages = []
        self._rx_lock = threading.Lock()
        self.received_statuses = []

    def get_last_status(self):
        with self._rx_lock:
            if self.received_statuses:
                return self.received_statuses.pop()
            return None

    def _send_data(self, frames):
        """
        Sends a list of encoded frames over the simulated bus.

        Args: frames(list[str]): Encoded frames (e.g., command/data words)
                                 produced by the Message Layer Encoder.

        Process:
            - Iterates through each frame and uses BC_Sender to transmit.
            - Introduces a 1-second delay between frames to simulate
            transmission timing (1553 operates sequentially, not in bursts).
        """
        for frame in frames:
            self.sender.send_message(frame)
            time.sleep(1) # simulate timing between words
    
    def _handle_incoming_frame(self, frame):
        decoded = BC_Message_Decoder().interpret_incoming_frame(frame)
        if isinstance(decoded, bytes):
            text = decoded.decode('utf-8')
            print(f"[BC] Received data: '{text}'")
            with self._rx_lock:
                self.received_messages.append(text)
        else:
            with self._rx_lock:
                self.received_statuses.append(decoded)
                print(f"[BC] Received status: {decoded}")

    
    # ------------------------------ PUBLIC METHODS -----------------------------


    def start_listener(self):
        listener_thread = threading.Thread(
            target=self.listener.start_listening,
            daemon=True
        )
        listener_thread.start()

        poll_thread = threading.Thread(
            target=self._poll_listener,
            daemon=True
        )
        poll_thread.start()

    def _poll_listener(self):
        while True:
            if self.listener.data_received:
                self._handle_incoming_frame(self.listener.data_received.pop(0))
            time.sleep(0.01)

    def send_data_to_rt(self, rt_address, sub_address_or_mode_code, message):
        """
        Sends a data message from the BC to an RT
        
        Args:
            rt_address (str): Address of the target RT.
            sub_address_or_mode_code(str): Target subaddress or mode code.
            message (str): The human-readable message (payload).
            
            Process:
                - The Message Layer Encoder builds a command + data frame sequence.
                - The Physical Layer sender transmits each frame sequentially.
                
                Example:
                    send_data_to_rt("02", "05", "HELLO")
        """
        frames = BC_Message_Encoder().send_message_to_RT(
            rt_address, sub_address_or_mode_code, message
        )
        self._send_data(frames)
        
    def receive_data_from_rt(self, rt_address, sub_address_or_mode_code, word_count):
        """
        Requests data from an RT (BC commands the RT to transmit).
        
        Args: 
            rt_address (str): Address of the RT to query.
            sub_address_or_mode_code (str): RT subaddress or mode code.
            word_count (str): Expected number of data words to receive.

        Process: 
            - The Message Layer Encoder constructs a command word
            with the TR bit = 'T' (indicating the RT should transmit).
            - The command is sent, and the BC waits for a. response
            (the listener thread should capture the incoming frames).
        """
        frames = BC_Message_Encoder().receive_message_from_RT(rt_address, sub_address_or_mode_code, word_count)
        self._send_data(frames)

    def get_received_text(self):
        with self._rx_lock:
            result = ''.join(self.received_messages)
            self.received_messages.clear()
        return result

# ------------------------------ ENTRY POINT ------------------------------

if __name__ == "__main__":
    bc = Bus_Controller()
    bc.start_listener()
    
    print("Bus Controller running. Press Ctrl+C to exit.")
    try:
        threading.Event().wait()  # blocks forever until Ctrl+C
    except KeyboardInterrupt:
        print("Shutdown.")