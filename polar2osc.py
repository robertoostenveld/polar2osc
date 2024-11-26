"""
This script is an adaptation of the polarbelt module from the EEGsynth software, see <https://github.com/eegsynth/eegsynth>.

Copyright (C) 2024, Robert Oostenveld 
Copyright (C) 2017-2024 EEGsynth project

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import asyncio
from bleak import BleakClient, BleakScanner
from pythonosc import udp_client

# the data can be sent simultaneously to multiple OSC receivers, for example to the osc2similarity.py script and to TouchDesigner
OSC_HOST = ["127.0.0.1", "127.0.0.1"]
OSC_PORT = [8000, 10000]

# you can add multiple Polar H9 addresses here
# for testing purposes you can also add the same Polar H9 address multiple times
ADDRESS = []
ADDRESS.append("818AFE80-3652-4DBA-5192-88128E5FAB3D")  # Robert
# ADDRESS.append("C8BC000D-146F-6939-9C5F-9F657F308E1E")  # Sharon 1
# ADDRESS.append("8023FA31-F440-FABA-5D50-8A64D06B1EC7")  # Sharon 2
# ADDRESSES.append(...)
# ADDRESSES.append(...)

#############################################################################
# no changes should be needed below this line
#############################################################################

UUID_HEARTRATE = "2A37"
UUID_MODEL_NUMBER = "2A24"

clients = []    # list of OSC clients
belts = []      # list of Polar H9 belts

class PolarClient:

    def __init__(self, address, index, scan=False):
        self.address = address      # the address is a string like 818AFE80-3652-4DBA-5192-88128E5FAB3D
        self.index = index          # the one-based index is used to distinguish between multiple belts/people
        self.previous_ibi = None    # the previous interbeat interval

        # BLE client
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.ble_client = BleakClient(self.address, loop=self.loop)

        if scan:
            # show a list of all available devices, only needed once
            self.loop.run_until_complete(self.discover())


    async def discover(self):
        devices = await BleakScanner.discover()
        print("================= Available devices =================")
        for d in devices:
            print(d)
        print("=====================================================")


    async def connect(self):
        print("Trying to connect to Polar belt {0} ...".format(self.address))
        await self.ble_client.connect()
        await self.ble_client.start_notify(UUID_HEARTRATE, self.data_handler)
        print("Connected to Polar belt")


    def start(self):
        asyncio.ensure_future(self.connect())
        # self.loop.run_forever()


    def stop(self):
        asyncio.ensure_future(self.ble_client.stop_notify(UUID_HEARTRATE))
        asyncio.ensure_future(self.ble_client.disconnect())
        print("Disconnected from Polar belt {0} ...".format(self.address))


    def data_handler(self, sender, data):  # sender is unused but required by Bleak API
        """
        data has up to 6 bytes:
        byte 1: flags
            00 = only HR
            16 = HR and IBI(s)
        byte 2: HR
        byte 3 and 4: IBI1 (if present)
        byte 5 and 6: IBI2 (if present)
        byte 7 and 8: IBI3 (if present)
        etc.

        Polar H10 Heart Rate Characteristics
        (UUID: 00002a37-0000-1000-8000-00805f9b34fb):
            + Energy expenditure is not transmitted
            + HR only transmitted as uint8, no need to check if HR is
              transmitted as uint8 or uint16 (necessary for bpm > 255)
        Acceleration and raw ECG only available via Polar SDK
        """
        global clients
        bytes = list(data)
        hr = None
        ibis = []
        if bytes[0] == 00:
            hr = data[1]
        if bytes[0] == 16:
            hr = data[1]
            for i in range(2, len(bytes), 2):
                ibis.append(data[i] + 256 * data[i + 1])

        # give feedback to the console
        print("belt={0}, hr={1}, ibis={2}".format(self.index, hr, ibis))

        # send the heart rate data to the OSC receivers
        if hr:
            oscaddress = "/polar/{0}/hr".format(self.index)
            for recipient in clients:
                recipient.send_message(oscaddress, hr)
        for ibi in ibis:
            oscaddress = "/polar/{0}/ibi".format(self.index)
            for recipient in clients:
                recipient.send_message(oscaddress, ibi)
    
            # compute the heart rate variability (HRV) in milliseconds
            if self.previous_ibi:
                hrv = abs(ibi - self.previous_ibi)
                oscaddress = "/polar/{0}/hrv".format(self.index)
                for recipient in clients:
                    recipient.send_message(oscaddress, hrv)
            # remember the current interbeat interval for the next iteration
            self.previous_ibi = ibi
    

if __name__ == "__main__":
    # the following section connects multiple OSC clients
    for host, port in zip(OSC_HOST, OSC_PORT):
        print('Connecting to OSC server on {0}:{1} ...'.format(host, port))
        clients.append(udp_client.SimpleUDPClient(host, port))
        print('Connected to OSC server')

    # the following section connects multiple Polar H9 belts
    try:
        for addr, index in zip(ADDRESS, range(len(ADDRESS))):
            first = (index==0)  # only do the BLE scan for the first belt
            belts.append(PolarClient(addr, index+1, scan=first))    # use a one-based index for the belts
        for belt in belts:
            belt.start()
        for belt in belts:
            belt.loop.run_forever()
    except (SystemExit, KeyboardInterrupt, RuntimeError):
        for belt in belts:
            belt.stop()

    sys.exit()
