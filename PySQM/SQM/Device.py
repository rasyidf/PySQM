import os

from .Common import *

class observatory(object):
    def read_datetime(self):
        # Get UTC datetime from the computer.
        utc_dt = datetime.datetime.utcnow()
        #utc_dt = datetime.datetime.now() - datetime.timedelta(hours=config._computer_timezone)
                #time.localtime(); daylight_saving=_.tm_isdst>0
        return(utc_dt)

    def local_datetime(self,utc_dt):
        # Get Local datetime from the computer, without daylight saving.
        return(utc_dt + datetime.timedelta(hours=config._local_timezone))

    def calculate_sun_altitude(self,OBS,timeutc):
        # Calculate Sun altitude
        OBS.date = ephem.date(timeutc)
        Sun = ephem.Sun(OBS)
        return(Sun.alt)

    def next_sunset(self,OBS):
        # Next sunset calculation
        previous_horizon = OBS.horizon
        OBS.horizon = str(config._observatory_horizon)
        next_setting = OBS.next_setting(ephem.Sun()).datetime()
        next_setting = next_setting.strftime("%Y-%m-%d %H:%M:%S")
        OBS.horizon = previous_horizon
        return(next_setting)

    def is_nighttime(self,OBS):
        # Is nightime (sun below a given altitude)
        timeutc = self.read_datetime()
        if self.calculate_sun_altitude(OBS,timeutc)*180./math.pi>config._observatory_horizon:
            return False
        else:
            return True

