"""****************************Imports****************************"""
import numpy as np; import time; import socket; import serial
from  tpu_sensing.keithley_connect import *; from tpu_sensing.keithley_setup import *
from time import perf_counter_ns; import os.path


def DeviceConnect():
    # define the instrament's IP address. the port is always 5025 for LAN connection.
    ip_address = "169.254.253.110"
    my_port = 5025

    # establish connection to the LAN socket. initialize and connect to the Keithley
    s = socket.socket() # Establish a TCP/IP socket object
    InstrumentConnect(s, ip_address, my_port, 10000)

    # connect to the 3d printer
    ser = serial.Serial('COM3', 250000, timeout = 1)
    time.sleep(1)
    return s, ser


def PrintCommand(ser, command):
  # encode text to ascii
  ser.write(str.encode(command)) 

  # check for the final read out
  while True:
    line = ser.readline()
    if line == b'ok\n' or line == b'ok \n' or line == b'':
      break


def Homing(s, ser):
    # home the linear actuator
    PrintCommand(ser,'G90 \n') # set absolute position
    PrintCommand(ser,'G1 Z5\n') # move the linear actuator up
    print('\n\nClear the glass plate and remove anode to home the linear actuator')
    time.sleep(2)
    input('Press enter when finished\n')
    print('Homing\n')
    PrintCommand(ser, 'G28 Z \n') # home the linear actuator
    
    # move the actuator up and set the Z-axis coordinates to zero
    PrintCommand(ser,'G1 Z15 \n') 
    input("Load test cell - press enter \n")
    PrintCommand(ser,'G1 Z4 \n') 
    input("Adjust sample - press enter \n")
    PrintCommand(ser,'G92 Z0 \n')
    return


def GelFinder(s, ser):
    # define the measurement channels
    KeithleySetup(s, '119')
    DcVoltSetup(s, '119')

    # initialize the starting position and a movement divisor.
    position = 0
    i = 1

    # begin data collection
    InstrumentWrite(s,"INIT")
    time.sleep(0.25)
    print('Position, Termination Criteria, Load cell')

    # make larger steps
    while True:
        bufferSize = int(InstrumentQuery(s, "TRACe:ACTual? \"Sensing\"", 16).rstrip())
        
        # let the buffer get to 100 data points. if the buffer isn't large enough, pass
        if bufferSize <= 100:
            pass    
        elif bufferSize > 100:
                # read the buffer value and the average
                time.sleep(0.025)
                buffer = float(InstrumentQuery(s, f"TRACe:DATA? {bufferSize}, {bufferSize}, \"Sensing\", READ", 16).split(',')[0])
                bufferAverage = float(InstrumentQuery(s, "TRACe:STATistics:AVERage? \"Sensing\"", 16))
                print(np.round(position, 3), np.round(bufferAverage, 6), buffer)
                
                # termination is when the load cell sees variance above the average. at termination, the actuator
                # moves back one step. future steps are cut in half. this is occurs two times before reaching zero. 
                if np.abs(bufferAverage - buffer) >= 0.00005:
                    position += 0.020
                    PrintCommand(ser,f'G1 Z{position} \n')
                    i += 1
                    if i == 3:
                        break
                else:
                    position -= 0.010/i
                    PrintCommand(ser,f'G1 Z{position} \n')

    # stop the instrument and set axis to zero
    print(' \n')
    PrintCommand(ser,'G92 Z0 \n')
    InstrumentWrite(s,"ABORT")


def Heater(t, ser):
    PrintCommand(ser, f'M140 S{t} \n')
    print('Heating... please wait\n')
    while True:
            # remove empty echos from the mother board
            line = ser.readline()
            if line == b'ok\n' or line == b'ok \n' or line == b'' or line == b' ':
                pass
            else:
                line = int(float(str(line, encoding = 'UTF-8').split(' ')[3].lstrip('B:')))
                if line == t:
                    print(f'{t}C Target temperature hit - wait 120 seconds\n')
                    time.sleep(120)
                    break


