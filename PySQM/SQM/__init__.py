from PySQM.SQM.Plot import Plot
from PySQM.SQM.Common import define_ephem_observatory
from PySQM.SQM.Device import SQMLU, SQMLE

from os import times
from datetime import datetime, time
import os
from .ConfigFile import ConfigFile

GlobalConfig = ConfigFile()

# ! GlobalConfig.read_config_file(arguments['config'])

config = GlobalConfig.config
# If the old format (SQM_LE/SQM_LU) is used, replace _ with -
config._device_type = config._device_type.replace('_', '-')

if config._device_type == 'SQM-LE':
    import socket
elif config._device_type == 'SQM-LU':
    import serial
if config._use_mysql == True:
    import mysql
# Create directories if needed

for directory in [config.monthly_data_directory, config.daily_data_directory, config.current_data_directory]:
    if not os.path.exists(directory):
        os.makedirs(directory)


'''
Select the device to be used based on user input
and start the measures
'''

if config._device_type == 'SQM-LU':
    mydevice = SQMLU()
elif config._device_type == 'SQM-LE':
    mydevice = SQMLE()
else:
    print(('ERROR. Unknown device type '+str(config._device_type)))
    exit(0)


def loop():
    '''
    Ephem is used to calculate moon position (if above horizon)
    and to determine start-end times of the measures
    '''
    observ = define_ephem_observatory()
    niter = 0
    DaytimePrint = True
    print('Starting readings ...')
    while 1 < 2:
        ''' The programs works as a daemon '''
        utcdt = mydevice.read_datetime()
        #print (str(mydevice.local_datetime(utcdt))),
        if mydevice.is_nighttime(observ):
            # If we are in a new night, create the new file.
            config._send_to_datacenter = False  # Not enabled by default
            try:
                assert(config._send_to_datacenter == True)
                assert(niter == 0)
                mydevice.save_data_datacenter("NEWFILE")
            except:
                pass

            StartDateTime = datetime.now()
            niter += 1

            mydevice.define_filenames()

            ''' Get values from the photometer '''
            try:
                timeutc_mean, timelocal_mean, temp_sensor,\
                    freq_sensor, ticks_uC, sky_brightness = \
                    mydevice.read_photometer(
                        Nmeasures=config._measures_to_promediate, PauseMeasures=10)
            except:
                print('Connection lost')
                if config._reboot_on_connlost == True:
                    sleep(600)
                    os.system('reboot.bat')

                time.sleep(1)
                mydevice.reset_device()

            formatted_data = mydevice.format_content(
                timeutc_mean, timelocal_mean, temp_sensor, freq_sensor, ticks_uC, sky_brightness)

            try:
                assert(config._use_mysql == True)
                mydevice.save_data_mysql(formatted_data)
            except:
                pass

            try:
                assert(config._send_to_datacenter == True)
                mydevice.save_data_datacenter(formatted_data)
            except:
                pass

            mydevice.data_cache(
                formatted_data, number_measures=config._cache_measures, niter=niter)

            if niter % config._plot_each == 0:
                ''' Each X minutes, plot a new graph '''
                try:
                    Plot.make_plot(send_emails=False, write_stats=False)
                except:
                    print('Warning: Error plotting data.')
                    print((exc_info()))

            if DaytimePrint == False:
                DaytimePrint = True

            MainDeltaSeconds = (datetime.datetime.now() -
                                StartDateTime).total_seconds()
            time.sleep(max(1, config._delay_between_measures-MainDeltaSeconds))

        else:
            ''' Daytime, print info '''
            if DaytimePrint == True:
                utcdt = utcdt.strftime("%Y-%m-%d %H:%M:%S")
                print((utcdt), end=' ')
                print(('. Daytime. Waiting until ' +
                       str(mydevice.next_sunset(observ))))
                DaytimePrint = False
            if niter > 0:
                mydevice.flush_cache()
                if config._send_data_by_email == True:
                    try:
                        plot.make_plot(
                            send_emails=True, write_stats=True)
                    except:
                        print('Warning: Error plotting data / sending email.')
                        print((sys.exc_info()))

                else:
                    try:
                        plot.make_plot(
                            send_emails=False, write_stats=True)
                    except:
                        print('Warning: Error plotting data.')
                        print((sys.exc_info()))

                niter = 0

            # Send data that is still in the datacenter buffer
            try:
                assert(config._send_to_datacenter == True)
                mydevice.save_data_datacenter("")
            except:
                pass

            times.sleep(300)
