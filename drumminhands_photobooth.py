#!/usr/bin/env python
# -*- coding: utf-8 -*-

# created by chris@drumminhands.com
# see instructions at http://www.drumminhands.com/2014/06/15/raspberry-pi-photo-booth/

import os
import shutil
import glob
import time
import traceback
from time import sleep
import RPi.GPIO as GPIO
#import picamera # http://picamera.readthedocs.org/en/release-1.4/install2.html
import atexit
import sys
import socket
import pygame
import pygame.camera
#import pytumblr # https://github.com/tumblr/pytumblr
import config
from signal import alarm, signal, SIGALRM, SIGKILL

########################
### Variables Config ###
########################
led1_pin = 12 # LED 1
led2_pin = 19 # LED 2
led3_pin = 21 # LED 3
led4_pin = 23 # LED 4
button1_pin = 22 # pin for the big red button
button2_pin = 07 # pin for button to shutdown the pi
button3_pin = 16 # pin for button to end the program, but not shutdown the pi

post_online = 0 # default 1. Change to 0 if you don't want to upload pics.
total_pics = 2 # number of pics to be taken
capture_delay = 0 # delay between pics
prep_delay = 1 # number of seconds at step 1 as users prep to have photo taken
gif_delay = 100 # How much time between frames in the animated gif
restart_delay = 2 # how long to display finished message before beginning a new session

monitor_w = 1024
monitor_h = 768
transform_x = 1024 # how wide to scale the jpg when replaying
transfrom_y = 768 # how high to scale the jpg when replaying
offset_x = 0 # how far off to left corner to display photos
offset_y = 0 # how far off to left corner to display photos
replay_delay = 1 # how much to wait in-between showing pics on-screen after taking
replay_cycles = 2 # how many times to show each photo on-screen after taking

test_server = 'www.google.com'
real_path = os.path.dirname(os.path.realpath(__file__))


# Setup the tumblr OAuth Client
#client = pytumblr.TumblrRestClient(
#    config.consumer_key,
#    config.consumer_secret,
#    config.oath_token,
#    config.oath_secret,
#);

