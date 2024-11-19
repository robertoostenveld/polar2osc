import sys
import asyncio
from bleak import BleakClient, BleakScanner
from pythonosc import udp_client

OSC_HOST = "localhost"
OSC_PORT = 8000

ADDRESS = []
ADDRESS.append("818AFE80-3652-4DBA-5192-88128E5FAB3D")

# you can add multiple Polar H9 addresses here
# for testing purposes you can also add the same Polar H9 address multiple times
# ADDRESSES.append(...)
# ADDRESSES.append(...)

#############################################################################
# no changes should be needed below this line
#############################################################################

UUID_HEARTRATE = "2A37"
UUID_MODEL_NUMBER = "2A24"

class PolarClient:

    def __init__(self, address, index, scan=False):
        self.address = address      # the address is a string like 818AFE80-3652-4DBA-5192-88128E5FAB3D
        self.index = index          # the index is used to distinguish between multiple belts

        # BLE client
        self.loop = asyncio.get_event_loop()
        self.ble_client= BleakClient(self.address, loop=self.loop)

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

        # send the heart rate and each of the inter-beat intervals to the OSC server
        # the index (0, 1, 2, ...) is used to distinguish between multiple belts
        global osc
        if hr:
            oscaddress = "/polar/{0}/hr".format(self.index)
            osc.send_message(oscaddress, hr)
        for ibi in ibis:
            oscaddress = "/polar/{0}/ibi".format(self.index)
            osc.send_message(oscaddress, ibi)


if __name__ == "__main__":
    global osc
    print('Connecting to OSC server on {0}:{1} ...'.format(OSC_HOST, OSC_PORT))
    osc = udp_client.SimpleUDPClient(OSC_HOST, OSC_PORT) 
    print('Connected to OSC server')

    # the followingsection processes multiple Polar H9 belts
    belts = []
    try:
        for addr, index in zip(ADDRESS, range(len(ADDRESS))):
            first = (index==0)  # only do the BLE scan for the first belt
            belts.append(PolarClient(addr, index, scan=first))
        for belt in belts:
            belt.start()
        for belt in belts:
            belt.loop.run_forever()
    except (SystemExit, KeyboardInterrupt, RuntimeError):
        for belt in belts:
            belt.stop()

    sys.exit()
