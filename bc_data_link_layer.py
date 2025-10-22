
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

            self.rt_address = self.rt_address + status_word_frame[3]

            addr_char = status_word_frame[4:8]
            self.rt_address = self.rt_address + str(hex(int(addr_char, 2)))[2:]
            status_word['rt_address'] = self.rt_address

            # Error bit
            self.message_error_bit = status_word_frame[8]
            status_word['message_error_bit'] = self.message_error_bit
            
            # Instrumentation bit
            self.instrumentation_bit = status_word_frame[9]
            status_word['instrumentation_bit'] = self.instrumentation_bit

            # Service request bit
            self.service_request_bit = status_word_frame[10]
            status_word['service_request_bit'] = self.service_request_bit

            # Reserved bits
            self.reserved_bits = status_word_frame[11:14]
            status_word['reserved_bits'] = self.reserved_bits

            # BRDCST received bit
            self.brdcst_received_bit = status_word_frame[14]
            status_word['brdcst_received'] = self.brdcst_received_bit

            # Busy bit
            self.busy_bit = status_word_frame[15]
            status_word['busy_bit'] = self.busy_bit

            # Subsystem flag bit
            self.subsystem_flag_bit = status_word_frame[16]
            status_word['subsystem_flag_bit'] = self.subsystem_flag_bit

            # Dynamic bus control accept bit
            self.dynamic_bus_control_accpt_bit = status_word_frame[17]
            status_word['dynamic_bus_control_accpt_bit'] = self.dynamic_bus_control_accpt_bit

            # Terminal flag bit
            self.terminal_flag_bit = status_word_frame[18]
            status_word['terminal_flag_bit'] = self.terminal_flag_bit

            print (status_word)
            return status_word
        except Exception as ex:
            print("Exception while decoding a status word from an RT")
            print("    Exception:{}".format(str(ex)))
        

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
    def _char_check(self, character):
        pass

    def build_cmd_word(self, cmd_word):
        pass

    def build_data_word(self, data_word):
        pass