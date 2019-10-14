#!/usr/bin/python3

# import Relevant Librares
import blynklib
import os
import smbus
import threading
import RPi.GPIO as GPIO
import time
import spidev # To communicate with SPI devices
from numpy import interp	
from threading import Thread
###########################################################
# VARIABLES
###########################################################

#initialize variables
Sensor_Val = [0, 0, 0] #Store data from CH0-2: LDR, Temp, Humidity(POT)
Sensor_Print = ['','','']
V_DAC = 1 #default value between thresholds 0.65 and 2.65
alarm = '' #no alarm
#boolean variables
bMonitoring = 1 #default monitoring
bLight = 0
#time variables
T_Delay=1
T_Alarm = 0

T_0 = 0 #0 for when system starts
T_Sec_0 = 0
T_Min_0 = 0
T_Hour_0 = 0
T_1 = 0 #1 for current system time
T_Sec_1 = 0
T_Min_1 = 0
T_Hour_1 = 0
T_sys = 0 #T_1-T_0

# Set-up RTC for time reading
bus = smbus.SMBus(1)
RTCAddr = 0x6f
SEC = 0x00 # see register table in datasheet
MIN = 0x01
HOUR = 0x02

#Initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM) #Output pin mode

#Output
GPIO.setup(21, GPIO.OUT, initial=GPIO.LOW)

#Input
PB = [23, 24, 16, 20] #push-button pins
GPIO.setup(PB[0], GPIO.IN, pull_up_down=GPIO.PUD_UP) #btn 1, start/stop
GPIO.setup(PB[1], GPIO.IN, pull_up_down=GPIO.PUD_UP) #btn 2, reset
GPIO.setup(PB[2], GPIO.IN, pull_up_down=GPIO.PUD_UP) #btn 3, change interval
GPIO.setup(PB[3], GPIO.IN, pull_up_down=GPIO.PUD_UP) #btn 4, dismiss alarm

###########################################################
# FUNCTIONS
###########################################################
#Time functions
def init_sysTime():
    global T_0, T_Sec_0, T_Min_0, T_Hour_0
    T_Sec_0 = int(time.strftime("%S"))
    T_Min_0 = int(time.strftime("%M"))
    T_Hour_0 = int(time.strftime("%H"))
    T_0 = (T_Hour_0*3600)+(T_Min_0*60)+T_Sec_0
    
def sysTime():
    global T_0, T_Sec_0, T_Min_0, T_Hour_0
    global T_1, T_Sec_1, T_Min_1, T_Hour_1
    global T_sys
    T_Sec_1 = int(time.strftime("%S"))
    T_Min_1 = int(time.strftime("%M"))
    T_Hour_1 = int(time.strftime("%H"))
    T_1 = (T_Hour_1*3600)+(T_Min_1*60)+T_Sec_1
    T_sys = T_1-T_0
   
#Button Function
def startStop_btn(channel):
    #print("Start-stop button pressed")
    global bMonitoring
    if bMonitoring==0:
        bMonitoring=1
        init_sysTime()
    else:
        bMonitoring=0
        
def reset_btn(channel):
    #print("Reset button pressed")
    global T_Alarm, alarm
    T_Alarm = 0
    alarm = ''
    init_sysTime()
    os.system('clear')
    Table()

def changeFreq_btn(channel):
   # print("Frequency button pressed")
    global T_Delay
    if T_Delay == 1:
    	T_Delay = 2
    else:
    	if T_Delay == 2:
    		T_Delay = 5
    	else:
    		T_Delay= 1
    #print("Polling interval: ", T_Delay)
 
def dismissAlarm_btn(channel):
    print("Alarm dismissed")
    global alarm 
    alarm = ''
    GPIO.output(21, GPIO.LOW)
 
#Button Detection
GPIO.add_event_detect(PB[0], GPIO.FALLING, callback=startStop_btn, bouncetime=200)
GPIO.add_event_detect(PB[1], GPIO.FALLING, callback=reset_btn, bouncetime=200)
GPIO.add_event_detect(PB[2],GPIO.FALLING, callback=changeFreq_btn, bouncetime=200) 
GPIO.add_event_detect(PB[3], GPIO.FALLING, callback=dismissAlarm_btn, bouncetime=200)

#Start SPI connection
spi = spidev.SpiDev() # Created an object
spi.open(0,0) 
#Read MCP3008 data
def analogInput(channel):
    #spi.max_speed_hz = 1350000
    spi.max_speed_hz = 1350000
    adc = spi.xfer2([1,(8+channel)<<4,0])
    data = ((adc[1]&3) << 8) + adc[2]
    return data
  
def Volts(data):    #Convert ADC to Voltage
    volts = (data * 3.3) / float(1024)    #V_in= data*V_ref/1024, V_ref=3v3
    #volts = interp(data, [0, 1024], [0, 3.3]) 
    volts = round(volts, 2) # Round off to 2 decimal places
    return volts

