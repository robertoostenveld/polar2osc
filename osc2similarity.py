"""
This script computes the similarity of the heart rate over multiple people wearing a Polar H9 belt.

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

# this is the local OSC address for receiving the heart rate and interbeat-interval data
INCOMING_HOST = "localhost"
INCOMING_PORT = 8001

# this is the remote OSC address to which the similarity scores are sent
OUTGOING_HOST = "localhost"
OUTGOING_PORT = 8000

MAXBELTS = 20   # how many belts to keep track of
NSAMPLES = 30   # how many data samples to keep track of
INTERVAL = 1.0  # update interval in seconds between data samples
ALPHA = 0.5     # smoothing factor (between 0 and 1) for the exponential moving average, large means short memory, small means large memory, see https://en.wikipedia.org/wiki/Exponential_smoothing

#############################################################################
# no changes should be needed below this line
#############################################################################

NBELTS = 0      # this will automatically increment when more belts are seen
HR = []         # list of the most recent heart rates, one for each belt
IBI = []        # list of the most recent interbeat intervals, one for each belt
HRV = []        # list of the most recent heart rate variabilities, one for each belt
ACTIVE = []     # boolean list of the belts that are currently active


def similarity(x):
    # compute the similarity between the time series in x
    mx = np.ma.masked_array(x, mask=np.isnan(x))        # make a masked array to ignore the missing values, indicated by NaN
    cx = np.ma.cov(mx)                                  # compute the covariance matrix                    
    u, s, vh = np.linalg.svd(cx, full_matrices=False)   # compute the singular value decomposition
    s = s / np.sum(s)                                   # normalize the singular values
    return s.tolist()                                   # return as a plain Python list with floats


def incoming_osc_handler(address, *args):
    print(f"{address}: {args}")

    # incoming messages are expected to be in the format /polar/X/hr or /polar/X/hrv, where X is the belt index (one-based)
    polar, belt, type = address.split("/")

    if type not in ["hr", "ibi", "hrv"]:
        # ignore this message
        return
    
    try:
        # the one-based belt index (1, 2, ...) is used to distinguish between multiple belts/people
        belt = int(belt)
    except ValueError:
        # ignore this message alltogether
        return
    
    while belt>NBELTS:
        # ensure that the lists are long enough to hold the data for the new belt
        HR.append(None)
        IBI.append(None)
        HRV.append(None)
        ACTIVE.append(False)
        NBELTS += 1

    # the following code uses a zero-based index
    belt = belt - 1

    if type == "hr":
        HR[belt] = args[0]
    elif type == "ibi":
        IBI[belt] = args[0]
    elif type == "hrv":
        HRV[belt] = args[0]

    # flag this belt as active
    ACTIVE[belt] = True


async def loop_main():
    global client

    # these are matrices with the time series of the data, one row for each belt
    # missing values are indicated by NaN
    data_hr  = np.zeros((MAXBELTS, NSAMPLES), dtype=np.float64) + np.nan
    data_ibi = np.zeros((MAXBELTS, NSAMPLES), dtype=np.float64) + np.nan
    data_hrv = np.zeros((MAXBELTS, NSAMPLES), dtype=np.float64) + np.nan

    while True:
        # the subsequent code runs once per second
        await asyncio.sleep(INTERVAL)

        # move all the previous values one column to the right
        data_hr = np.roll(data_hr, 1, axis=1)
        data_hrv = np.roll(data_hrv, 1, axis=1)
        data_ibi = np.roll(data_hrv, 1, axis=1)
    
        selection = [i for i in range(NBELTS) if ACTIVE[i]]
        print("number of active belts:", len(selection))
        for i in selection:
            # copy the latest known value into the first column
            data_hr[i, 1] = HR[i]
            data_ibi[i, 1] = IBI[i]
            data_hrv[i, 1] = HRV[i]

        # compute how similar the heart rate time series are 
        s = similarity(data_hr[selection,:])
        client.send_message("/polar/similarity/hr", s)
        print("similarity in HR: {0}".format(s))

        # compute how similar the interbeat interval time series are 
        s = similarity(data_ibi[selection,:])
        client.send_message("/polar/similarity/ibi", s)
        print("similarity in IBI: {0}".format(s))

        # compute how similar the heart rate variability time series are 
        s = similarity(data_hrv[selection,:])
        client.send_message("/polar/similarity/hrv", s)
        print("similarity in HRV: {0}".format(s))


async def init_main():
    global client

    dispatcher = Dispatcher()
    dispatcher.map("/polar/*/*", incoming_osc_handler)
    server = AsyncIOOSCUDPServer((INCOMING_HOST, INCOMING_PORT), dispatcher, asyncio.get_event_loop()) # this is for receiving the heart rate and interbeat interval data
    transport, protocol = await server.create_serve_endpoint()  # Create datagram endpoint and start serving
    client = SimpleUDPClient(OUTGOING_HOST, OUTGOING_PORT)  # this is for sending the similarity scores
    await loop_main()   # Enter the main loop of the program
    transport.close()   # Clean up the server
    client.close()      # Clean up client


if __name__ == "__main__":
    """ Start the main program """
    asyncio.run(init_main())
