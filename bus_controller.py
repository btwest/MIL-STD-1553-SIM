from bc_message_layer import BC_Message_Decoder, BC_Message_Encoder
from bc_physical_layer import BC_Sender, BC_Listener
import threading
import time
import queue

class Bus_Controller:
    """
    Simulated MIL-STD-1553 Bus Controller (BC)

    This class represents the BC role in a MIL-STD-1553 communication setup.
    It handles:
        - Message creation and encoding (Message Layer)
        - Transmission and reception of frames (Physical Layer)
        - Continuous background listening for RT responses on both buses
        - Dual-bus redundancy with automatic failover (Bus A → Bus B)

    The BC acts as the *master node* on the bus - it initiates all communication
    by sending command words and expects RTs (Remote Terminals) to respond with
    status and/or data words.
    """

    _FAILOVER_TIMEOUT = 3.0  # seconds (real MIL-STD-1553: 14 µs no-response timeout)

    # ----------------------------- PRIVATE METHODS -----------------------------

    def __init__(self):
        self.sender_a   = BC_Sender(bus='A')
        self.sender_b   = BC_Sender(bus='B')
        self.listener_a = BC_Listener(bus='A')
        self.listener_b = BC_Listener(bus='B')
        self._active_bus = 'A'  # BC always starts on Bus A per MIL-STD-1553B convention
        self.received_messages = []
        self._rx_lock = threading.Lock()
        self.received_statuses = []
        self._status_event = threading.Event()  # set whenever any status word arrives

    def get_last_status(self):
        with self._rx_lock:
            if self.received_statuses:
                return self.received_statuses.pop()
            return None

    def _send_with_failover(self, frames):
        """
        Transmit frames on the active bus. If no status-word response arrives
        within _FAILOVER_TIMEOUT seconds, switch to the other bus and retransmit.

        This mirrors the MIL-STD-1553B §4.2 requirement: the BC must detect a
        no-response condition and retry on the redundant bus before declaring
        an RT unresponsive.
        """
        senders  = {'A': self.sender_a,  'B': self.sender_b}
        fallback = {'A': 'B',            'B': 'A'}

        # Transmit on the active bus
        self._status_event.clear()
        print(f"[BC] Transmitting on Bus {self._active_bus}")
        for frame in frames:
            senders[self._active_bus].send_message(frame)
            time.sleep(1)

        # Wait for a status-word acknowledgement — uses an Event so the status
        # word stays in received_statuses and remains readable by the caller
        if self._status_event.wait(timeout=self._FAILOVER_TIMEOUT):
            return  # acknowledged — stay on active bus

        # No response — failover to the other bus
        self._active_bus = fallback[self._active_bus]
        print(f"[BC] No response — failing over to Bus {self._active_bus}")
        self._status_event.clear()
        for frame in frames:
            senders[self._active_bus].send_message(frame)
            time.sleep(1)

    def _send_data(self, frames):
        """
        Sends a list of encoded frames over the simulated bus with failover support.

        Args: frames(list[str]): Encoded frames (e.g., command/data words)
                                 produced by the Message Layer Encoder.
        """
        self._send_with_failover(frames)

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
            self._status_event.set()  # signal _send_with_failover without consuming the status


    # ------------------------------ PUBLIC METHODS -----------------------------


    def start_listener(self):
        for listener in (self.listener_a, self.listener_b):
            threading.Thread(
                target=listener.start_listening,
                daemon=True
            ).start()

        poll_thread = threading.Thread(
            target=self._poll_listener,
            daemon=True
        )
        poll_thread.start()

    def _poll_listener(self):
        while True:
            drained = False
            for listener in (self.listener_a, self.listener_b):
                try:
                    frame = listener.data_received.get_nowait()
                    self._handle_incoming_frame(frame)
                    drained = True
                except queue.Empty:
                    pass
            if not drained:
                time.sleep(0.01)

    def send_data_to_rt(self, rt_address, sub_address_or_mode_code, message):
        """
        Sends a data message from the BC to an RT.

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
            - The command is sent, and the BC waits for a response
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