class device(observatory):
    def standard_file_header(self):
        # Data Header, at the end of this script.
        header_content=RAWHeaderContent

        # Update data file header with observatory data
        header_content = header_content.replace(\
         '$DEVICE_TYPE',str(config._device_type))
        header_content = header_content.replace(\
         '$DEVICE_ID',str(config._device_id))
        header_content = header_content.replace(\
         '$DATA_SUPPLIER',str(config._data_supplier))
        header_content = header_content.replace(\
         '$LOCATION_NAME',str(config._device_locationname))
        header_content = header_content.replace(\
         '$OBSLAT',str(config._observatory_latitude))
        header_content = header_content.replace(\
         '$OBSLON',str(config._observatory_longitude))
        header_content = header_content.replace(\
         '$OBSALT',str(config._observatory_altitude))
        header_content = header_content.replace(\
         '$OFFSET',str(config._offset_calibration))

        if config._local_timezone==0:
            header_content = header_content.replace(\
             '$TIMEZONE','UTC')
        elif config._local_timezone>0:
            header_content = header_content.replace(\
             '$TIMEZONE','UTC+'+str(config._local_timezone))
        elif config._local_timezone<0:
            header_content = header_content.replace(\
             '$TIMEZONE','UTC'+str(config._local_timezone))

        header_content = header_content.replace(\
         '$PROTOCOL_NUMBER',str(self.protocol_number))
        header_content = header_content.replace(\
         '$MODEL_NUMBER', str(self.model_number))
        header_content = header_content.replace(\
         '$FEATURE_NUMBER', str(self.feature_number))
        header_content = header_content.replace(\
         '$SERIAL_NUMBER', str(self.serial_number))

        header_content = header_content.replace(\
         '$IXREADOUT', remove_linebreaks(self.ix_readout))
        header_content = header_content.replace(\
         '$RXREADOUT', remove_linebreaks(self.rx_readout))
        header_content = header_content.replace(\
         '$CXREADOUT', remove_linebreaks(self.cx_readout))

        return(header_content)

    def format_content(self,timeutc_mean,timelocal_mean,temp_sensor,\
     freq_sensor,ticks_uC,sky_brightness):
        # Format a string with data
        date_time_utc_str   = str(\
         timeutc_mean.strftime("%Y-%m-%dT%H:%M:%S"))+'.000'
        date_time_local_str = str(\
         timelocal_mean.strftime("%Y-%m-%dT%H:%M:%S"))+'.000'
        temp_sensor_str     = str('%.2f' %temp_sensor)
        ticks_uC_str        = str('%.3f' %ticks_uC)
        freq_sensor_str     = str('%.3f' %freq_sensor)
        sky_brightness_str  = str('%.3f' %sky_brightness)

        formatted_data = \
          date_time_utc_str+";"+date_time_local_str+";"+temp_sensor_str+";"+\
          ticks_uC_str+";"+freq_sensor_str+";"+sky_brightness_str+"\n"

        return(formatted_data)

    def define_filenames(self):
        # Filenames should follow a standard based on observatory name and date.
        date_time_file = self.local_datetime(\
         self.read_datetime())-datetime.timedelta(hours=12)
        date_file = date_time_file.date()
        yearmonth = str(date_file)[0:7]
        yearmonthday = str(date_file)[0:10]

        self.monthly_datafile = \
         config.monthly_data_directory+"/"+config._device_shorttype+\
         "_"+config._observatory_name+"_"+yearmonth+".dat"
        #self.daily_datafile = \
        # config.daily_data_directory+"/"+config._device_shorttype+\
        # "_"+config._observatory_name+"_"+yearmonthday+".dat"
        self.daily_datafile = \
         config.daily_data_directory+"/"+\
         yearmonthday.replace('-','')+'_120000_'+\
         config._device_shorttype+'-'+config._observatory_name+'.dat'
        self.current_datafile = \
         config.current_data_directory+"/"+config._device_shorttype+\
         "_"+config._observatory_name+".dat"

    def save_data(self,formatted_data):
        '''
        Save data to file and duplicate to current
        data file (the one that will be ploted)
        '''
        for each_file in [self.monthly_datafile,self.daily_datafile]:
            if not os.path.exists(each_file):
                datafile = open(each_file,'w')
                datafile.write(self.standard_file_header())
                datafile.close()

            datafile = open(each_file,'a+')
            datafile.write(formatted_data)
            datafile.close()

        self.copy_file(self.daily_datafile,self.current_datafile)


    def save_data_datacenter(self,formatted_data):
        '''
        This function sends the data from this pysqm client to the central
        node @ UCM. It saves the data there (only the SQM data file contents)
        '''

        # Connection details (hardcoded to avoid user changes)
        DC_HOST = "muon.gae.ucm.es"
        DC_PORT = 8739
        DEV_ID = str(config._device_id)+"_"+str(self.serial_number)

        def send_data(data):
            try:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect((DC_HOST, DC_PORT))
                client.sendall(data)
                client.shutdown(socket.SHUT_RDWR)
                client.close()
            except:
                return(0)
            else:
                return(1)

        def write_buffer():
            for data_line in self.DataBuffer[:]:
                success = send_data(DEV_ID+";;D;;"+data_line)
                if (success==1): self.DataBuffer.remove(data_line)

            return(success)

        '''
        Send the new file initialization to the datacenter
        Appends the header to the buffer (it will be sent later)
        '''

        if (formatted_data=="NEWFILE"):
            self.DataBuffer=[\
                hl+"\n" for hl in self.standard_file_header().split("\n")[:-1]]

            # Try to connect with the datacenter and send the header
            success = send_data(DEV_ID+";;C;;")
            success = write_buffer()
            return(success)
        else:

            '''
            Send the data to the datacenter
            '''

            # If the buffer is full, dont append more data.
            if (len(self.DataBuffer)<10000):
                self.DataBuffer.append(formatted_data)

            # Try to connect with the datacenter and send the data
            success = write_buffer()
            return(success)

    def save_data_mysql(self,formatted_data):
        '''
        Use the Python MySQL API to save the
        data to a database
        '''
        mydb = None
        values = formatted_data.split(';')
        try:
            ''' Start database connection '''
            mydb = _mysql.connect(\
             host = config._mysql_host,
             user = config._mysql_user,
             passwd = config._mysql_pass,
             db = config._mysql_database,
             port = config._mysql_port)

            ''' Insert the data '''
            mydb.query(\
             "INSERT INTO "+str(config._mysql_dbtable)+" VALUES (NULL,'"+\
             values[0]+"','"+values[1]+"',"+\
             values[2]+","+values[3]+","+\
             values[4]+","+values[5]+")")
        except Exception as ex:
            print((str(inspect.stack()[0][2:4][::-1])+\
             ' DB Error. Exception: %s' % str(ex)))

        if mydb != None:
            mydb.close()

    def data_cache(self,formatted_data,number_measures=1,niter=0):
        '''
        Append data to DataCache str.
        If len(data)>number_measures, write to file
        and flush the cache
        '''
        try:
            self.DataCache
        except:
            self.DataCache=""

        self.DataCache = self.DataCache+formatted_data

        if len(self.DataCache.split("\n"))>=number_measures+1:
            self.save_data(self.DataCache)
            self.DataCache = ""
            print((str(niter)+'\t'+formatted_data[:-1]))

    def flush_cache(self):
        ''' Flush the data cache '''
        self.save_data(self.DataCache)
        self.DataCache = ""

    def copy_file(self,source,destination):
        # Copy file content from source to dest.
        fichero_source = open(source,'r')
        contenido_source = fichero_source.read()
        fichero_source.close()
        # Create file and truncate it
        fichero_destination = open(destination,'w')
        fichero_destination.close()
        # Write content
        fichero_destination = open(destination,'r+')
        fichero_destination.write(contenido_source)
        fichero_destination.close()

    def remove_currentfile(self):
        # Remove a file from the host
        if os.path.exists(self.current_datafile):
            os.remove(self.current_datafile)

