from __future__ import absolute_import, division, print_function
from builtins import *  # @UnusedWildImport

from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from time import sleep
from ctypes import cast, POINTER, c_double, c_ushort, c_ulong
from mcculw.enums import ScanOptions, FunctionType, Status, InterfaceType

import datetime as dt
import matplotlib.pyplot as plt
#import matplotlib.animation as animation
import scipy.signal

single = True
data = 1000
channel = 1
sensor_value = []

# Create figure for plotting
fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
xs = []
ys = []


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

    #single Analog Input
    # Add the first DAQ device to the UL with the specified board number
    if single:
        ul.create_daq_device(board_num, device)
        analog_input(board_num, channel, 1, data)
    else:
        #Multi Analog Input
        multi_analog_input(board_num)

def multi_analog_input(board_num):
    # By default, the example detects and displays all available devices and
    # selects the first device listed. Use the dev_id_list variable to filter
    # detected devices by device ID (see UL documentation for device IDs).
    # If use_device_detection is set to False, the board_num variable needs to
    # match the desired board number configured with Instacal.
    use_device_detection = True
    dev_id_list = []
    rate = 100
    points_per_channel = 1000
    memhandle = None

    try:
        if use_device_detection:
            config_first_detected_device(board_num, dev_id_list)

        daq_dev_info = DaqDeviceInfo(board_num)
        if not daq_dev_info.supports_analog_input:
            raise Exception('Error: The DAQ device does not support '
                            'analog input')

        print('\nActive DAQ device: ', daq_dev_info.product_name, ' (',
              daq_dev_info.unique_id, ')\n', sep='')

        ai_info = daq_dev_info.get_ai_info()

        low_chan = 0
        high_chan = min(3, ai_info.num_chans - 1)
        num_chans = high_chan - low_chan + 1

        total_count = points_per_channel * num_chans

        ai_range = ai_info.supported_ranges[0]

        scan_options = ScanOptions.BACKGROUND

        if ScanOptions.SCALEDATA in ai_info.supported_scan_options:
            # If the hardware supports the SCALEDATA option, it is easiest to
            # use it.
            scan_options |= ScanOptions.SCALEDATA

            memhandle = ul.scaled_win_buf_alloc(total_count)
            # Convert the memhandle to a ctypes array.
            ctypes_array = cast(memhandle, POINTER(c_double))
        elif ai_info.resolution <= 16:
            # Use the win_buf_alloc method for devices with a resolution <= 16
            memhandle = ul.win_buf_alloc(total_count)
            # Convert the memhandle to a ctypes array.
            ctypes_array = cast(memhandle, POINTER(c_ushort))
        else:
            # Use the win_buf_alloc_32 method for devices with a resolution > 16
            memhandle = ul.win_buf_alloc_32(total_count)
            # Convert the memhandle to a ctypes array.
            ctypes_array = cast(memhandle, POINTER(c_ulong))

        # Note: the ctypes array will no longer be valid after win_buf_free is
        # called.
        # A copy of the buffer can be created using win_buf_to_array or
        # win_buf_to_array_32 before the memory is freed. The copy can be used
        # at any time.

        # Check if the buffer was successfully allocated
        if not memhandle:
            raise Exception('Error: Failed to allocate memory')

        # Start the scan
        ul.a_in_scan(
            board_num, low_chan, high_chan, total_count,
            rate, ai_range, memhandle, scan_options)

        # Create a format string that aligns the data in columns
        row_format = '{:>12}' * num_chans

        # Print the channel name headers
        labels = []
        for ch_num in range(low_chan, high_chan + 1):
            labels.append('CH' + str(ch_num))
        print(row_format.format(*labels))

        # Start updating the displayed values
        status, curr_count, curr_index = ul.get_status(
            board_num, FunctionType.AIFUNCTION)
        while status != Status.IDLE:
            # Make sure a data point is available for display.
            if curr_count > 0:
                # curr_index points to the start of the last completed
                # channel scan that was transferred between the board and
                # the data buffer. Display the latest value for each
                # channel.
                display_data = []
                for data_index in range(curr_index, curr_index + num_chans):
                    if ScanOptions.SCALEDATA in scan_options:
                        # If the SCALEDATA ScanOption was used, the values
                        # in the array are already in engineering units.
                        eng_value = ctypes_array[data_index]
                    else:
                        # If the SCALEDATA ScanOption was NOT used, the
                        # values in the array must be converted to
                        # engineering units using ul.to_eng_units().
                        eng_value = ul.to_eng_units(board_num, ai_range,
                                                    ctypes_array[data_index])
                    display_data.append('{:.3f}'.format(eng_value))
                print(row_format.format(*display_data))

            # Wait a while before adding more values to the display.
            sleep(0.5)

            status, curr_count, curr_index = ul.get_status(
                board_num, FunctionType.AIFUNCTION)

        # Stop the background operation (this is required even if the
        # scan completes successfully)
        ul.stop_background(board_num, FunctionType.AIFUNCTION)

        print('Scan completed successfully')
    except Exception as e:
        print('\n', e)
    finally:
        if memhandle:
            # Free the buffer in a finally block to prevent a memory leak.
            ul.win_buf_free(memhandle)
        if use_device_detection:
            ul.release_daq_device(board_num)

