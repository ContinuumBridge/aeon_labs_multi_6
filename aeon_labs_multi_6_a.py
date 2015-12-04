#!/usr/bin/env python
# aeon_labs_mullti_6_a.py
# Copyright (C) ContinuumBridge Limited, 2014-2015 - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Peter Claydon
#
BATTERY_CHECK_INTERVAL   = 21600    # How often to check battery (secs) - 6 hours
MAX_INTERVAL             = 3600
MIN_INTERVAL             = 300      # How often to wake up
CHECK_INTERVAL           = 7200     # If not update during this time, assume we've lost connection
TIME_CUTOFF              = 1800     # Data older than this is considered "stale"

import sys
import time
import os
import json
from pprint import pprint
from cbcommslib import CbAdaptor
from cbconfig import *
from twisted.internet import threads
from twisted.internet import reactor

class Adaptor(CbAdaptor):
    def __init__(self, argv):
        self.status =           "ok"
        self.state =            "stopped"
        self.apps =             {"binary_sensor": [],
                                 "battery": [],
                                 "connected": [],
                                 "temperature": [],
                                 "humidity": [],
                                 "ultraviolet": [],
                                 "luminance": []}
        self.intervals = {
            "binary_sensor": MAX_INTERVAL,
            "battery": BATTERY_CHECK_INTERVAL,
            "temperature": MAX_INTERVAL,
            "humidity": MAX_INTERVAL,
            "ultraviolet": MAX_INTERVAL,
            "luminance": MAX_INTERVAL
        }
        self.intervalChanged = False
        self.pollInterval = MIN_INTERVAL - 1 # Start with a short poll interval when no apps have requested
        self.lastTemperatureTime =   0
        self.lastHumidityTime =      0
        self.lastLuminanceTime =     0
        self.lastBinaryTime =        0
        self.lastBatteryTime =       0
        self.lastUltravioletTime =   0
        self.updateTime =            0
        self.lastUpdateTime =        0
        # super's __init__ must be called:
        #super(Adaptor, self).__init__(argv)
        CbAdaptor.__init__(self, argv)
 
    def sendCharacteristic(self, characteristic, data, timeStamp):
        msg = {"id": self.id,
               "content": "characteristic",
               "characteristic": characteristic,
               "data": data,
               "timeStamp": timeStamp}
        for a in self.apps[characteristic]:
            self.sendMessage(msg, a)

    def setState(self, action):
        # error is only ever set from the running state, so set back to running if error is cleared
        if action == "error":
            self.state == "error"
        elif action == "clear_error":
            self.state = "running"
        else:
            self.state = action
        msg = {"id": self.id,
               "status": "state",
               "state": self.state}
        self.sendManagerMessage(msg)

    def forceInterview(self):
        self.cbLog("debug", "forceInterview")
        cmd = {"id": self.id,
               "request": "force_interview",
               "address": self.addr
              }
        self.sendZwaveMessage(cmd)

    def onAction(self, action):
        if action == "interview":
            self.forceInterview()
        else:
            self.cbLog("warning", "onAction. Unrecognised action: " +  str(action))

    def checkConnected(self):
        self.cbLog("debug", "checkConnected, time: " + str(time.time()) + ", updateTime: " + str(self.updateTime))
        if time.time() - self.updateTime > CHECK_INTERVAL:
            connected = False
        else:
            connected = True
        self.sendCharacteristic("connected", connected, time.time())
        reactor.callLater(CHECK_INTERVAL, self.checkConnected)

    def checkBattery(self):
        self.cbLog("debug", "checkBattery")
        cmd = {"id": self.id,
               "request": "post",
               "address": self.addr,
               "instance": "0",
               "commandClass": "128",
               "action": "Get",
               "value": ""
              }
        self.sendZwaveMessage(cmd)
        reactor.callLater(BATTERY_CHECK_INTERVAL, self.checkBattery)

    def pollSensors(self):
        self.cbLog("debug", "pollSensors. intervalChanged: " + str(self.intervalChanged))
        if self.intervalChanged:
            self.intervalChanged = False
            # Set wakeup time
            cmd = {"id": self.id,
                   "request": "post",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "132",
                   "action": "Set",
                   "value": str(self.pollInterval) + ",1"
                  }
            self.sendZwaveMessage(cmd)
            self.cbLog("debug", "pollSensors, sending: " + str(json.dumps(cmd, indent=4)))
        """
        cmd = {"id": self.id,
               "request": "post",
               "address": self.addr,
               "instance": "0",
               "commandClass": "49",
               "action": "Get",
               "value": ""
              }
        self.sendZwaveMessage(cmd)
        """
        reactor.callLater(self.pollInterval, self.pollSensors)

    def onZwaveMessage(self, message):
        #self.cbLog("debug", "onZwaveMessage, message: " + str(message))
        if message["content"] == "init":
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "48",
                   "value": "1"
                  }
            self.sendZwaveMessage(cmd)
            # Temperature
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "49",
                   "value": "1"
                  }
            self.sendZwaveMessage(cmd)
            # luminance
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "49",
                   "value": "3"
                  }
            self.sendZwaveMessage(cmd)
            # Humidity
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "49",
                   "value": "5"
                  }
            self.sendZwaveMessage(cmd)
            # Ultraviolet
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "49",
                   "value": "27"
                  }
            self.sendZwaveMessage(cmd)
            # Battery
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "128"
                  }
            self.sendZwaveMessage(cmd)
            # Set wakeup time
            cmd = {"id": self.id,
                   "request": "post",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "132",
                   "action": "Set",
                   "value": str(MIN_INTERVAL) + ",1"
                  }
            self.sendZwaveMessage(cmd)
            # Associate with this controller
            cmd = {"id": self.id,
                   "request": "post",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "133",
                   "action": "Set",
                   "value": "1,1"
                  }
            self.sendZwaveMessage(cmd)
            # Send binary sensor instead of basic command when PIR triggered
            cmd = {"id": self.id,
                   "request": "post",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "112",
                   "action": "Set",
                   "value": "5,2,1"
                  }
            self.sendZwaveMessage(cmd)
            # Allow device to be woken up locally
            cmd = {"id": self.id,
                   "request": "post",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "132",
                   "action": "Set",
                   "value": "2,1,1"
                  }
            self.sendZwaveMessage(cmd)
            # 10 s timeout period of no-motion detected before the Multisensor sends the OFF state after being triggered.
            cmd = {"id": self.id,
                   "request": "post",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "112",
                   "action": "Set",
                   "value": "3,10,2"
                  }
            self.sendZwaveMessage(cmd)
            # Automatically report parameters when they change
            cmd = {"id": self.id,
                   "request": "post",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "112",
                   "action": "Set",
                   "value": "40,1,1"
                  }
            self.sendZwaveMessage(cmd)
            # Automatically send temperature when it has changed by 0.2 degree
            cmd = {"id": self.id,
                   "request": "post",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "112",
                   "action": "Set",
                   "value": "41,2,2"
                  }
            self.sendZwaveMessage(cmd)
            # Automatically send humidity when it has changed by 1%
            cmd = {"id": self.id,
                   "request": "post",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "112",
                   "action": "Set",
                   "value": "42,1,1"
                  }
            self.sendZwaveMessage(cmd)
            # Report to association group 1
            cmd = {"id": self.id,
                   "request": "post",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "112",
                   "action": "Set",
                   "value": "101,227,4"
                  }
            self.sendZwaveMessage(cmd)
            # Send a message on wakeup
            cmd = {"id": self.id,
                   "request": "get",
                   "address": self.addr,
                   "instance": "0",
                   "commandClass": "132",
                   "value": "lastWakeup"
                  }
            self.sendZwaveMessage(cmd)
            reactor.callLater(300, self.checkBattery)
            reactor.callLater(10, self.pollSensors)
            reactor.callLater(CHECK_INTERVAL, self.checkConnected)
        elif message["content"] == "data":
            try:
                if message["commandClass"] == "49":
                    if message["value"] == "1":
                        updateTime = message["data"]["val"]["updateTime"] 
                        # Only send if we don't already have an update from this time and the update is recent (not stale after restart)
                        if updateTime != self.lastTemperatureTime and time.time() - updateTime < TIME_CUTOFF:
                            temperature = message["data"]["val"]["value"] 
                            if temperature is not None:
                                self.cbLog("debug", "onZwaveMessage, temperature: " + str(temperature))
                                self.sendCharacteristic("temperature", temperature, time.time())
                                self.lastTemperatureTime = updateTime
                                self.updateTime = updateTime
                    elif message["value"] == "3":
                        updateTime = message["data"]["val"]["updateTime"] 
                        if updateTime != self.lastLuminanceTime and time.time() - updateTime < TIME_CUTOFF:
                            luminance = message["data"]["val"]["value"] 
                            if luminance is not None:
                                self.cbLog("debug", "onZwaveMessage, luminance: " + str(luminance))
                                self.sendCharacteristic("luminance", luminance, time.time())
                                self.lastLuminanceTime = updateTime
                                self.updateTime = updateTime
                    elif message["value"] == "5":
                        updateTime = message["data"]["val"]["updateTime"] 
                        if updateTime != self.lastHumidityTime and time.time() - updateTime < TIME_CUTOFF:
                            humidity = message["data"]["val"]["value"] 
                            if humidity is not None:
                                self.cbLog("debug", "onZwaveMessage, humidity: " + str(humidity))
                                self.sendCharacteristic("humidity", humidity, time.time())
                                self.lastHumidityTime = updateTime
                                self.updateTime = updateTime
                    elif message["value"] == "27":
                        updateTime = message["data"]["val"]["updateTime"] 
                        if updateTime != self.lastUltravioletTime and time.time() - updateTime < TIME_CUTOFF:
                            ultraviolet = message["data"]["val"]["value"] 
                            if ultraviolet is not None:
                                self.cbLog("debug", "onZwaveMessage, ultraviolet: " + str(ultraviolet))
                                self.sendCharacteristic("ultraviolet", ultraviolet, time.time())
                                self.lastUltravioletTime = updateTime
                                self.updateTime = updateTime
                elif message["commandClass"] == "48":
                    if message["value"] == "1":
                        updateTime = message["data"]["level"]["updateTime"]
                        if updateTime != self.lastBinaryTime and time.time() - updateTime < TIME_CUTOFF:
                            if message["data"]["level"]["value"]:
                                b = "on"
                            else:
                                b = "off"
                            self.cbLog("debug", "onZwaveMessage, alarm: " + b)
                            self.sendCharacteristic("binary_sensor", b, time.time())
                            self.lastBinaryTime = updateTime
                            self.updateTime = updateTime
                elif message["commandClass"] == "128":
                    updateTime = message["data"]["last"]["updateTime"]
                    if updateTime != self.lastBatteryTime and time.time() - updateTime < TIME_CUTOFF:
                        battery = message["data"]["last"]["value"] 
                        self.cbLog("debug", "battery: " + str(battery))
                        msg = {"id": self.id,
                               "status": "battery_level",
                               "battery_level": battery}
                        self.sendManagerMessage(msg)
                        self.sendCharacteristic("battery", battery, time.time())
                        self.lastBatteryTime = updateTime
                        self.updateTime = updateTime
                elif message["commandClass"] == "132":
                    self.cbLog("debug", "device woke up")
                    self.updateTime = message["data"]["updateTime"]
            except Exception as ex:
                self.cbLog("warning", "onZwaveMessage, unexpected message: " + str(message))
                self.cbLog("warning", "Exception: " + str(type(ex)) + str(ex.args))

    def onAppInit(self, message):
        self.cbLog("debug", "onAppInit, req = " + str(message))
        resp = {"name": self.name,
                "id": self.id,
                "status": "ok",
                "service": [{"characteristic": "binary_sensor", "interval": 0, "type": "pir"},
                            {"characteristic": "temperature", "interval": 0},
                            {"characteristic": "luminance", "interval": 0},
                            {"characteristic": "humidity", "interval": 0},
                            {"characteristic": "ultraviolet", "interval": 0},
                            {"characteristic": "connected", "interval": 0},
                            {"characteristic": "battery", "interval": BATTERY_CHECK_INTERVAL}],
                "content": "service"}
        self.sendMessage(resp, message["id"])
        self.setState("running")

    def onAppRequest(self, message):
        self.cbLog("debug", "onAppRequest, message: " + str(json.dumps(message, indent=4)))
        # Switch off anything that already exists for this app
        for a in self.apps:
            if message["id"] in self.apps[a]:
                self.apps[a].remove(message["id"])
        # Now update details based on the message
        for f in message["service"]:
            if message["id"] not in self.apps[f["characteristic"]]:
                self.apps[f["characteristic"]].append(message["id"])
                if f["characteristic"] != "battery" and f["characteristic"] != "binary_sensor":
                    # This is now redundant for this sensor as it is not polled
                    if "interval" in f:
                        if f["interval"] <= MIN_INTERVAL:
                            self.intervals[f["characteristic"]] = MIN_INTERVAL
                        elif self.intervals[f["characteristic"]] == MAX_INTERVAL and f["interval"] > MIN_INTERVAL:
                            self.intervals[f["characteristic"]] = int(f["interval"])
                        elif f["interval"] < self.intervals[f["characteristic"]]:
                            self.intervals[f["characteristic"]] = int(f["interval"])
                for i in self.intervals:
                    if self.pollInterval < MIN_INTERVAL:
                        self.pollInterval = self.intervals[i]
                    elif self.intervals[i] < self.pollInterval:
                        self.pollInterval = self.intervals[i]
                self.intervalChanged = True
        self.cbLog("debug", "onAppRequest, apps: " + str(self.apps))
        self.cbLog("debug", "onAppRequest, pollInterval: " + str(self.pollInterval))
        self.cbLog("debug", "onAppRequest. intervals " + str(json.dumps(self.intervals, indent=4)))

    def onAppCommand(self, message):
        self.cbLog("debug", "onAppCommand, req: " + str(message))
        if "data" not in message:
            self.cbLog("warning", "app message without data: " +  str(message))
        else:
            self.cbLog("warning", "This is a sensor. Message not understood: " + str(message))

    def onConfigureMessage(self, config):
        """Config is based on what apps are to be connected.
            May be called again if there is a new configuration, which
            could be because a new app has been added.
        """
        self.cbLog("debug", "onConfigureMessage, config: " + str(config))
        self.setState("starting")

if __name__ == '__main__':
    Adaptor(sys.argv)