class SQM(device):
    def read_photometer(self,Nmeasures=1,PauseMeasures=2):
        # Initialize values
        temp_sensor   = []
        flux_sensor   = []
        freq_sensor   = []
        ticks_uC      = []
        Nremaining = Nmeasures

        # Promediate N measures to remove jitter
        timeutc_initial = self.read_datetime()
        while(Nremaining>0):
            InitialDateTime = datetime.datetime.now()

            # Get the raw data from the photometer and process it.
            raw_data = self.read_data(tries=10)
            temp_sensor_i,freq_sensor_i,ticks_uC_i,sky_brightness_i = \
             self.data_process(raw_data)

            temp_sensor += [temp_sensor_i]
            freq_sensor += [freq_sensor_i]
            ticks_uC    += [ticks_uC_i]
            flux_sensor += [10**(-0.4*sky_brightness_i)]
            Nremaining  -= 1
            DeltaSeconds = (datetime.datetime.now()-InitialDateTime).total_seconds()

            # Just to show on screen that the program is alive and running
            sys.stdout.write('.')
            sys.stdout.flush()

            if (Nremaining>0): time.sleep(max(1,PauseMeasures-DeltaSeconds))

        timeutc_final = self.read_datetime()
        timeutc_delta = timeutc_final - timeutc_initial

        timeutc_mean   = timeutc_initial+\
         datetime.timedelta(seconds=int(timeutc_delta.seconds/2.+0.5))
        timelocal_mean = self.local_datetime(timeutc_mean)

        # Calculate the mean of the data.
        temp_sensor = filtered_mean(temp_sensor)
        freq_sensor = filtered_mean(freq_sensor)
        flux_sensor = filtered_mean(flux_sensor)
        ticks_uC    = filtered_mean(ticks_uC)
        sky_brightness = -2.5*np.log10(flux_sensor)

        # Correct from offset (if cover is installed on the photometer)
        #sky_brightness = sky_brightness+config._offset_calibration

        return(\
         timeutc_mean,timelocal_mean,\
         temp_sensor,freq_sensor,\
         ticks_uC,sky_brightness)

    def metadata_process(self,msg,sep=','):
        # Separate the output array in items
        msg = format_value(msg)
        msg_array = msg.split(sep)

        # Get Photometer identification codes
        self.protocol_number = int(format_value(msg_array[1]))
        self.model_number    = int(format_value(msg_array[2]))
        self.feature_number  = int(format_value(msg_array[3]))
        self.serial_number   = int(format_value(msg_array[4]))

    def data_process(self,msg,sep=','):
        # Separate the output array in items
        msg = format_value(msg)
        msg_array = msg.split(sep)

        # Output definition characters
        mag_char  = 'm'
        freq_char = 'Hz'
        perc_char = 'c'
        pers_char = 's'
        temp_char = 'C'

        # Get the measures
        sky_brightness = float(format_value(msg_array[1],mag_char))
        freq_sensor    = float(format_value(msg_array[2],freq_char))
        ticks_uC       = float(format_value(msg_array[3],perc_char))
        period_sensor  = float(format_value(msg_array[4],pers_char))
        temp_sensor    = float(format_value(msg_array[5],temp_char))

        # For low frequencies, use the period instead
        if freq_sensor<30 and period_sensor>0:
            freq_sensor = 1./period_sensor

        return(temp_sensor,freq_sensor,ticks_uC,sky_brightness)

    def start_connection(self):
        ''' Start photometer connection '''
        pass

    def close_connection(self):
        ''' End photometer connection '''
        pass

    def reset_device(self):
        ''' Restart connection'''
        self.close_connection()
        time.sleep(0.1)
        #self.__init__()
        self.start_connection()