def Temp(V_out):     #Convert Voltage to Temperature
    temp = (V_out-0.5)/10 #T_ambient=(V_out-V_0)/T_coefficient, V_0=500mV, T_coefficient=10
    temp = round(temp)
    return temp
 
def DAC_Value(LightReading, HumidityReading):
    V_DAC = LightReading*HumidityReading/1023
    V_DAC = round(V_DAC, 2)
    return V_DAC
    
###########################################################
# Threads and stuff
###########################################################
#Table setup
tableHeaders = ["RTC Time", "Sys Timer", "Humidity", "Temp", "Light", "DAC out", "Alarm"]
template = '{:<12}|{:<12}|{:<10}|{:<7}|{:<7}|{:<7}|{:<5}'

def Table():
    print("BONG HOUSE")
    print template.replace(':', ':-').format('', '', '', '', '', '', '')
    print template.format(*tableHeaders)
    print template.replace(':', ':-').format('', '', '', '', '', '', '')

def readADC():
    global Sensor_Val, alarm, T_Alarm
    while True:  
        if bMonitoring==1:
            Sensor_Val[0] = analogInput(0)
            Sensor_Val[2] = Volts(analogInput(2))
            Sensor_Val[1] = Temp(analogInput(1))
            sysTime()
            V_DAC = DAC_Value(Sensor_Val[0], Sensor_Val[2]) 
            if (V_DAC<0.65 or V_DAC>2.65):
                if ((T_sys-T_Alarm>=180 or T_Alarm==0) and alarm==''):
                    alarm = '*'
                    T_Alarm = T_sys
                   
            print template.format(time.strftime("%H:%M:%S"),time.strftime("%H:%M:%S", time.gmtime(T_sys)), "{}V".format(Sensor_Val[2]), "{} C".format(Sensor_Val[1]), "{}".format(Sensor_Val[0]), "{}V".format(V_DAC), alarm)
            time.sleep(T_Delay) #will change as sleep stops background events from occuring

poll = Thread(target = readADC)
poll.setDaemon(True)

    
def Alarm():
    global bLight
    
    while True:
        if alarm=='*':
            if bLight==0:  #Blinking LED
                GPIO.output(21, GPIO.HIGH)
                bLight=1
            else:
                GPIO.output(21, GPIO.LOW)
                bLight=0
        time.sleep(0.5)
        
weewoo = Thread(target = Alarm)
weewoo.setDaemon(True)


#Blynk stuff
BLYNK_AUTH = 'TJkD0-GGNUnVzcHW7OxqzkuW1hC9P8mp'
# base lib init
blynk = blynklib.Blynk(BLYNK_AUTH)

@blynk.handle_event('read V0')
def read_virtual_pin_handler(pin):
    blynk.virtual_write(0, "{}".format(Sensor_Val[0]))
    blynk.virtual_write(1, "{}V".format(Sensor_Val[2]))
    blynk.virtual_write(2, "{} C".format(Sensor_Val[1]))
    blynk.virtual_write(3, time.strftime("%H:%M:%S", time.gmtime(T_sys)))

    if alarm=='*':
        blynk.virtual_write(4, 255)
    else:
        blynk.virtual_write(4, 0)
        
'''        
@blynk.handle_event('read V0')
def read_virtual_pin_handler(pin):
    blynk.virtual_write(1, "Light")
    blynk.virtual_write(2, "Humidity")
    blynk.virtual_write(3, "Temperature")
    blynk.virtual_write(4, "69:69:69")+
    
    blynk.virtual_write(0, "Yeet")
    blynk.virtual_write(1, "U")
    blynk.virtual_write(2, "Gay")
    blynk.virtual_write(3, "69:69:69")
    blynk.virtual_write(4, 255)
    GPIO.output(21, GPIO.HIGH)
    if alarm == '*':
        blynk.virtual_write(0, 255)
    else:
        blynk.virtual_write(0, 0)
  '''
  
    
#def BlynkBlonk():
 #   while True:
     #   blynk.run()
    
#x = Thread(target = BlynkBlonk)
#x.setDaemon(True)
#x.start()

 # blynk.virtual_write(0, "add", 1, "Humidity Reading: ", "{} C".format(Sensor_Val[1]))
  #blynk.virtual_write(0, "add", 2, "LDR Reading: ", "{}V".format(Sensor_Val[0]))

###########################################################
# MAIN STUFF
###########################################################
#Initialize
Table()
init_sysTime()
poll.start()
weewoo.start()

def main():
    blynk.run()
    time.sleep(T_Delay)

if __name__ == "__main__":
       # Make sure the GPIO is stopped correctly
       try:
           while True:
                  main()
       except KeyboardInterrupt:
              print("Exiting gracefully")
              # Turn off your GPIOs here
              GPIO.cleanup()
       except Exception as e:
        GPIO.cleanup()
        print("Some other error occurred")
        print(e.message)