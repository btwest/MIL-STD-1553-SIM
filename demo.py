import threading
import time
from bus_controller import Bus_Controller
from rt_simulator import RT_Simulator

def print_header():
    print("═══════════════════════════════════════════════════════")
    print("  MIL-STD-1553 Bus Protocol Simulator")
    print("  West-Tek Solutions")
    print("═══════════════════════════════════════════════════════")
    print()

def print_scenario(number, title):
    print(f"\n[SCENARIO {number}] {title}")
    print("─" * 50)


def scenario_1(bc):
    print_scenario(1, "BC → RT Write")
    print("  BC sending 'NAVIGATE' to RT-02 subaddress 01...")
    bc.send_data_to_rt('02', '01', 'NAVIGATE')
    time.sleep(10)  # Give RT time to process and respond
    status = bc.get_last_status()
    if status and status['message_error_bit'] == '0':
        print("  RT-02 acknowledged ✓")
    else:
        print("  RT-02 did NOT acknowledge ✗")
def scenario_2(bc):
    print_scenario(2, "BC → RT Read (Telemetry Poll)")
    print("  BC polling RT-02 subaddress 02 (Altitude)...")
    bc.receive_data_from_rt('02', '02', '04')
    time.sleep(5)
    received = bc.get_received_text()
    print(f"  Received from RT-02: '{received}' ✓")
def scenario_3(bc):
    print_scenario(3, "BC → RT Full Telemetry Poll")
    subaddresses = {
        '01': ('Heading',   '03'),
        '02': ('Altitude',  '04'),
        '03': ('Airspeed',  '04'),
    }
    for sa, (label, word_count) in subaddresses.items():
        print(f"  Polling RT-02 subaddress {sa} ({label})...")
        bc.receive_data_from_rt('02', sa, word_count)
        time.sleep(1)
        received = bc.get_received_text()
        print(f"  {label}: '{received}' ✓")
def scenario_4(bc, rt):
    print_scenario(4, "Fault Simulation — RT Not Responding")
    rt.stop()
    time.sleep(0.5)
    rt_silent = RT_Simulator(rt_address='02', drop_response=True)
    rt_silent_thread = threading.Thread(target=rt_silent.start, daemon=True)
    rt_silent_thread.start()
    time.sleep(0.5)
    print("  BC polling RT-02 subaddress 01 (Heading)...")
    print("  RT-02 is not responding — waiting for timeout...")
    bc.receive_data_from_rt('02', '01', '03')
    time.sleep(3)
    received = bc.get_received_text()
    if not received:
        print("  No response received from RT-02 ✗")
        print("  [BC] Timeout — marking RT-02 as unresponsive")
    else:
        print(f"  Received: '{received}'")

def main():
    print_header()
    
    rt = RT_Simulator(rt_address='02')
    rt_thread = threading.Thread(target=rt.start, daemon=True)
    rt_thread.start()
    time.sleep(0.5)
    
    bc = Bus_Controller()
    bc.start_listener()
    time.sleep(0.5)

    scenario_1(bc)
    scenario_2(bc)
    scenario_3(bc)
    scenario_4(bc, rt)

    print("\n═══════════════════════════════════════════════════════")
    print("  Simulation complete.")
    print("═══════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()