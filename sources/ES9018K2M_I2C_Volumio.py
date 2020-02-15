#!/usr/bin/python2
# coding: utf-8
#
# ESS ES9018K2M DAC I2C bus direct hardware management script for Volumio
# by Damian Schneider (January 2020)
#
# Based on python script by vigo
# https://forum.volumio.org/setup-audiophonics-es9018k2m-dac-with-volumio-t6041.html
# which is based on script for Runeaudio by Audiophonics and Fujitus
# https://github.com/audiophonics/ES9018K2M_serial_sync
#
# Require to setup ES9018K2M DAC with I2C pins connected to Raspberry pi


import time , smbus
import subprocess , os
import json
from urllib2 import Request, urlopen, URLError

#global register definitions
DEVICE_ADDRESS = 0x48      #7 bit address (will be left shifted to add the read write bit), alternat address: 0x49 if pin 5 is pulled high

#useful register numbers, refer to datasheet for more info (is hard to find but can be found online, check chinese sites)
#register number refers to its address, reg 0 is addres 0x00 
#Reg0 system&oscillator settings, write 0x01 to reset chip (default 0x00)
#Reg1 input configuration, default=I2S 32bit, 0x8C (highest two bits are bit rate, write 0x4C for 24bit and 0x0C for 16bit)
#Reg6 deemphasis filter settings (off by default) and softe-mute speed (0x40 = fastest, 0x47 = slowest (?) not tested but 3 LSB give the speed, default is 0x42)
#Reg7 filter setting and mute, set to 0x80 (default) for unmute and set to 0x83 to mute both channels (2 LSB are mute or unmute) will ramp up the volume, speed can be set in register 6
#Reg15 left channel volume (0 is 0dB = loudest, 255 is -127.5dB = almost mute)
#Reg16 right channel volume (0 is 0dB = loudest, 255 is -127.5dB = almost mute)

      
def VolumioGetStatus():
    process = subprocess.Popen('/volumio/app/plugins/system_controller/volumio_command_line_client/volumio.sh status', stdout=subprocess.PIPE, shell=True)
    os.waitpid(process.pid, 0)[1]
    Status = process.stdout.read().strip()

    ParamList = json.loads(Status)

    #set the defaults in case the status call does not return a required value
    volumioBitDepth = '32 bit'
    volumioStatus = 'stop' #also sets volume = 0
    volumioMute = False

    # volumioService = ParamList['service'] #service currently not checked

    if 'status' in ParamList:
        volumioStatus = ParamList['status']

    if 'bitdepth' in ParamList:
        volumioBitDepth = ParamList['bitdepth'] #entry is '24 bit' o r '16 bit', we only need to check if it is 16bit (on webradio this string is empty but plays fine with 32bit)

    if 'volume' in ParamList:
        volumioVolume = ParamList['volume'] #volume is an integer

    if 'mute' in ParamList:
        volumioMute = ParamList['mute'] #is true or false

    if(volumioStatus != 'play'):
        volumioVolume = 0 #set volume low if nothing is playing

    return(volumioVolume, volumioBitDepth, volumioMute)

#set the volume by adjusting both left and right channel, input is 0-100
def ES9018K2M_set_volume(vol):
    vol = max(min(100, vol), 0) #limit the input value 0-100
    vol_set = (100-vol) #map 0-100 to 100-0 (register is attenuation not amplification so 0 = max, 256=min, 100 means -50dB which is qute silent already)
    bus.write_byte_data(DEVICE_ADDRESS, 15, vol_set) #set volume of left channel
    bus.write_byte_data(DEVICE_ADDRESS, 16, vol_set) #set volume of right channel



if __name__ == '__main__':
    bus = smbus.SMBus(1)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
    #set the defaults (also used to check if value changed)
    volume = 100
    bitrate = 32
    mute = False

    try:
        while True: #run the script forever
            volumioStatus = VolumioGetStatus() #read the status of the player: reading volume, bit debth and mute

            #check if a state changed
            if(volumioStatus[0] != volume):
                volume = volumioStatus[0]
                ES9018K2M_set_volume(volume)

            if(volumioStatus[1] == '16 bit'):
                if(bitrate != 16):
                    bitrate = 16
                    bus.write_byte_data(DEVICE_ADDRESS, 1, 0x0C)  # set 16bit mode
            else:
                if(bitrate != 32):
                    bitrate = 32
                    bus.write_byte_data(DEVICE_ADDRESS, 1, 0x8C)  # set 32bit mode (works fine for 24bit input but not for 16 bit)
                    #bus.write_byte_data(DEVICE_ADDRESS, 1, 0x4C)  # set 24bit mode

            if(volumioStatus[2] != mute):  #mute changed
                mute = volumioStatus[2]
                if(mute):
                    bus.write_byte_data(DEVICE_ADDRESS, 7, 0x83)  # mute both channels
                else:
                    bus.write_byte_data(DEVICE_ADDRESS, 7, 0x80)  # unmute both channels

            time.sleep(0.05)
    except KeyboardInterrupt:
        bus.close()
bus.close()