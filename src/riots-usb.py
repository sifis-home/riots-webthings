#from __future__ import division

from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols.basic import Int8StringReceiver
from twisted.internet import reactor
from twisted.internet.asyncioreactor import AsyncioSelectorReactor

from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.twisted.websocket import WebSocketServerFactory

import websockets

from twisted.internet.serialport import SerialPort
import serial
import time
import codecs
import signal
import asyncio
import json

from Crypto.Cipher import AES
import random
import math
import sys
from enum import Enum

import serial.tools.list_ports

serInst = None
tcpInst = None
wsInst = None
ser = None
riotsJsonData = None

riots_url = "mama.riots.fi"
port = 8000

def handler(signum, frame):
  reactor.stop()
  exit(1)

signal.signal(signal.SIGINT, handler)

# Riots Serial class for handling the connection with Mama
class RiotsSerial(Int8StringReceiver):
  def __init__(self):
    global serInst, tcpInst, wsInst
    serInst = self
    self.databuf = []
    self.tracebuf = {}
    self.empty_buffer = True
    self.session_crypto = None
    self.state = "NO_KEYS"

  def connectionMade(self):
    plain = "24" # SERVER_REQUESTS_INTRODUCTION
    msg = codecs.decode(plain, 'hex')
    self.sendString(msg)

    # Data received from Riots devices towards Cloud
  def stringReceived(self, data):
    global riotsJsonData
    buf = codecs.encode(data, 'hex')
    mama_op = buf[0:2]
    # print("stringReceived", buf)

    # CLIENT_INTRODUCTION from USB Dongle
    if mama_op == b'01':
      self.base = buf[2:10]
      self.core = buf[10:18]
      self.chal = buf[18:26]
      self.block = 0
      self.tcp = tcpInst
      if self.tcp:
        self.tcp.mac = self.base
        self.tcp.core = self.core
        self.tcp.chal = self.chal
        self.tcp.clientInit()
      # Clear data buffer
      self.databuf = []
      self.empty_buffer = True

    # CLIENT_VERIFICATION from USB Dongle 
    # This data structure is used by Mama Dongle to verify itself
    elif mama_op == b'02':
      self.tcp.sendData(data) # Forward to Riots TCP (cloud)

    # CLIENT_DATA_POST, CLIENT_SAVED_DATA_POST from USB Dongle
    # This function is used to post new data from devices to Cloud
    elif mama_op == b'03' or mama_op == b'04':
      if self.tcp:
        if self.state == "KEYS_RECEIVED":
          netid = int.from_bytes(data[14:16], "big")
          data_type = data[1]

          # WIRELESS_DEBUG START
          if data_type == 128:
            debug_id = int((data[14].encode("hex") + data[15].encode("hex")), 16)
            if self.msg_len < 12:
              debug_data = data[4:3+self.msg_len]
            packet_count = int(data[3].encode("hex"))
            if packet_count > 1:
              #more data coming, push to table
              if debug_id in self.tracebuf:
                #new trace, while previous is not complete
                print("OLD OTA DEBUG id="+str(debug_id)+":", self.tracebuf[debug_id]['data'])
              self.tracebuf[debug_id] = {'data':debug_data, 'pkg_count':packet_count}
            else:
              print(" ["+str(debug_id).rjust(4, '0') +"]:", debug_data)

          # WIRELESS_DEBUG MESSAGE
          elif data_type == 129:
            debug_id = int((data[14].encode("hex") + data[15].encode("hex")), 16)
            if debug_id in self.tracebuf:
              if self.msg_len < 12:
                debug_data = data[4:4+self.msg_len]
              packet_nro = int(data[3].encode("hex"), 16)
              self.tracebuf[debug_id]['data'] = self.tracebuf[debug_id]['data'] + debug_data
              if packet_nro +1 == self.tracebuf[debug_id]['pkg_count']:
                # received everything
                print(" ["+str(debug_id).rjust(4, '0') +"]:", self.tracebuf[debug_id]['data'][:-1])
                del(self.tracebuf[debug_id])
          # TIMEOUT
          elif data_type == 74: #and "12" == data[7].encode("hex"):
            print("TIMEOUT")
          # DATA MESSAGE

          # Data from Riots Device
          elif data_type == 1:
            #print("Client data from", netid)
            index = data[3]
            value = int.from_bytes(data[4:8], "big")
            coeff = data[8]
            if(coeff > 127):
              coeff = coeff - 256

            for idx, device in enumerate(riotsJsonData):
              if(int(device["id"]) == netid):
                # print("Got data from: ", device["title"], ", #", index)
                for propert in device["properties"]:
                  if(int(device["properties"][propert]["id"]) == index):
                    val = round(value * pow(10, coeff),1)
                    # print("Got data from: ", device["title"])
                    # print("Data type: ", device["properties"][propert]["title"])
                    if(propert == "status" and int(val) == 0):
                      val = "off"
                    elif(propert == "status" and int(val) == 1):
                      val = "heating"

                    if device["properties"][propert]["value"] != val:
                      # Encrypt and forward updated data to Riots TCP (cloud)
                      self.tcp.sendData(bytes([data[0]])+self.session_crypto.encrypt(data[1:17]))

                    # print(device["properties"][propert]["value"], "updated to", val)
                    device["properties"][propert]["value"] = val
                    if wsInst is not None:
                      # print("Send updated data to Clients")
                      sendData = {}
                      sendData['thermostat'] = idx
                      sendData['propertyType'] = device["properties"][propert]["propertyType"]
                      sendData['value'] = val
                      wsInst.sendMessage(json.dumps(sendData, ensure_ascii = False).encode('utf8'), False)
                    return

          # Encrypt and forward message to Riots TCP (cloud)
          self.tcp.sendData(bytes([data[0]])+self.session_crypto.encrypt(data[1:17]))

        else:
          # Forward to Riots TCP as plain data
          self.tcp.sendData(data)

    # MAMA_SERIAL_CONNECT ('ce') from USB dongle
    elif mama_op == b'ce':
      # send 'cd' back
      plain = "cd"
      msg = codecs.decode(plain, 'hex')
      self.sendString(msg)

    # MAMA_SERIAL_DISCONNECT ('dc') from USB dongle
    elif mama_op == b'dc':
      tcpInst.transport.loseConnection()

    # MAMA_SERIAL_SEND_MORE_DATA ('5d') from USB dongle
    elif mama_op == b'5d':
      if len(self.databuf) > 0:
        self.sendOneFromBuffer()
      else:
        self.empty_buffer = True

    # KEYS_RECEIVED ('5a') from USB dongle
    elif mama_op == b'5a':
      self.state = "KEYS_RECEIVED"
      self.session_crypto = AES.new(data[1:17], AES.MODE_ECB)

  def sendData(self, msg):
    # Decrypt message
    if self.state == "KEYS_RECEIVED":
      msg = msg[0:1]+self.session_crypto.decrypt(msg[1:])

    # Chop message
    if len(msg) > 32:
      plain = "da" # MAMA_SERIAL_DATA_PART
      op = codecs.decode(plain, 'hex')
      # Add length
      msg = bytes([len(msg)])+msg
      for i in range(int(math.ceil(len(msg)/32))):
        if len(msg) > 32:
          self.databuf.append(op+msg[0:32])
          msg = msg[32:]
        else:
          self.databuf.append(op+msg)
    else:
      self.databuf.append(msg)

    if self.empty_buffer:
      self.sendOneFromBuffer()

    self.empty_buffer = False

  def sendOneFromBuffer(self):
    send_msg = self.databuf.pop(0)
    self.sendString(send_msg)



