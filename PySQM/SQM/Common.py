

'''
Read configuration
'''
config = GlobalConfig.config



'''
This import section is only for software build purposes.
Dont worry if some of these are missing in your setup.
'''
def relaxed_import(themodule):
    try: exec('import '+str(themodule))
    except: pass

relaxed_import('serial')
relaxed_import('_mysql')
relaxed_import('pysqm.email')


try:
    DEBUG=config.DEBUG
except:
    DEBUG=False

'''
Conditional imports
'''

# If the old format (SQM_LE/SQM_LU) is used, replace _ with -
config._device_type = config._device_type.replace('_','-')

if config._device_type == 'SQM-LE':
    import socket
elif config._device_type == 'SQM-LU':
    import serial
if config._use_mysql == True:
    import mysql


def filtered_mean(array,sigma=3):
    # Our data probably contains outliers, filter them
    # Notes:
    #   Median is more robust than mean
    #    Std increases if the outliers are far away from real values.
    #    We need to limit the amount of discrepancy we want in the data (20%?).

    # We will use data masking and some operations with arrays. Convert to numpy.
    array = np.array(array)

    # Get the median and std.
    data_median = np.median(array)
    data_std    = np.std(array)

    # Max discrepancy we allow.
    fixed_max_dev  = 0.2*data_median
    clip_deviation = np.min([fixed_max_dev,data_std*sigma+0.1])

    # Create the filter (10% flux + variable factor)
    filter_values_ok = np.abs(array-data_median)<=clip_deviation
    filtered_values = array[filter_values_ok]

    # Return the mean of filtered data or the median.
    if np.size(filtered_values)==0:
        print('Warning: High dispersion found on last measures')
        filtered_mean = data_median
    else:
        filtered_mean = np.mean(filtered_values)

    return(filtered_mean)


def define_ephem_observatory():
    ''' Define the Observatory in Pyephem '''
    OBS = ephem.Observer()
    OBS.lat = config._observatory_latitude*ephem.pi/180
    OBS.lon = config._observatory_longitude*ephem.pi/180
    OBS.elev = config._observatory_altitude
    return(OBS)

def remove_linebreaks(data):
    # Remove line breaks from data
    data = data.replace('\r\n','')
    data = data.replace('\r','')
    data = data.replace('\n','')
    return(data)

def format_value(data,remove_str=' '):
    # Remove string and spaces from data
    data = remove_linebreaks(data)
    data = data.replace(remove_str,'')
    data = data.replace(' ','')
    return(data)

def format_value_list(data,remove_str=' '):
    # Remove string and spaces from data array/list
    data = [format_value(line,remove_str).split(';') for line in data]
    return(data)

def set_decimals(number,dec=3):
        str_number = str(number)
        int_,dec_ = str_number.split('.')
        while len(dec_)<=dec:
            dec_=dec_+'0'

        return(int_+'.'+dec_[:dec])