def analog_input(_board_num, _channel, _ai_range, limit):
    # use_device_detection = True
    # dev_id_list = []
    # board_num = 0

    try:
        # if use_device_detection:
        #     config_first_detected_device(board_num, dev_id_list)

        daq_dev_info = DaqDeviceInfo(_board_num)
        if not daq_dev_info.supports_analog_input:
            raise Exception('Error: The DAQ device does not support '
                            'analog input')

        print('\nActive DAQ device: ', daq_dev_info.product_name, ' (',
              daq_dev_info.unique_id, ')\n', sep='')

        ai_info = daq_dev_info.get_ai_info()
        ai_range = ai_info.supported_ranges[0]
        channel = 0


        loop = 0
        while(loop < limit):

            # Get a value from the device
            if ai_info.resolution <= 16:
                xs.append(loop) # current time
                # Use the a_in method for devices with a resolution <= 16
                value = ul.a_in(_board_num, _channel, _ai_range)
                # Convert the raw value to engineering units
                eng_units_value = ul.to_eng_units(_board_num, _ai_range, value)
                ys.append(eng_units_value)
            else:
                # Use the a_in_32 method for devices with a resolution > 16
                # (optional parameter omitted)
                value = ul.a_in_32(_board_num, _channel, _ai_range)
                # Convert the raw value to engineering units
                eng_units_value = ul.to_eng_units_32(_board_num, _ai_range, value)

            # Display the raw value
            # print('Raw Value:', value)
            # Display the engineering value
            # print('Analog ' + str(_channel) + ' Volts: {:.7f}'.format(eng_units_value))
            loop+=1
    except Exception as e:
        print('\n', e)
    finally:
        # Format plot
        plt.xticks(rotation=45, ha='right')
        plt.subplots_adjust(bottom=0.30)
        plt.title('TMP102 Temperature over Time')
        plt.ylabel('Temperature (deg C)')
        #     # Draw x and y lists
        ax.clear()
        ax.plot(xs, ys)
        

        ul.release_daq_device(_board_num)
        # if use_device_detection:
        #     ul.release_daq_device(_board_num)
    
# run main function on program start
if __name__ == '__main__':
    config_first_detected_device(1)
    # print("start")
    # multi_analog_input(0)
    # ul.a_in_scan(1)


#[V]
    #Filtered Value = y_lfilter

fs = 100  # sampling rate, Hz
# define lowpass filter with 2.5 Hz cutoff frequency
b, a = scipy.signal.iirfilter(4, Wn=1.0, fs=fs, btype="low", ftype="butter")
print(b, a, sep="\n")
y_lfilter = scipy.signal.lfilter(b, a, ys)

plt.figure(figsize=[6.4, 2.4])
plt.plot(xs, ys, label="Raw signal")
plt.plot(xs, y_lfilter, alpha=0.8, lw=3, label="SciPy lfilter")

# Print Filtered Value
for i in y_lfilter:
    print(i)
# End Printing
    
plt.xlabel("Time / s")
plt.ylabel("Amplitude")
plt.legend(loc="lower center", bbox_to_anchor=[0.5, 1], ncol=2,
           fontsize="smaller")

plt.tight_layout()
plt.show()