class RiotsWebSocket(WebSocketServerProtocol):
  global riotsJsonData
  global serInst

  def onClose(self, wasClean, code, reason):    
    print("WebSocket connection closed")
    global wsInst
    wsInst = None

  def onOpen(self):
    print("WebSocket connection opened")
    global wsInst
    if wsInst is None:
      wsInst = self


  def onMessage(self, payload, isBinary):
    obj = json.loads(payload)
    t_id = obj["thermostat"]
    t_prop = obj["propertyType"]
    t_data = obj["value"]
    if(t_prop == "TargetTemperatureProperty"):
      if(int(riotsJsonData[t_id]["properties"]["set_temperature"]["value"]) != int(t_data)):
        # set temperature changed, send to device
        nplain  = riotsJsonData[t_id]["address"] # receiver
        for i in range(11):
          nplain += '{:2x}'.format(22)  # Padding
        buf = codecs.decode(nplain, 'hex')
        checksum = 0
        for chk in buf:
          checksum ^= chk
        nplain += '{:02x}'.format(checksum)
        new_msg = codecs.decode(('22' + nplain), 'hex')
        serInst.sendString(new_msg)
        key = riotsJsonData[t_id]["key"].encode('UTF-8')
        key = codecs.decode(key, 'hex')
        crypto = AES.new(key, AES.MODE_ECB)
        plain  = '{:02x}'.format(2)  # CLOUD_EVENT_DOWN
        plain += '{:02x}'.format(6)  # Length
        plain += '{:02x}'.format(0)  # Value id
        plain += '{:08x}'.format(int(t_data)) # data
        plain += '{:02x}'.format(0)  # COEFFICIENT
        plain += '{:06x}'.format(12)  # PADDING
        plain += '{:04x}'.format(66)  # PADDING
        plain += '{:04x}'.format(int(riotsJsonData[t_id]["id"])) # Reveiver ID
        buf = codecs.decode(plain, 'hex')
        checksum = 0
        for chk in buf:
          checksum ^= chk
        plain += '{:02x}'.format(checksum)
        crypted = crypto.encrypt(codecs.decode(plain, 'hex'))
        new_msg = codecs.decode('23', 'hex') + crypted
        serInst.sendString(new_msg)