####################
### Other Config ###
####################
GPIO.setmode(GPIO.BOARD)
GPIO.setup(led1_pin,GPIO.OUT) # LED 1
GPIO.setup(led2_pin,GPIO.OUT) # LED 2
GPIO.setup(led3_pin,GPIO.OUT) # LED 3
GPIO.setup(led4_pin,GPIO.OUT) # LED 4
GPIO.setup(button1_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # falling edge detection on button 1
GPIO.setup(button2_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # falling edge detection on button 2
GPIO.setup(button3_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # falling edge detection on button 3

GPIO.output(led1_pin,True);
GPIO.output(led2_pin,True);
GPIO.output(led3_pin,True);
GPIO.output(led4_pin,True);

time.sleep(0.2)
GPIO.output(led1_pin,False);
time.sleep(0.2)
GPIO.output(led2_pin,False);
time.sleep(0.2)
GPIO.output(led3_pin,False);
time.sleep(0.2)
GPIO.output(led4_pin,False); #for some reason the pin turns on at the beginning of the program. why?????????????????????????????????


#################
### Functions ###
#################

def cleanup():
  print('Ended abruptly')
  GPIO.cleanup()
atexit.register(cleanup)

def shut_it_down(channel):  
    print "Shutting down..." 
    GPIO.output(led1_pin,True);
    GPIO.output(led2_pin,True);
    GPIO.output(led3_pin,True);
    GPIO.output(led4_pin,True);
    time.sleep(3)
    os.system("sudo halt")

def exit_photobooth(channel):
    print "Photo booth app ended. RPi still running" 
    GPIO.output(led1_pin,True);
    time.sleep(3)
    sys.exit()
    
def clear_pics(foo): #why is this function being passed an arguments?
    #delete files in folder on startup
	files = glob.glob(config.file_path + '*')
	for f in files:
		os.remove(f) 
	#light the lights in series to show completed
	print "Deleted previous pics"
	GPIO.output(led1_pin,False); #turn off the lights
	GPIO.output(led2_pin,False);
	GPIO.output(led3_pin,False);
	GPIO.output(led4_pin,False)
	pins = [led1_pin, led2_pin, led3_pin, led4_pin]
	for p in pins:
		GPIO.output(p,True); 
		sleep(0.25)
		GPIO.output(p,False);
		sleep(0.25)
      
def is_connected():
  try:
    # see if we can resolve the host name -- tells us if there is
    # a DNS listening
    host = socket.gethostbyname(test_server)
    # connect to the host -- tells us if the host is actually
    # reachable
    s = socket.create_connection((host, 80), 2)
    return True
  except:
     pass
  return False    

def init_pygame():
    print "pygame init start"
    pygame.init()
    pygame.camera.init()
    size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
    pygame.display.set_caption('Photo Booth Pics')
    pygame.mouse.set_visible(False) #hide the mouse cursor	

    print "pygame init done"
    return pygame.display.set_mode(size, pygame.FULLSCREEN)

def show_camera_until(button):
    global screen
    font = pygame.font.Font(None, 36)
    text = font.render(u"Zum Loslegen: Roten Knopf drücken.", True, (128, 128, 128))
    #screen = init_pygame()
    pixel_width = 1024
    pixel_height = 768
    camera = pygame.camera.Camera("/dev/video0",(pixel_width,pixel_height))
    camera.start()
    while GPIO.input(button) == GPIO.HIGH:
      image = camera.get_image()
      screen.blit(image,(offset_x,offset_y))
      screen.blit(text,(512 - text.get_width() // 2, 384 - text.get_height() // 2))
      pygame.display.flip()
      sleep(0.0001)
    camera.stop()

def show_image(image_path):
    global screen
    #screen = init_pygame()
    print "load"
    img=pygame.image.load(image_path).convert() 
    print "scale"
    img = pygame.transform.scale(img,(transform_x,transfrom_y))
    print "blit"
    screen.blit(img,(offset_x,offset_y))
    print "flip"
    pygame.display.flip()


def display_pics(jpg_group):
    # this section is an unbelievable nasty hack - for some reason Pygame
    # needs a keyboardinterrupt to initialise in some limited circs (second time running)

    class Alarm(Exception):
        pass
    def alarm_handler(signum, frame):
        raise Alarm
    signal(SIGALRM, alarm_handler)
    alarm(3)
    try:
        screen = init_pygame()

        alarm(0)
    except Alarm:
        raise KeyboardInterrupt
    for i in range(0, replay_cycles): #show pics a few times
		for i in range(1, total_pics+1): #show each pic
			filename = config.file_path + jpg_group + "-0" + str(i) + ".jpg"
                        show_image(filename);
			time.sleep(replay_delay) # pause 
				
# define the photo taking function for when the big button is pressed 
def start_photobooth(): 
	################################# Begin Step 1 ################################# 
	show_image(real_path + "/blank.png")
	print "Get Ready"
	GPIO.output(led1_pin,True);
	show_image(real_path + "/instructions.png")
	sleep(prep_delay) 
	GPIO.output(led1_pin,False)

	show_image(real_path + "/blank.png")
	
	sleep(2) #warm up camera
	################################# Begin Step 2 #################################
	print "Taking pics" 
	now = time.strftime("%Y-%m-%d-%H-%M-%S") #get the current date and time for the start of the filename
	try: #take the photos
			show_image(real_path + "/taking_picture_01.png" )
			tmpfilename = config.tmp_path + now + '-' + "%n.jpg"
			filename = config.file_path + now + '-' + "%n.jpg"
			GPIO.output(led2_pin,True) #turn on the LED
			print("gphoto2 --capture-image-and-download --keep -F 2 --interval 1s --filename %s" % tmpfilename )
        		os.system("gphoto2 --capture-image-and-download --keep -F 2 --interval 1s --filename %s" % tmpfilename )	
			sleep(0.25) #pause the LED on for just a bit
			GPIO.output(led2_pin,False) #turn off the LED
			print "pausing ..."
			sleep(capture_delay) # pause in-between shots
			print "...done2"
	finally:
		pass
	########################### Begin Step 3 #################################
	print "Showing Images" 
	
	for i in range(1,total_pics+1):
		show_image(config.tmp_path + now + '-' + "%d.jpg" % i)
		print "moving"
		shutil.move(config.tmp_path + now + '-' + "%d.jpg" % i,config.file_path + now + '-' + "%d.jpg" % i)
		print "pausing..." 
		sleep(2)
		print "...done" 
	
	GPIO.output(led3_pin,True) #turn on the LED
	
	########################### Begin Step 4 #################################
	print "Done"
	GPIO.output(led4_pin,False) #turn off the LED
	
	show_image(real_path + "/finished.png")
	
	time.sleep(restart_delay)
	show_image(real_path + "/intro.png");

####################
### Main Program ###
####################

# when a falling edge is detected on button2_pin and button3_pin, regardless of whatever   
# else is happening in the program, their function will be run   
#GPIO.add_event_detect(button1_pin, GPIO.FALLING, callback=start_photobooth, bouncetime=300) 
GPIO.add_event_detect(button2_pin, GPIO.FALLING, callback=shut_it_down, bouncetime=300) 

#choose one of the two following lines to be un-commented
GPIO.add_event_detect(button3_pin, GPIO.FALLING, callback=exit_photobooth, bouncetime=300) #use third button to exit python. Good while developing
#GPIO.add_event_detect(button3_pin, GPIO.FALLING, callback=clear_pics, bouncetime=300) #use the third button to clear pics stored on the SD card from previous events

# delete files in folder on startup
files = glob.glob(config.file_path + '*')
for f in files:
   print f 
   #os.remove(f)

print "Photo booth app running..." 
GPIO.output(led1_pin,True); #light up the lights to show the app is running
GPIO.output(led2_pin,True);
GPIO.output(led3_pin,True);
GPIO.output(led4_pin,True);
time.sleep(0.5)
GPIO.output(led1_pin,False); #turn off the lights
GPIO.output(led2_pin,False);
GPIO.output(led3_pin,False);
GPIO.output(led4_pin,False);

screen = init_pygame()
show_image(real_path + "/intro.png");

while True:
        #GPIO.wait_for_edge(button1_pin, GPIO.FALLING)
	time.sleep(0.2) #debounce
	show_camera_until(button1_pin)
	start_photobooth()
