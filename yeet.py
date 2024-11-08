"""****************************Imports****************************"""
from tpu_sensing.functions import *
from  tpu_sensing.keithley_connect import *; from tpu_sensing.keithley_setup import *

s, ser = DeviceConnect()

PrintCommand(ser, f'M155 S1 \n')

temperatureReading = []
testTime = 180
temps = range(25, 85, 5)

for i in temps:
    PrintCommand(ser, f'M140 S{i} \n')
    print(f'{i} C testin')
    
    intialTime =  perf_counter_ns() 

    while perf_counter_ns() < intialTime + testTime*10**9:
        # remove empty echos from the mother board
        line = ser.readline()
        if line == b'ok\n' or line == b'ok \n' or line == b'' or line == b' ':
            pass
        else:
            temperatureReading.append(float(str(line, encoding = 'UTF-8').split(' ')[3].lstrip('B:')))

PrintCommand(ser, f'M140 S0 \n')
