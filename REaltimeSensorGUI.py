import tkinter as tk
from tkinter import ttk
from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import InterfaceType
from threading import Thread
import datetime as dt

data = 2000
channel = [0, 1, 2, 3]
sensor_values = [0.0] * len(channel)

def config_first_detected_device(board_num, dev_id_list=None):
    ul.ignore_instacal()
    devices = ul.get_daq_device_inventory(InterfaceType.USB)
    if not devices:
        raise Exception('Error: No DAQ devices found')

    print('Found', len(devices), 'DAQ device(s):')
    for device in devices:
        print('  ', device.product_name, ' (', device.unique_id, ') - ',
              'Device ID = ', device.product_id, sep='')

    device = devices[0]
    ul.create_daq_device(board_num, device)

def read_sensor_data(board_num, channel_index):
    try:
        daq_dev_info = DaqDeviceInfo(board_num)
        if not daq_dev_info.supports_analog_input:
            raise Exception('Error: The DAQ device does not support analog input')

        ai_info = daq_dev_info.get_ai_info()
        ai_range = ai_info.supported_ranges[0]

        while True:
            value = ul.a_in(board_num, channel[channel_index], ai_range)
            eng_units_value = ul.to_eng_units(board_num, ai_range, value)
            sensor_values[channel_index] = eng_units_value

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print('\n', e)
    finally:
        ul.release_daq_device(board_num)

def create_gui():
    root = tk.Tk()
    root.title("Sensor Data GUI")

    labels = []
    for i in range(len(channel)):
        labels.append(ttk.Label(root, text=f"Sensor {channel[i]}: 0.0 mV"))
        labels[i].grid(row=i, column=0, padx=10, pady=10)

        t = Thread(target=read_sensor_data, args=(1, i))
        t.daemon = True
        t.start()

    def update_labels():
        while True:
            for i in range(len(channel)):
                labels[i].config(text=f"Sensor {channel[i]}: {sensor_values[i]*1000:.1f} mV")
            root.update()

    update_thread = Thread(target=update_labels)
    update_thread.daemon = True
    update_thread.start()

    root.mainloop()

if __name__ == '__main__':
    config_first_detected_device(1)
    create_gui()