class SQMLE(SQM):
    def __init__(self):
        '''
        Search the photometer in the network and
        read its metadata
        '''

        try:
            print(('Trying fixed device address %s ... ' %str(config._device_addr)))
            self.addr = config._device_addr
            self.port = 10001
            self.start_connection()
        except:
            print('Trying auto device address ...')
            self.addr = self.search()
            print(('Found address %s ... ' %str(self.addr)))
            self.port = 10001
            self.start_connection()

        # Clearing buffer
        print(('Clearing buffer ... |'), end=' ')
        buffer_data = self.read_buffer()
        print((buffer_data), end=' ')
        print('| ... DONE')
        print('Reading test data (ix,cx,rx)...')
        time.sleep(1)
        self.ix_readout = self.read_metadata(tries=10)
        time.sleep(1)
        self.cx_readout = self.read_calibration(tries=10)
        time.sleep(1)
        self.rx_readout = self.read_data(tries=10)

    def search(self):
        ''' Search SQM LE in the LAN. Return its adress '''
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setblocking(False)

        if hasattr(socket,'SO_BROADCAST'):
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.s.sendto("000000f6".decode("hex"), ("255.255.255.255", 30718))
        buf=''
        starttime = time.time()

        print("Looking for replies; press Ctrl-C to stop.")
        addr=[None,None]
        while True:
            try:
                (buf, addr) = self.s.recvfrom(30)
                if buf[3].encode("hex")=="f7":
                    print("Received from %s: MAC: %s" % \
                     (addr, buf[24:30].encode("hex")))
            except:
                #Timeout in seconds. Allow all devices time to respond
                if time.time()-starttime > 3:
                    break
                pass

        try:
            assert(addr[0]!=None)
        except:
            print('ERR. Device not found!')
            raise
        else:
            return(addr[0])

    def start_connection(self):
        ''' Start photometer connection '''
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(20)
        self.s.connect((self.addr,int(self.port)))
        #self.s.settimeout(1)

    def close_connection(self):
        ''' End photometer connection '''
        self.s.setsockopt(\
         socket.SOL_SOCKET,\
         socket.SO_LINGER,\
         struct.pack('ii', 1, 0))

        # Check until there is no answer from device
        request = ""
        r = True
        while r:
            r = self.read_buffer()
            request += str(r)
        self.s.close()

    def read_buffer(self):
        ''' Read the data '''
        msg = None
        try: msg = self.s.recv(256)
        except: pass
        return(msg)

    def reset_device(self):
        ''' Connection reset '''
        #print('Trying to reset connection')
        self.close_connection()
        self.start_connection()

    def read_metadata(self,tries=1):
        ''' Read the serial number, firmware version '''
        self.s.send('ix')
        time.sleep(1)

        read_err = False
        msg = self.read_buffer()

        # Check metadata
        try:
            # Sanity check
            assert(len(msg)==_meta_len_ or _meta_len_==None)
            assert("i," in msg)
            self.metadata_process(msg)
        except:
            tries-=1
            read_err=True

        if (read_err==True and tries>0):
            time.sleep(1)
            self.reset_device()
            time.sleep(1)
            msg = self.read_metadata(tries)
            if (msg!=-1): read_err=False

        # Check that msg contains data
        if read_err==True:
            print(('ERR. Reading the photometer!: %s' %str(msg)))
            if (DEBUG): raise
            return(-1)
        else:
            print(('Sensor info: '+str(msg)), end=' ')
            return(msg)

    def read_calibration(self,tries=1):
        ''' Read the calibration parameters '''
        self.s.send('cx')
        time.sleep(1)

        read_err = False
        msg = self.read_buffer()

        # Check caldata
        try:
            # Sanity check
            assert(len(msg)==_cal_len_ or _cal_len_==None)
            assert("c," in msg)
        except:
            tries-=1
            read_err=True

        if (read_err==True and tries>0):
            time.sleep(1)
            self.reset_device()
            time.sleep(1)
            msg = self.read_calibration(tries)
            if (msg!=-1): read_err=False

        # Check that msg contains data
        if read_err==True:
            print(('ERR. Reading the photometer!: %s' %str(msg)))
            if (DEBUG): raise
            return(-1)
        else:
            print(('Calibration info: '+str(msg)), end=' ')
            return(msg)

    def read_data(self,tries=1):
        ''' Read the SQM and format the Temperature, Frequency and NSB measures '''
        self.s.send('rx')
        time.sleep(1)

        read_err = False
        msg = self.read_buffer()

        # Check data
        try:
            # Sanity check
            assert(len(msg)==_data_len_ or _data_len_==None)
            assert("r," in msg)
            self.data_process(msg)
        except:
            tries-=1
            read_err=True

        if (read_err==True and tries>0):
            time.sleep(1)
            self.reset_device()
            time.sleep(1)
            msg = self.read_data(tries)
            if (msg!=-1): read_err=False

        # Check that msg contains data
        if read_err==True:
            print(('ERR. Reading the photometer!: %s' %str(msg)))
            if (DEBUG): raise
            return(-1)
        else:
            if (DEBUG): print(('Data msg: '+str(msg)))
            return(msg)

