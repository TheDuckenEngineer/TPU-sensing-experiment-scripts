"""****************************Imports****************************"""
from tpu_sensing.functions import *
from  tpu_sensing.keithley_connect import *; from tpu_sensing.keithley_setup import *

"""***************Connect to devices***************"""
s, ser = DeviceConnect()


try: 
    """***************Experimental script***************"""
    # s is the Keithley socket connection
    # ser is the serial connection to the motherboard
    # stepSize is the actuators incremental displacement (mm)
    # maxStrain is the maximum desired strain (%). it's a function of the gel thickness 
    # temperatureList is the desired temperatures in a list form (C)
    # testTime is how long to record data at each displacement (s)
    params, Data, info = Experiment(s, ser, stepSize = 0.02, maxStrain = 15, 
                                    temperatureList = [24], testTime = 120)


    """*******************Data export*******************"""
    DataExport(params, Data, info)
    
    # end test up by lifting load cell and turning the bed off 
    print('Test complete\n\n')
    PrintCommand(ser, 'G1 Z10\n')
    PrintCommand(ser, 'M140 S20 \n')

except KeyboardInterrupt:
    instrument_write(s, "ABORT")
    print('\nTest aborted')
    PrintCommand(ser, 'G1 Z10\n')
    PrintCommand(ser, 'M140 S20 \n')
    pass