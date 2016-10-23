import schedule
import time
import json
from neopixel import *
from random import shuffle
import threading
import os

#Non-configurable constants
CONFIG_FILE = 'config.json'
CONFIG_DIR = os.path.dirname(__file__)
BOOT_DURATION = 6
DEBUG = True

# LED strip configuration:
LED_COUNT 			= 12 		# Number of LED pixels.
LED_PIN 			= 18 		# GPIO pin connected to the pixels (must support PWM!).
LED_FREQ 			= 800000 	# LED signal frequency in hertz (usually 800khz)
LED_DMA 			= 5 		# DMA channel to use for generating signal (try 5)
LED_BRIGHTNESS 		= 255 		# Set to 0 for darkest and 255 for brightest
LED_INVERT 			= False 	# True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL 		= 0
LED_STRIP_TYPE 		= ws.WS2811_STRIP_GRB

#Default settings (will be used if they aren't found in the config file)
boot_red 			= 100
boot_green 			= 100
boot_blue 			= 100
alarm_off_duration 	= 30

#The current colours
current_red 		= 0
current_green 		= 0
current_blue 		= 0
alarm_on 			= False

#The LEDs
strip 				= None

#Threading locks
print_lock = threading.Lock()
current_colour_lock = threading.Lock()
alarm_status_lock = threading.Lock()


def runAlarm(start, end, duration, remain_on):
	global alarm_on
	with alarm_status_lock:
		alarm_on = True
	
	#Build a thread to run the alarm cycle
	alarm_on_thread = threading.Thread(target=transition, args=(start, end, duration, True))
	alarm_on_thread.daemon = True
	
	#Build a thread to turn off the alarm 
	alarm_off_thread = threading.Thread(target=turnOffAlarm, args=(duration, remain_on))
	alarm_off_thread.daemon = True	
	
	#Run the threads
	alarm_on_thread.start()
	alarm_off_thread.start()
	
def turnOffAlarm(duration, remain_on):
	global alarm_on
	global current_red
	global current_green
	global current_blue
	global  alarm_off_duration
	
	out('Waiting for alarm to finish')
	time.sleep(duration)
	out('Waiting for remaining on time')
	time.sleep(remain_on)
	out('Ready to turn off alarm')
	
	if alarm_on:
		out('Turning off alarm')
		current = {'red' : current_red, 'green' : current_green, 'blue' : current_blue}
		off = {'red' : 0, 'green' : 0, 'blue' : 0}
		transition(current, off,  alarm_off_duration)
	with alarm_status_lock:
		alarm_on = False
	
def transition(start, end, duration, interruptable = False):
	global strip
	global current_red
	global current_green
	global current_blue
	global alarm_on
		
	diffRed = end['red'] - start['red']
	diffGreen = end['green'] - start['green']
	diffBlue = end['blue'] - start['blue']
	steps = max(abs(diffRed), abs(diffGreen), abs(diffBlue))
	interval = duration / steps / strip.numPixels()
	#Sleep is pretty inaccurate with small numbers, if its less then 2ms just don't sleep.
	if interval < 0.002:
		interval = 0
	
	out('Starting transition...')
	#Set the initial colour
	for led in range(strip.numPixels()):
		strip.setPixelColorRGB(led, start['red'], start['green'], start['blue'])
		strip.show()
	
	for step in range(steps):
		#Build a randomly sorted array to ensure the lights come on randomly (avoids a spiral effect)
		random_order = []
		random_order.extend(range(0, strip.numPixels()))
		shuffle(random_order)
		#Store the current colour
		with current_colour_lock:
			current_red = int(start['red'] + (diffRed / steps) * step)
			current_green = int(start['green'] + (diffGreen / steps) * step)
			current_blue = int(start['blue'] + (diffBlue / steps) * step)
			nextColor = Color(current_red, current_green, current_blue)
		for led in range(strip.numPixels()):
			#Run the next step in the process if this transition can't be interrupted or it can and the alarm is on
			with alarm_status_lock:
				if not interruptable or (alarm_on and interruptable):
					strip.setPixelColor(random_order[led],nextColor)
					strip.show()
					time.sleep(interval)
				else:
					return
			
	#Set the final colour
	for led in range(strip.numPixels()):
		strip.setPixelColorRGB(led, end['red'], end['green'], end['blue'])
		strip.show()
	
	out('End of transition')
	
			
def runStartup():
	global boot_red
	global boot_green
	global boot_blue
	boot = {'red' : boot_red, 'green' : boot_green, 'blue' : boot_blue}
	off = {'red' : 0, 'green' : 0, 'blue' : 0}
	in_time = int(BOOT_DURATION / 2)
	out_time = BOOT_DURATION - in_time
	transition(off, boot, in_time)
	transition(boot, off, out_time)

def out(message):
	global DEBUG
	if DEBUG:
		with print_lock:
			print(message)

	
#Run application
out('Reading configuration file...')
with open(os.path.join(CONFIG_DIR, CONFIG_FILE)) as config_file:
	config = json.load(config_file)
	
	#Load the boot colours
	if 'boot_red' in config:
		boot_red = config['boot_red']
	if 'boot_green' in config:
		boot_green = config['boot_green']
	if 'boot_blue' in config:
		boot_blue = config['boot_blue']	
	if 'alarm_off_duration' in config:
		alarm_off_duration = config['alarm_off_duration']	
	out('Loaded configuration')
	
	out('Loading alarms...')
	#Check to see if there are any alarms listed
	if 'alarms' in config:
		#Loop through the alarms in turn
		for alarm in config['alarms']:
			#If each alarm contains the necessary information then run the alarm
			if 'time' in alarm and 'duration' in alarm and 'days' in alarm and 'remain_on' in alarm:
				start = {'red' : alarm['start_red'], 'green' : alarm['start_green'], 'blue' : alarm['start_blue']}
				end = {'red' : alarm['end_red'], 'green' : alarm['end_green'], 'blue' : alarm['end_blue']}
				#Check the days in turn
				if 'monday' in alarm['days']:
					schedule.every().monday.at(alarm['time']).do(runAlarm, start, end, alarm['duration'], alarm['remain_on'])
				if 'tuesday' in alarm['days']:
					schedule.every().tuesday.at(alarm['time']).do(runAlarm, start, end, alarm['duration'], alarm['remain_on'])
				if 'wednesday' in alarm['days']:
					schedule.every().wednesday.at(alarm['time']).do(runAlarm, start, end, alarm['duration'], alarm['remain_on'])
				if 'thursday' in alarm['days']:
					schedule.every().thursday.at(alarm['time']).do(runAlarm, start, end, alarm['duration'], alarm['remain_on'])
				if 'friday' in alarm['days']:
					schedule.every().friday.at(alarm['time']).do(runAlarm, start, end, alarm['duration'], alarm['remain_on'])
				if 'saturday' in alarm['days']:
					schedule.every().saturday.at(alarm['time']).do(runAlarm, start, end, alarm['duration'], alarm['remain_on'])
				if 'sunday' in alarm['days']:
					schedule.every().sunday.at(alarm['time']).do(runAlarm, start, end, alarm['duration'], alarm['remain_on'])
	out('Loaded alarms')
				
config_file.closed
out('Closed configuration file')

out('Initialising LEDs...')
print(LED_STRIP_TYPE)
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP_TYPE)
strip.begin()
out('Initialised LEDs')

out('Running boot LEDs')
runStartup()

out('Waiting for alarms')
while True:
 schedule.run_pending()
 time.sleep(1)