class SQMLU(SQM):
    def __init__(self):
        '''
        Search the photometer and
        read its metadata
        '''

        try:
            print(('Trying fixed device address %s ... ' %str(config._device_addr)))
            self.addr = config._device_addr
            self.bauds = 115200
            self.start_connection()
        except:
            print('Trying auto device address ...')
            self.addr = self.search()
            print(('Found address %s ... ' %str(self.addr)))
            self.bauds = 115200
            self.start_connection()

        # Clearing buffer
        print(('Clearing buffer ... |'), end=' ')
        buffer_data = self.read_buffer()
        print((buffer_data), end=' ')
        print('| ... DONE')
        print('Reading test data (ix,cx,rx)...')
        time.sleep(1)
        self.ix_readout = self.read_metadata(tries=10)
        time.sleep(1)
        self.cx_readout = self.read_calibration(tries=10)
        time.sleep(1)
        self.rx_readout = self.read_data(tries=10)


    def search(self):
        '''
        Photometer search.
        Name of the port depends on the platform.
        '''
        ports_unix = ['/dev/ttyUSB'+str(num) for num in range(100)]
        ports_win  = ['COM'+str(num) for num in range(100)]

        os_in_use = sys.platform

        if os_in_use == 'linux2':
            print('Detected Linux platform')
            ports = ports_unix
        elif os_in_use == 'win32':
            print('Detected Windows platform')
            ports = ports_win

        used_port = None
        for port in ports:
            conn_test = serial.Serial(port, 115200, timeout=1)
            conn_test.write('ix')
            if conn_test.readline()[0] == 'i':
                used_port = port
                break

        try:
            assert(used_port!=None)
        except:
            print('ERR. Device not found!')
            raise
        else:
            return(used_port)

    def start_connection(self):
        '''Start photometer connection '''

        self.s = serial.Serial(self.addr, 115200, timeout=2)

    def close_connection(self):
        ''' End photometer connection '''
        # Check until there is no answer from device
        request = ""
        r = True
        while r:
            r = self.read_buffer()
            request += str(r)

        self.s.close()

    def reset_device(self):
        ''' Connection reset '''
        #print('Trying to reset connection')
        self.close_connection()
        self.start_connection()

    def read_buffer(self):
        ''' Read the data '''
        msg = None
        try: msg = self.s.readline()
        except: pass
        return(msg)

    def read_metadata(self,tries=1):
        ''' Read the serial number, firmware version '''
        self.s.write('ix')
        time.sleep(1)

        read_err = False
        msg = self.read_buffer()

        # Check metadata
        try:
            # Sanity check
            assert(len(msg)==_meta_len_ or _meta_len_==None)
            assert("i," in msg)
            self.metadata_process(msg)
        except:
            tries-=1
            read_err=True

        if (read_err==True and tries>0):
            time.sleep(1)
            self.reset_device()
            time.sleep(1)
            msg = self.read_metadata(tries)
            if (msg!=-1): read_err=False

        # Check that msg contains data
        if read_err==True:
            print(('ERR. Reading the photometer!: %s' %str(msg)))
            if (DEBUG): raise
            return(-1)
        else:
            print(('Sensor info: '+str(msg)), end=' ')
            return(msg)

    def read_calibration(self,tries=1):
        ''' Read the calibration data '''
        self.s.write('cx')
        time.sleep(1)

        read_err = False
        msg = self.read_buffer()

        # Check caldata
        try:
            # Sanity check
            assert(len(msg)==_cal_len_ or _cal_len_==None)
            assert("c," in msg)
        except:
            tries-=1
            read_err=True

        if (read_err==True and tries>0):
            time.sleep(1)
            self.reset_device()
            time.sleep(1)
            msg = self.read_calibration(tries)
            if (msg!=-1): read_err=False

        # Check that msg contains data
        if read_err==True:
            print(('ERR. Reading the photometer!: %s' %str(msg)))
            if (DEBUG): raise
            return(-1)
        else:
            print(('Calibration info: '+str(msg)), end=' ')
            return(msg)

    def read_data(self,tries=1):
        ''' Read the SQM and format the Temperature, Frequency and NSB measures '''
        self.s.write('rx')
        time.sleep(1)

        read_err = False
        msg = self.read_buffer()

        # Check data
        try:
            # Sanity check
            assert(len(msg)==_data_len_ or _data_len_==None)
            assert("r," in msg)
            self.data_process(msg)
        except:
            tries-=1
            read_err=True

        if (read_err==True and tries>0):
            time.sleep(1)
            self.reset_device()
            time.sleep(1)
            msg = self.read_data(tries)
            if (msg!=-1): read_err=False

        # Check that msg contains data
        if read_err==True:
            print(('ERR. Reading the photometer!: %s' %str(msg)))
            if (DEBUG): raise
            return(-1)
        else:
            if (DEBUG): print(('Data msg: '+str(msg)))
            return(msg)

