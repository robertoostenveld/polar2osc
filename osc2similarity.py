"""
This script computes how similar the time series are of the heart rate and inter-beat-interval of multiple people wearing a Polar H9 belt.

Copyright (C) 2024, Robert Oostenveld

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import numpy as np
import asyncio
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
from pythonosc.udp_client import SimpleUDPClient

INCOMING_HOST = "localhost"
INCOMING_PORT=8001     # for receiving the heart rate and inter-beat-interval data
OUTGOING_HOST = "localhost"
OUTGOING_PORT=8000     # for sending the similarity scores

MAXBELTS = 20   # how many belts to keep track of
MAXTIME = 30    # how many seconds of data to keep track of
ALPHA = 0.5     # smoothing factor (between 0 and 1) for the exponential moving average, large means short memory, small means large memory, see https://en.wikipedia.org/wiki/Exponential_smoothing

NBELTS = 0      # this will automatically increment when more belts are seen
IBI = []        # list of the latest inter-beat intervals, one for each belt
HR = []         # list of the latest heart rates, one for each belt
IBI_MEAN = []   # exponential moving average of the inter-beat intervals
HR_MEAN = []    # exponential moving average of the heart rate
ACTIVE = []     # boolean list of the belts that are currently active


def incoming_osc_handler(address, *args):
    print(f"{address}: {args}")

    polar, belt, hr_or_ibi = address.split("/")
    belt = int(belt)
    while belt>NBELTS:
        # ensure that the lists are long enough to hold the data for the new belt
        IBI.append(None)
        HR.append(None)
        IBI_MEAN.append(None)
        HR_MEAN.append(None)
        ACTIVE.append(False)
        NBELTS += 1

    # the following uses a 0-based index
    belt = belt - 1
    if hr_or_ibi == "hr":
        if HR_MEAN[belt] is None:
            # this is the first value
            HR_MEAN[belt] = args[0]
        else:
            # update the exponential moving average with the latest value
            HR_MEAN[belt] = ALPHA*args[0] + (1-ALPHA)*HR_MEAN[belt]
        # remember the latest value
        HR[belt] = args[0]
        
    elif hr_or_ibi == "ibi":
        if IBI_MEAN[belt] is None:
            # this is the first value
            IBI_MEAN[belt] = args[0]
        else:
            # update the exponential moving average with the latest value
            IBI_MEAN[belt] = ALPHA*args[0] + (1-ALPHA)*IBI_MEAN[belt]
        # remember the latest value
        IBI[belt] = args[0]
    # flag this belt as active
    ACTIVE[belt] = True


dispatcher = Dispatcher()
dispatcher.map("/polar/*/*", incoming_osc_handler)

client = SimpleUDPClient(OUTGOING_HOST, OUTGOING_PORT)  # Create an OSC client that will send the similarity scores


async def loop_main():
    # these are matrices with the time series of the data, one row for each belt
    data_hr  = np.zeros((MAXBELTS, MAXTIME), dtype=np.float64)
    data_ibi = np.zeros((MAXBELTS, MAXTIME), dtype=np.float64)

    while True:
        # this runs at a fixed rate of once per second
        await asyncio.sleep(1)

        # update the matrices with the latest values, implemented as a rolling buffer
        selection = [i for i in range(NBELTS) if ACTIVE[i]]
        data_hr = np.roll(data_hr, 1, axis=1)
        data_ibi = np.roll(data_ibi, 1, axis=1)
        print("number of belts:", len(selection))
        for i in selection:
            # put the latest value in the first column, after subtracting the mean
            data_hr[i, 1] = HR[i] - HR_MEAN[i]
            data_ibi[i, 1] = IBI[i] - IBI_MEAN[i]

        # compute how similar the heart rate time series are 
        u, s, vh = np.linalg.svd(np.cov(data_hr[selection,:]), full_matrices=False)
        s = s / np.sum(s)
        client.send_message("/polar/similarity/hr", s)

        # compute how similar the inter-beat-interval time series are 
        u, s, vh = np.linalg.svd(np.cov(data_ibi[selection,:]), full_matrices=False)
        s = s / np.sum(s)
        client.send_message("/polar/similarity/ibi", s)


async def init_main():
    server = AsyncIOOSCUDPServer((INCOMING_HOST, INCOMING_PORT), dispatcher, asyncio.get_event_loop())
    transport, protocol = await server.create_serve_endpoint()  # Create datagram endpoint and start serving
    await loop_main()   # Enter the main loop of the program
    transport.close()   # Clean up the server
    client.close()      # Clean up client


if __name__ == "__main__":
    """ Start the main program """
    asyncio.run(init_main())
