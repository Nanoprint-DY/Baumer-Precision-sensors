import tkinter as tk
from tkinter import ttk
from tkinter import font
from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import InterfaceType, ScanOptions
from threading import Thread
from scipy.signal import iirfilter, lfilter, lfilter_zi
import argparse


channel = [0, 1, 2, 3]
sensor_values = [0.0] * len(channel)  # For filtered values
raw_sensor_values = [0.0] * len(channel)  # For raw sensor values

def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = iirfilter(order, cutoff, fs=fs, btype='low', ftype='butter', output='ba')
    zi = lfilter_zi(b, a) * data[0]
    y, _ = lfilter(b, a, data, zi=zi)
    return y

def config_first_detected_device(board_num):
    ul.ignore_instacal()
    devices = ul.get_daq_device_inventory(InterfaceType.USB)
    if not devices:
        raise Exception('Error: No DAQ devices found')

    print('Found', len(devices), 'DAQ device(s):')
    for device in devices:
        print('  Device Name:', device.product_name)
        print('  Unique ID:', device.unique_id)
        print('  Device ID:', device.product_id)
        
    if len(devices) < board_num + 1:
        raise Exception(f'Error: Board number {board_num} is invalid. There are only {len(devices)} DAQ devices found.')
    
    selected_device = devices[board_num]
    ul.create_daq_device(board_num, selected_device)

def read_sensor_data(board_num, channel_index, args):
    try:
        daq_dev_info = DaqDeviceInfo(board_num)
        if not daq_dev_info.supports_analog_input:
            raise Exception('Error: The DAQ device does not support analog input')

        ai_info = daq_dev_info.get_ai_info()
        ai_range = ai_info.supported_ranges[0]

        data_buffer = []
        cutoff = args.cutoff  # Filter cutoff frequency in Hz
        sample_size = args.sample_size  # Buffer size for filtering
        fs = args.sample_rate  # Sample rate in Hz

        # Configure triggering
        #ul.set_trigger(board_num, TriggerType.IMMEDIATE)
        print('Configured triggering as IMMEDIATE')

        total_samples = sample_size * 10  # Read 10 times the buffer size
        scan_options = ScanOptions.BACKGROUND | ScanOptions.CONTINUOUS
        print('Configured scan options:', scan_options)

        memhandle = ul.win_buf_alloc(total_samples)
        ul.a_in_scan(
            board_num, channel[channel_index], channel[channel_index], total_samples,
            args.sample_rate, ai_range, memhandle, scan_options)
        print('Started analog input scan')

        while True:
            if ul.get_status(board_num).current_scan_count >= total_samples:
                # Read the data
                ul.win_buf_to_array(memhandle, sensor_values)
                ul.win_buf_free(memhandle)

                # Apply low-pass filter
                filtered_value = butter_lowpass_filter(sensor_values, cutoff, fs, order=5)[-1]
                sensor_values[channel_index] = filtered_value

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print('\nError:', e)
    finally:
        ul.release_daq_device(board_num)

def create_gui():
    root = tk.Tk()
    root.title("Sensor Data GUI")

    # Define a larger font
    larger_font = font.Font(size=18)  # You can adjust the size as needed

    labels = []
    raw_labels = []  # Labels for raw sensor values

    threads = []

    for i in range(len(channel)):
        # Label for filtered values with larger font
        labels.append(ttk.Label(root, text=f"Sensor {channel[i]} Filtered: 0.0 mV", font=larger_font))
        labels[i].grid(row=i*2, column=0, padx=10, pady=10)

        # Label for raw values with larger font
        raw_labels.append(ttk.Label(root, text=f"Sensor {channel[i]} Raw: 0.0 mV", font=larger_font))
        raw_labels[i].grid(row=i*2+1, column=0, padx=10, pady=10)

        t = Thread(target=read_sensor_data, args=(0, i, args))  # Assuming board number is 0, change it if needed
        t.daemon = True
        t.start()
        threads.append(t)

    def update_labels():
        while True:
            for i in range(len(channel)):
                labels[i].config(text=f"Sensor {channel[i]} Filtered: {sensor_values[i]*1000:.1f} mV")
                raw_labels[i].config(text=f"Sensor {channel[i]} Raw: {raw_sensor_values[i]*1000:.1f} mV")
            root.update()

    update_thread = Thread(target=update_labels)
    update_thread.daemon = True
    update_thread.start()

    root.mainloop()

if __name__ == '__main__':
    # Define and parse command-line arguments
    parser = argparse.ArgumentParser(description='Sensor Data Filtering')
    parser.add_argument('--cutoff', type=float, default=0.4, help='Cutoff frequency of the filter in Hz')
    parser.add_argument('--sample-size', type=int, default=1000, help='Buffer size for filtering')
    parser.add_argument('--sample-rate', type=float, default=200.0, help='Sample rate in Hz')
    args = parser.parse_args()

    config_first_detected_device(0)  # Assuming the first detected device should be used
    create_gui()