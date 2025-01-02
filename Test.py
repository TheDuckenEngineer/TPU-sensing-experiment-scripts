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
    # diameter is the gel diameter based on the punch used (mm)
    # temperatureList is the desired temperatures in a list form (C). currently set to no heating so put one element in the list
    # testTime is how long to record data at each displacement (s)
    params, Data, info = Experiment(s, ser, stepSize = 0.02, maxStrain = 10, diameter = 12,
                                    temperatureList = [50], testTime = 60)


    """*******************Data export*******************"""
    DataExport(params, Data, info)
    
    # end test up by lifting load cell and turning the bed off 
    print('Test complete\n\n')
    PrintCommand(ser, 'G1 Z10\n')
    PrintCommand(ser, 'M140 S20 \n')

except KeyboardInterrupt:
    InstrumentWrite(s, "ABORT")
    print('\nTest aborted')
    PrintCommand(ser, 'G1 Z10\n')
    PrintCommand(ser, 'M140 S20 \n')
    pass