# PiBtSyncLCD
Python script for displaying BitTorrent Sync status on an LCD display connected to a Raspberry/Banana Pi

![LCD Display example](http://www.hackviking.com/wp-content/uploads/2016/04/IMG_3197.jpg)

So what does this script actually do? It runs an infinit loop until you kill the process. Every 45 seconds it checks the stuff that doesn't need updating all that often and every 3 seconds it checks the current status of the BtSync operations.

#### Every 45 seconds:

- Check the current IP-address
- Check if the Truecrypt volume is actually mounted
- Check if the BtSync daemon is running

#### Every 3 seconds:

- Checks number of files synced
- Checks number of files to be synced
- Checks the current download speed
- Checks the current upload speed

## Pre-Requirements

First you need to wire up the LCD, it differs a bit from model to model but there are ton of descriptions on pinouts if you Google your specific model. Then go ahead and run raspi-config or what ever equivalent your brand of Pi uses. Go under **Advanced** and enable **I2C**. Then we download some tools that we need:

sudo apt-get install i2c-tools python-dev libxml2-dev libxslt1-dev zlib1g-dev python-smbus

This will install all the things you need to communicate over the GPIO header to your LCD and also libraries needed for the features in the script. Then you can go ahead and download the script:

wget -O https://raw.githubusercontent.com/kallsbo/PiBtSyncLCD/master/lcd_info.py

## Script functions

If we first look at the main method it is simple enough. We run the **lcd_init()** function to initialize the LCD. All the LCD functions was forked from a script written by [Matt Hawkins @ Raspberry Pi Spy](https://bitbucket.org/MattHawkinsUK/rpispy-misc/raw/master/python/lcd_i2c.py). Then we set a simple update counter that keeps track of if the 45 second mark has been hit and if we should check the IP, mount and daemon status. It's initially set to 16 so it will run the first loop and the counter is reset. Then it pluses one for every 3 second run so whenever it's larger then 15 the 45 seconds has elapsed.
**get_ip_address()** - Simple function that takes the adapter name (eth0) as a parameter and then grabs the current IP-address of that adapter.

**is_trucrypt_mounted()** - Uses the **os.path.ismount()** function to check if the mount point is actually utilized by the Truecrypt drive.

**get_btsync_cred()** - Checks for the json file on the encrypted volume containing the UI username and password for BitTorrent Sync. I used this approach to keep the credentials safe. This function is executed every 45 seconds to make sure that the script get's the credentials when the disk get's mounted.

**get_btsync_token()** - Sends the initial request to the BitTorrent Sync UI (api) to get the token needed for all the requests to the API. This will also run every 45 seconds to make sure the token never times out and to counter any recycles of the web service.

Every three seconds the script checks if it has the credentials and token needed for the requests and if so runs the **get_btsync_info()**.

**get_btsync_info()** - This function takes two parameters LLforSpeed and LLforFiles which stands for LCD Line. This value is used to display the information on the LCD panel row you like. It simply builds an url with the GLOBAL credentials and token and get the same json that the UI uses. Then parses it and get the total file count for downloaded files as well for files that are in the download queue. It also grabs the current upload and download speed and converts it to Mb/s and displays it on the LCD.

## Credentials JSON file

This is just a plain JSON file containing the credentials. You can modify the script to hard code the credentials in the script but that will impact the security of the script. Here is an example of the credential files:

{
    "BTSYNC_USR": "btuser",
    "BTSYNC_PSW": ":wDHz56L.blDgM,3Jm"
}

http://www.hackviking.com/single-board-computers/pi-python-script-for-btsync-status-lcd/
