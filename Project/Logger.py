#!/usr/bin/python3

# import Relevant Librares
import os
import smbus
import threading
import RPi.GPIO as GPIO
import spidev # To communicate with SPI devices
from numpy import interp	
from time import sleep	

#initialize variables
Sensor_Val = [0, 0, 0] #Store data from CH0-2: LDR, Temp, Humidity(POT)
Sensor_Print = ['','','']
V_DAC = 1 #default value between thresholds 0.65 and 2.65
alarm = '' #no alarm
#boolean variables
bMonitoring = 1 #default monitoring
#time variables
T_Delay=5
t0 = 0 
t1 = 0

#Initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM) #Output pin mode

#Output
#Input
PB = [23, 24, 16, 20] #push-button pins
GPIO.setup(PB[0], GPIO.IN, pull_up_down=GPIO.PUD_UP) #btn 1, start/stop
GPIO.setup(PB[1], GPIO.IN, pull_up_down=GPIO.PUD_UP) #btn 2, reset
GPIO.setup(PB[2], GPIO.IN, pull_up_down=GPIO.PUD_UP) #btn 3, change interval
GPIO.setup(PB[3], GPIO.IN, pull_up_down=GPIO.PUD_UP) #btn 4, dismiss alarm

#Button Function
def startStop_btn(channel):
    #print("Start-stop button pressed")
    global bMonitoring
    if bMonitoring==0:
        bMonitoring=1
    else:
        bMonitoring=0
        
def reset_btn(channel):
    #print("Reset button pressed")
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
    #print("Dismiss alarm pressed")
    global alarm 
    alarm = ''
 
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
  spi.max_speed_hz = 1350000
  adc = spi.xfer2([1,(8+channel)<<4,0])
  data = ((adc[1]&3) << 8) + adc[2]
  return data
  
def Volts(data):    #Convert ADC to Voltage
  volts = (data * 3.3) / float(1024)    #V_in= data*V_ref/1024, V_ref=3v3
  #volts = interp(data, [0, 1023], [0, 3.3]) 
  volts = round(volts, 2) # Round off to 2 decimal places
  return volts

def Temp(V_out):     #Convert Voltage to Temperature
  temp = (V_out-0.5)/10 #T_ambient=(V_out-V_0)/T_coefficient, V_0=500mV, T_coefficient=10
  temp = round(temp)
  return temp
 
 #Functions
def DAC_Value(LightReading, HumidityReading):
    V_DAC = LightReading*HumidityReading/1023
    V_DAC = round(V_DAC, 2)
    return V_DAC

def Alarm():
    global alarm
    alarm = '*'

#Table setup
tableHeaders = ["RTC Time", "Sys Timer", "Humidity", "Temp", "Light", "DAC out", "Alarm"]
template = '{:<20}|{:<14}|{:<10}|{:<7}|{:<7}|{:<7}|{:<5}'

def Table():
    print("BONG HOUSE")
    print template.replace(':', ':-').format('', '', '', '', '', '', '')
    print template.format(*tableHeaders)
    print template.replace(':', ':-').format('', '', '', '', '', '', '')

Table()

#Main stuff
def main():
    if bMonitoring==1:
        Sensor_Val[0] = Volts(analogInput(0))
        Sensor_Val[2] = Volts(analogInput(2))
        
        temp = Volts(analogInput(1))
        Sensor_Val[1] = Temp(temp)
        
        #print( time.strftime("%H:%M:%S") + "    " + '{0: <8}'.format(systemTime()) + "      "+ '{0: <5}'.format(humidity)+ "       "+ '{0: <5}'.format(temp) + "   "+ '{0: <5}'.format(light)+ "    " + '{0: <5}'.format('DAC') + "      "+ '{0: <5}'.format('*') )
        V_DAC = DAC_Value(analogInput(0), Sensor_Val[2]) #formula is giving weird answers
        if (V_DAC<0.65 or V_DAC>2.65):
            Alarm()
        print template.format('','', "{}V ".format(Sensor_Val[2]), "{} C".format(Sensor_Val[1]), "{}V ".format(Sensor_Val[0]), "{}V ".format(V_DAC), alarm)
        #print template.format('','', Sensor_Print[2], Sensor_Print[1], Sensor_Print[0], '', '')
        sleep(T_Delay) #will change as sleep stops background events from occuring
  
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