def Experiment(s, ser, stepSize, maxStrain, diameter, temperatureList, testTime):
    """***************Test parameters***************"""
    # input the gel type and its plasticizer content
    print('List the gel type and plasticizer content\n Ex: PVC P2')
    parameters = input('     ').upper()
    thickness = float(input("\nWhat's the gel thickness in mm (number only)?\n"))
    
       
    """***********************Motion materices***********************"""
    # define the total travel from max maximum strain. this rounds to the nearest stepSize
    totalTravel = np.round(maxStrain/100*thickness/stepSize)*stepSize # mm

    # preallocate gantry movement
    yMotion = np.around(np.concatenate([np.arange(0, -totalTravel, -stepSize), np.arange(-totalTravel, 0 + stepSize, stepSize)]), 2)
    yLength = len(yMotion)


    """***************Linear actuator home and temperature reading***************"""
    # home the linear actuator
    Homing(s, ser)

    # set the temperature and read from the motherboard every second. this is max temperature
    # collection resolution defined by the motherboard   
    PrintCommand(ser, 'M155 S1 \n')

    Data = np.zeros([0, 7])
    for t in temperatureList:
        # heat the bed to the target temp then find the gel
        # Heater(t, ser)    # uncomment to start using the heater
        GelFinder(s, ser)


        """***********************Data matrices***********************"""
        # initialize the inital buffer count, temperature readings, and data matrices
        bufferInitial = 0
        buffer = np.zeros(0)
        bufferTimes = np.zeros(0)
        temperatureReading = []
        position = np.zeros(0)

        """***********************Experiment***********************"""
        # list the channels used and initize the keithley. the you place these values is 
        # the order the columns will produce the excel sheet
        channels = '119, 120' # 119 - load cell, 120 - TPU sensor

        # setup the channels
        KeithleySetup(s, channels)
        numberOfChannels = len(channels.split(','))
        DcVoltSetup(s, channels)
    
        # begin data collection
        InstrumentWrite(s, "INIT")
        time.sleep(0.2)
        
        for x in range(0, yLength):
            # move the printer
            PrintCommand(ser, f'G1 Z{yMotion[x]} \n')
            print(f'Testing {yMotion[x]} mm at {t}C')

            # read temperature every second. use a while loop for experiment duration
            intialTime =  perf_counter_ns() # 
            while perf_counter_ns() < intialTime + testTime*10**9:
                # remove empty echos from the mother board
                line = ser.readline()
                if line == b'ok\n' or line == b'ok \n' or line == b'' or line == b' ':
                    pass
                else:
                    temperatureReading.append(float(str(line, encoding = 'UTF-8').split(' ')[3].lstrip('B:')))

            # stop the Keithley at an integer value of the data collected
            while True:
                bufferSize = int(InstrumentQuery(s, "TRACe:ACTual:END? \"Sensing\"", 16).rstrip())
                if bufferSize % numberOfChannels == 0:
                    # index the buffer the the inital position to the current position
                    points = np.ones(int((bufferSize - bufferInitial)/numberOfChannels))
                    position = np.hstack([position, yMotion[x]*points])
                    bufferInitial = bufferSize
                    print(f'Finished \n')
                    break
                else:
                    pass

        # stop the Keithley
        InstrumentWrite(s, "ABORT")

        # reset the initial position
        PrintCommand(ser,'G1 Z0.25\n')
        PrintCommand(ser,'G92 Z0\n')

        # collect the data from the buffer
        print('Reading buffer\n')
        for i in range(1, bufferInitial + 1):
            # read the measurements and their realtive times
            measurement = np.array(InstrumentQuery(s, f"TRACe:DATA? {i}, {i}, \"Sensing\", REL, READ", 16*bufferSize).split(','))
            bufferTimes = np.hstack([bufferTimes, float(measurement[0])])
            buffer = np.hstack([buffer, float(measurement[1])])
        bufferData = np.vstack([bufferTimes, buffer]).T.reshape(int(len(buffer)/numberOfChannels),2*numberOfChannels)
        
        # correlate the temperature times from the buffer to the temperature using floor using two
        # list comprehensions. the buffer time can be an index over the temperature reading. we limit this
        # and restric all the other measurements to accomdate this limit
        tempData = [temperatureReading[i] for i in [int(i) for i in bufferData[:, 0]] if i < len(temperatureReading)]
        tempDataLimit = len(tempData)
            
        # create the data export matrix. adjusst the final column for the loadcell 
        data = np.vstack([position[:tempDataLimit], position[:tempDataLimit]/thickness, tempData[:tempDataLimit], 
                          bufferData[:tempDataLimit, 0], bufferData[:tempDataLimit, 1],
                          bufferData[:tempDataLimit, 2], bufferData[:tempDataLimit, 3]]).T
        Data = np.vstack([Data, data])
        
    # apply the load cell resolution calibration with g converted to kg and diameter to area in m^2
    Data[:, -3] = 9.81*(28822*Data[:, -3] + 915.55)*1000/(np.power(diameter/1000, 2)*np.pi/4)
    info = f'Gel thickness: {thickness}, Step incrament: {stepSize}, Max Strain: {maxStrain}, Step time: {testTime}, Diameter: {diameter}'
    return parameters, Data, info


def DataExport(params, Data, info):
    fileName = f'{params}'
    if os.path.isfile(fileName) == 0:
        np.savetxt(f"Data/{fileName}.csv", Data, header = 'Position (mm), Strain (mm/mm), Temperature (C), Time, Stress (Pa), Time (s), Voltage (V)', delimiter = ",",
                   fmt = "%f", comments = f'{info}\n\n')
    elif os.path.isfile(fileName) == 1:
        os.remove(fileName)
        np.savetxt(f"Data/{fileName}.csv", Data, header = 'Position (mm), Strain (mm/mm), Temperature (C), Time, Stress (Pa), Time (s), Voltage (V)', delimiter = ",",
                   fmt = "%f", comments = f'{info}\n\n')