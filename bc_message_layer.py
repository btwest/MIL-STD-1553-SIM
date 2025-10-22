from bc_data_link_layer import BC_Data_Link_Decoder, BC_Data_Link_Encoder

class BC_Message_Decoder:

    def _deconstruct_status_word(self, recd_status_frame):
        recd_status_word = \
            BC_Data_Link_Decoder().decode_status_word(recd_status_frame)
        return recd_status_word
    
    def _deconstruct_data_word(self, recd_data_frame):
        recd_data_word = \
            BC_Data_Link_Decoder().decode_data_word(recd_data_frame)
        return recd_data_word

    def interpret_incoming_frame(self, recd_frame):
        if recd_frame[0:3] == "100":
            status_word = self._deconstruct_status_word(recd_frame)
            return status_word
        elif recd_frame[0:3] == "001":
            data_word = self._deconstruct_data_word(recd_frame)
            return bytes.fromhex(data_word)


class BC_Message_Encoder:
    def construct_command_word(
            self, rt_address, tr_bit, sub_address, data_word_count
    ):
        if not len(rt_address) > 2:
            command_word = command_word + rt_address

        if (not len(tr_bit)> 1) and tr_bit.isalpha():
            command_word = command_word + tr_bit

        if not len(sub_address) > 2:
            command_word = command_word + sub_address

        if not len(data_word_count)> 2:
            command_word = command_word + data_word_count

        if len(command_word) < 7 or len(command_word) > 7:
            raise Exception("Invaid data input. Command word format does not match.")
        command_frame = \
            BC_Data_Link_Encoder().build_cmd_word(command_word)
        return command_frame
    
    def construct_data_word(self, data_wd_part):
        data_part_frame = \
            BC_Data_Link_Encoder().build_data_word(data_wd_part)
        # TODO checksum
        return data_part_frame

    def send_message_to_RT(
            self, rt_address, sub_address_or_mode_code, message):
        pass

    def receive_message_from_RT(self, rt_address, sub_address_or_mode_code, data_word_count):
        pass