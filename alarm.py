import schedule
import time
from time import strftime
import json
from neopixel import *
from random import shuffle
import threading
import os
import RPi.GPIO as GPIO
from Adafruit_LED_Backpack import SevenSegment
import datetime

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

#Button configuration:
BUTTON_ONE_PIN 		= 23
BUTTON_TWO_PIN 		= 8
LONG_PRESS_TIME 	= 10
BUTTON_BOUNCE_TIME 	= 1000

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

#The off colour
off = {'red' : 0, 'green' : 0, 'blue' : 0}
on = {'red' : 0, 'green' : 100, 'blue' : 0}

#The clock
clock = SevenSegment.SevenSegment()
current_clock_display = 0
CLOCK_24_HOUR = True

#Threading locks
print_lock = threading.Lock()
current_colour_lock = threading.Lock()
alarm_status_lock = threading.Lock()

#Start the listeners for the buttons
def buttonListener():
	global BUTTON_ONE_PIN
	global BUTTON_TWO_PIN
	global BUTTON_BOUNCE_TIME
	GPIO.add_event_detect(BUTTON_ONE_PIN, GPIO.RISING, callback=toggleBedsideLight, bouncetime=BUTTON_BOUNCE_TIME)
	GPIO.add_event_detect(BUTTON_TWO_PIN, GPIO.RISING, callback=showOff, bouncetime=BUTTON_BOUNCE_TIME)

#Spins some LEDs a few times
def showOff(channel):
	spin(131,99,255)
	spin(73,255,78)
	spin(204,113,38)

#Spins the LEDs in a given colour. Performs one spin
def spin(r, g, b):
	global strip
	for led in range(strip.numPixels()):
		for ledOff in range(strip.numPixels()):
			strip.setPixelColorRGB(ledOff, 0, 0, 0)
		strip.setPixelColorRGB(led, r, g, b)
		strip.show()
		time.sleep(0.05)

	for ledOff in range(strip.numPixels()):
		strip.setPixelColorRGB(ledOff, 0, 0, 0)
	strip.show()

#Toggles the bedside light functionality.
def toggleBedsideLight(channel):
	global current_colour_lock
	global alarm_status_lock
	global current_red
	global current_green
	global current_blue
	global alarm_on
	global off
	global on

	with alarm_status_lock:
		if alarm_on:
			alarm_on = False
			with current_colour_lock:
				current_colour = {'red' : current_red, 'green' : current_green, 'blue' : current_blue}
				alarm_off_thread = threading.Thread(target=transition, args=(current_colour, off, 1, False))
				alarm_off_thread.daemon = True
				#Run the threads
				alarm_off_thread.start()
		else:
			with current_colour_lock:
				current_colour = {'red' : current_red, 'green' : current_green, 'blue' : current_blue}
				if current_red == 0 and current_green == 0 and current_blue == 0:
					light_on_thread = threading.Thread(target=transition, args=(current_colour, on, 1, False))
					light_on_thread.daemon = True
					light_on_thread.start()
				else:
					light_off_thread = threading.Thread(target=transition, args=(current_colour, off, 1, False))
					light_off_thread.daemon = True
					light_off_thread.start()

#Restarts the Raspberry Pi.
def restartPi():
	os.system('sudo shutdown -r now')

#Starts the threads to run the alarm. This will turn the alarm on and then off after the specified duration
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

#Turns the alarm off id it is still on.
def turnOffAlarm(duration, remain_on):
	global alarm_on
	global current_red
	global current_green
	global current_blue
	global alarm_off_duration

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

#Transitions the LEDs from one colour to another.
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
	current_red = end['red']
	current_green = end['green']
	current_blue = end['blue']

	out('End of transition')

#Runs a startup sequence (fades LEDs in and out to show program is running)
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

#Prints a message.
def out(message):
	global DEBUG
	if DEBUG:
		with print_lock:
			print(message)

#Schedules a single alarm
def loadAlarm(alarm):
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
		out('Alarm set for ' + alarm['time'] + ' on ' + str(alarm['days']))
	else:
		out('Cannot load alarm')

def updateClock():
	global clock
	global current_clock_display
	global CLOCK_24_HOUR
	now = datetime.datetime.now()
	new_clock_display = (now.hour * 100) + now.minute
	if not CLOCK_24_HOUR and new_clock_display >= 1200:
		new_clock_display = new_clock_display - 1200

	if new_clock_display != current_clock_display:
		out('Updating clock to ' + str(new_clock_display))
		current_clock_display = new_clock_display
		clock.clear()
		clock.print_float(current_clock_display, decimal_digits=0)
		clock.set_colon(True)
		clock.write_display()



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

	out('Configuring the buttons...')
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(BUTTON_ONE_PIN, GPIO.IN)
	GPIO.setup(BUTTON_TWO_PIN, GPIO.IN)
	out('Configured the button')
	out('Starting thread to listen for button presses...')
	#Listen for button presses
	buttonListener()
	out('Started thread to listen for button presses')

	out('I think the time is: ' + strftime("%Y-%m-%d %H:%M:%S"))


	out('Loading alarms...')
	#Check to see if there are any alarms listed
	if 'alarms' in config:
		#Loop through the alarms in turn
		for alarm in config['alarms']:
			#If each alarm contains the necessary information then run the alarm
			loadAlarm(alarm)
	out('Loaded alarms')

config_file.closed
out('Closed configuration file')

#Initialise the clock
out('Initialising the clock')
clock.begin()
clock.set_brightness(0)
out('Clock initialised')

out('Initialising LEDs...')
print(LED_STRIP_TYPE)
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, LED_STRIP_TYPE)
strip.begin()
out('Initialised LEDs')

out('Running boot LEDs')
runStartup()

out('Waiting for alarms')
try:
	while True:
	 schedule.run_pending()
	 time.sleep(1)
	 updateClock()
except KeyboardInterrupt:
    out('Goodbye')
finally:
	GPIO.cleanup()