# Riots TCP class for handling the Mama connection with cloud
class RiotsTcp(Int8StringReceiver):

  def __init__(self):
    global serInst, tcpInst
    tcpInst = self
    self.state = "INIT"
    self.shared = None
    self.prev_op = ""
    self.next_receiver = ""

    # Create a queue that we will use to store our "workload".
    # queue = asyncio.Queue()
    # queue.put_nowait("Hello World")

    print("Attach RIOTS USB (ctrl+c to cancel)")
    ser = None
    while ( ser == None ):
      for p in (serial.tools.list_ports.comports()):
        if "MCP" in p[1]:
          serport = p[0].strip()
          try:
            ser = serial.Serial(serport, baudrate=38400, timeout=5)
          except:
            pass
          if ser:
            print("Device connected to port:" + serport)
            ser.close()
            SerialPort(RiotsSerial(), serport, reactor, baudrate=38400)
            break
    self.ser = serInst


  def sendData(self, msg):
    self.sendString(msg)

  def connectionMade(self):
    print("TCP connected")    
    if self.ser:
      self.state = "CONNECTED"
    else:
      print("No serial yet!")

  def connectionLost(self, reason):
    print("TCP disconnected")
    self.ser.state = "INIT"
    self.state = "INIT"

  def stringReceived(self, msg):
    # Forward to Riots Serial
    global serInst
    buf = codecs.encode(msg, 'hex')
    cloud_op = buf[0:2]

    if cloud_op == b'21':
      print("Connection OK")

    serInst.sendData(msg)

  def clientInit(self):
    self.ser.state = "INIT"
    self.state = "INIT"
    # Send client introduction to cloud
    op = codecs.decode('01', 'hex')
    msg = op + codecs.decode((self.mac+self.core+self.chal), 'hex')
    print("Connecting to Riots Cloud")
    self.sendString(msg)

# Client factory
class RiotsClientFactory(ReconnectingClientFactory):
  def startedConnecting(self, connector):
    self.maxDelay = 5

  def buildProtocol(self, addr):
    self.resetDelay()
    return RiotsTcp()

  def clientConnectionLost(self, connector, reason):
    print('Lost connection.')
    ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

  def clientConnectionFailed(self, connector, reason):
    print('Connection failed.')
    ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


# Mainloop
print("Starting Riots client")
reactor.connectTCP(riots_url, port, RiotsClientFactory())

print("Loading device configurations")
f = open('inc/riots-device-configuration.json')
riotsJsonData = json.load(f)
f.close()

factory = WebSocketServerFactory()
factory.protocol = RiotsWebSocket
reactor.listenTCP(8942, factory)

reactor.run()
