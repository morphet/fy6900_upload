import numpy as np
import serial
import time

def exchange(cmd):
    ser.write(cmd)
    time.sleep(0.05)
    print 'waiting', ser.inWaiting(), 
    ret = ser.readline()
    ser.flushInput()
    return ret

def dec_to2byte(N, base=2**8):
    """convert a number N in base "base" to a two-byte value, returned as a tuple of 0-255 ints"""
    B = N/base
    A = N-B*base
    return A, B

sername = "/dev/ttyUSB0" #you'll have to figure this one out on your own
ser = serial.Serial(sername, 115200, timeout = 1)
print ser

#test communications, ask the generator for its model. 
print exchange("UMO\x0a")
#mine prints waiting 14 FY6900-60M

#test control, choose sine wave
print exchange("WMW0\x0a")

#in this minimal example we'll upload to Arbitrary waveform number 50
exchange("WMW{:d}\x0a".format(50+35)) #choose arbitrary wave 50

# the FY6900 has 2**13 = 8192 available samples
length = 2**13

time_base = np.linspace(0, np.pi*2, num=length, endpoint=False) #time base to generate wave.
#In my case, [0, 2pi)

#come up with your waveform bounded [-1, 1] inclusive.
#It does not have to span the entire [-1, 1] domain.
#I came up with an offset, square-tooted, offset-again sine wave
sig = (np.sin(time_base)/2+.5)**.5*2-1 

# map linearly: -1 -> 0, 1 -> 2**14-1, and 0 -> 2**13
mapped_sig = 0.5*(sig+1.)*(2**14-1)
samples = np.ceil(mapped_sig).astype(int)

#transform samples to a list of contiguous bytes, two bytes per sample.
#as per "Slidept.net-protocol arbitary.doc.pdf"
#I'm working with integer 0-255 values here, because they're easier to think about
#and because the serial module plays nice with them.
bytes = []
for i in range(length):
    bb = dec_to2byte(samples[i])
    bytes.extend([bb[0], bb[1]])

#When the DDS_WAVExx comand is sent, the unit will respond "W".
arg = b"DDS_WAVE50\n"
ser.write(arg)
while True:
    time.sleep(0.05)
    res = ser.readall()
    if len(res)>0:
        print res
        break

#The unit will then accept bytes, and it will not respond or take any commands until 2**13 samples (2**14 bytes) have been sent
chunk_length = 256
for i in range(100000):
    this_chunk = bytes[i*chunk_length:(i+1)*chunk_length] #chop up the array. The higher, the faster upload happens
    #I don't know what are the limits to this
    ser.write(this_chunk) #send a "chunk-length"-list of [0, 2**14-1) integers
    time.sleep(0.005) #sleep to avoid buffer overflow. I don't know whether this is necessary
    if ser.inWaiting()>0: #Has the unit responded?
        print ser.readall()
        break   
    if (i+1)*chunk_length>=len(bytes): #Have we consumed all our data?
        print ser.readall()
        break
        
#On success, the unit responds "HN"
#The unit should display a little picture of our curve.
ser.close()
