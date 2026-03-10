
class BC_Data_Link_Decoder:

    message_error_bit = ''
    instrumentation_bit = ''
    service_request_bit = ''
    reserved_bits = ''
    brdcst_received_bit = ''
    busy_bit = ''
    subsystem_flag_bit = ''
    dynamic_bus_control_accpt_bit = ''
    terminal_flag_bit = ''
    rt_address = ''
    
    def decode_status_word(self, status_word_frame):
        try:
            status_word = {}

            # Build rt_address as a local variable — not stored on self
            rt_address = status_word_frame[3]
            rt_address += hex(int(status_word_frame[4:8], 2))[2:]
            status_word['rt_address'] = rt_address

            # Error bit
            status_word['message_error_bit']            = status_word_frame[8]

            # Instrumentation bit
            status_word['instrumentation_bit']          = status_word_frame[9]
        
            # Service request bit
            status_word['service_request_bit']          = status_word_frame[10]

            # Reserved bits
            status_word['reserved_bits']                = status_word_frame[11:14]

            # Broadcast received bit
            status_word['brdcst_received']              = status_word_frame[14]

            # Busy bit
            status_word['busy_bit']                     = status_word_frame[15]

            # Subsystem flag bit
            status_word['subsystem_flag_bit']           = status_word_frame[16]

            # Dynamic bus control accept bit
            status_word['dynamic_bus_control_accpt_bit']= status_word_frame[17]

            # Terminal flag bit
            status_word['terminal_flag_bit']            = status_word_frame[18]

            return status_word

        except Exception as ex:
            print("Exception while decoding a status word from an RT")
            print(f"    Exception: {ex}")
        def decode_command_word(self, frame):
            # Command words and status words share identical bit layout.
            # This wrapper exists to make intent explicit at the call site.
            return self.decode_status_word(frame)
    
    def decode_command_word(self, frame):
        # Command words and status words share identical bit layout.
        # This wrapper exists to make intent explicit at the call site.
        return self.decode_status_word(frame)

    def decode_data_word(self, data_word_frame):
        try:
            data_word = ''

            for i in range(3, len(data_word_frame)-4,4):
                data_set = data_word_frame[i:i+4]
                data_word = data_word + str(hex(int(data_set, 2)))[2:]
            return data_word
        except Exception as ex:
            print("Exception while decoding a data word from an RT")
            
class BC_Data_Link_Encoder:

    def _validate_bit(self, character, label="bit"):
        if character not in ('0', '1'):
            raise ValueError(f"Invalid {label}: '{character}' — must be '0' or '1'")

    def _char_check(self, character):
        if not str.isdigit(character):
            print("Invalid address bits")
            return False
        elif int(character) != 0 and int(character) != 1:
            print("Invalid address bits 1")
            return False
        return True
    

    def build_cmd_word(self, cmd_word):
        try:
            cmd_word_frame = '100'

            char1 = cmd_word[0]
            if not self._char_check(char1):
                exit()
            cmd_word_frame = cmd_word_frame + char1

            char2 = cmd_word[1]
            cmd_word_frame = cmd_word_frame + '{0:04b}'.format(int(char2,16))

            char3 = cmd_word[2]
            if char3 == 'R':
                cmd_word_frame = cmd_word_frame + '0'
            elif char3 == 'T':
                cmd_word_frame = cmd_word_frame + '1'
            else:
                print("Invalid TR bit")
                exit()

            char4 = cmd_word[3]
            if not self._char_check(char4):
                exit()
            cmd_word_frame = cmd_word_frame + char4

            char5 = cmd_word[4]
            cmd_word_frame = cmd_word_frame + '{0:04b}'.format(int(char5,16))

            char6 = cmd_word[5]
            if not self._char_check(char6):
                exit()
            cmd_word_frame = cmd_word_frame + char6

            char7 = cmd_word[6]
            cmd_word_frame = cmd_word_frame + '{0:04b}'.format(int(char7,16))

            cmd_word_frame = cmd_word_frame + '1'

            return cmd_word_frame
        except Exception as ex:
            print("Exception while building a command word frame")
            print("    Exception:{}".format(str(ex)))

    def build_status_word(self, rt_address_msb, rt_address_nibble,
                        message_error=0, busy=0, terminal_flag=0):
        frame = '100'
        self._validate_bit(rt_address_msb, "RT address MSB")
        frame += rt_address_msb
        frame += '{0:04b}'.format(int(rt_address_nibble, 16))
        frame += str(message_error)
        frame += '0'   # instrumentation
        frame += '0'   # service request
        frame += '000' # reserved
        frame += '0'   # broadcast received
        frame += str(busy)
        frame += '0'   # subsystem flag
        frame += '0'   # dynamic bus control
        frame += str(terminal_flag)
        frame += '1'   # parity
        return frame

    def build_data_word(self, data_word):
        try:
            if(len(data_word) != 4):
                print("Data word must be 4 hex characters long")
                exit()
            
            data_word_frame = '001'

            for character in data_word:
                data_word_frame = data_word_frame + '{0:04b}'.format(int(character,16))

            data_word_frame = data_word_frame + '1'

            return data_word_frame
                   
        except Exception as ex:
            print("Exception while building a data word frame")
            print("    Exception:{}".format(str(ex)))   