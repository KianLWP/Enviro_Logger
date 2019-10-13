#!/usr/bin/python3

# import Relevant Librares
import smbus
import threading
import RPi.GPIO as GPIO
import spidev # To communicate with SPI devices
from numpy import interp	
from time import sleep	

#initialize variables
T_Delay=5
Sensor_Val = [0, 0, 0] #Store data from CH0-2: LDR, Temp, Humidity(POT)
Sensor_Print = ['','','']

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
    print("Start-stop button pressed")
    global initTimer
    if initTimer == 0:
    	initTimer()
        
def reset_btn(channel):
    print("Reset button pressed")
    # Reset stuff

def changeFreq_btn(channel):
    print("Frequency button pressed")
    global T_Delay
    if T_Delay == 1:
    	T_Delay = 2
    else:
    	if T_Delay == 2:
    		T_Delay = 5
    	else:
    		T_Delay= 1
    print("Polling interval: ", T_Delay)
 
def dismissAlarm_btn(channel):
    print("Dismiss alarm pressed")
 
#Button Detection
GPIO.add_event_detect(PB[0], GPIO.FALLING, callback=startStop_btn, bouncetime=200)
GPIO.add_event_detect(PB[1], GPIO.FALLING, callback=reset_btn, bouncetime=200)
GPIO.add_event_detect(PB[2],GPIO.FALLING, callback=changeFreq_btn, bouncetime=200) 
GPIO.add_event_detect(PB[3], GPIO.FALLING, callback=dismissAlarm_btn, bouncetime=200)

# Start SPI connection
spi = spidev.SpiDev() # Created an object
spi.open(0,0) 
# Read MCP3008 data
def analogInput(channel):
  spi.max_speed_hz = 1350000
  adc = spi.xfer2([1,(8+channel)<<4,0])
  data = ((adc[1]&3) << 8) + adc[2]
  return data
  
# Below function will convert data to voltage
def Volts(data):
  volts = (data * 3.3) / float(1023)
  #volts = interp(data, [0, 1023], [0, 3.3]) 
  volts = round(volts, 2) # Round off to 2 decimal places
  return volts
 


# Below function will convert data to temperature.
def Temp(data):
  temp = ((data * 330)/float(1023))-50
  temp = round(temp)
  return temp
 

#Table setup
tableHeaders = ["RTC Time", "Sys Timer", "Humidity", "Temp", "Light", "DAC out", "Alarm"]
template = '{:<20}|{:<14}|{:<10}|{:<7}|{:<7}|{:<7}|{:<5}'
print("BONG HOUSE")
print template.replace(':', ':-').format('', '', '', '', '', '', '')
print template.format(*tableHeaders)
print template.replace(':', ':-').format('', '', '', '', '', '', '')

#Main stuff
def main():
    Sensor_Val[0] = Volts(analogInput(0))
    Sensor_Val[1] = Temp(analogInput(1))
    Sensor_Val[2] = Volts(analogInput(2))
    #print("Light: ({}V) ".format(Sensor_Val[0]))
    #print("Temp: {} deg C".format(Sensor_Val[1]))
    #print("Humidity: ({}V) ".format(Sensor_Val[2]))
    #print( time.strftime("%H:%M:%S") + "    " + '{0: <8}'.format(systemTime()) + "      "+ '{0: <5}'.format(humidity)+ "       "+ '{0: <5}'.format(temp) + "   "+ '{0: <5}'.format(light)+ "    " + '{0: <5}'.format('DAC') + "      "+ '{0: <5}'.format('*') )
    Sensor_Print[0] = "{}V ".format(Sensor_Val[0])
    Sensor_Print[1] = "{} C".format(Sensor_Val[1])
    Sensor_Print[2] = "{}V ".format(Sensor_Val[2])
    print template.format('','', "{}V ".format(Sensor_Val[2]), "{} C".format(Sensor_Val[1]), "{}V ".format(Sensor_Val[0]), '', '')
    #print template.format('','', Sensor_Print[2], Sensor_Print[1], Sensor_Print[0], '', '')
    sleep(T_Delay)
  
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
