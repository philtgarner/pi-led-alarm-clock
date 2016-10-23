# Raspberry Pi LED alarm clock

This project uses a Raspberry Pi to control LEDs for use as an alarm clock. The alarm clock can be easily configured and it will smoothly change from one colour (usually off) to another, imitating a sunrise and waking you up naturally - at least that's the theory.

## Features
This project is very much in its infancy, it works at a basic level but there are a handful of features to add in the future.

### Current features
* Repeatable alarms
* Use of any colours
* LED fade on startup

### Future additions
* Integrate a 7 segment display to show the time
* Buttons controls
  * Button to turn light on at any time the alarm isn't in use - use different colours for different times of day
  * Button to turn light on while alarm is going off - immediately fade up
* Enable configuration with web UI

## Setup
To configure the LEDs you will need to change some constants in `alarm.py`. To setup a series of alarms you will need to setup a `config.json` file.

### LED setup
The configuration of the LEDs is done by adjusting a few constants in `alarm.py`. These should be initialised according to the [rpi_ws281x](https://github.com/jgarff/rpi_ws281x) library.
* `LED_COUNT` - Set this to the number of LEDs you have in your strip/ring
* `LED_PIN` - You'll probably want to keep this at 18
* `LED_FREQ` - 800khz seems to do the job
* `LED_DMA` - Probably keep at 5
* `LED_BRIGHTNESS` - I have kept this at 255 but it probably depends on your LED setup
* `LED_INVERT` - False seems to do the trick
* `LED_CHANNEL` - 0
* `LED_STRIP_TYPE` - This dictates the colour order, for my setup I needed `ws.WS2811_STRIP_GRB` but this may well be different for you.

### Alarm setup
All the alarm configurations are specified in `config.json`. Copy `sample-config.json` and rename it to get started. The tags in the JSON file should be fairly self explanitory.

## Libraries
This project uses [rpi_ws281x](https://github.com/jgarff/rpi_ws281x) to control the LEDs and [schedule](https://github.com/dbader/schedule) to start the alarms at a given time

## Things to note
* To make the script run on startup you should add the command to `rc.local` as per [these instructions](https://www.raspberrypi.org/documentation/linux/usage/rc-local.md).
* If you encounter randomly flickering LEDs it might be the audio output from the Pi interfering with PWM pin. You should add the following to your `/boot/config.txt` file (thanks to [Gadgetoid](https://github.com/Gadgetoid) on [rpi_ws281x issue 103](https://github.com/jgarff/rpi_ws281x/issues/103)):
````
hdmi_force_hotplug=1
hdmi_force_edid_audio=1
````
* If your LEDs are not showing the correct colours it may be because the colour order is set wrong. Make sure you set it correctly (thanks to [penfold42](https://github.com/penfold42) on [rpi_ws281x issue 122](https://github.com/jgarff/rpi_ws281x/issues/122)).

