# POLAR2OSC

The `polar2osc.py` script receives heart-rate and inter-beat interval data over Bluetooth from one or multiple Polar H9 belts. It transmits these using OSC (Open Sound Control) to another process that can analyze and/or visualize the heart data.

The `osc2similarity.py` script receives each update of the heart rate and inter-beat-interval, organizes it as a time series in a matrix, and once per second computes the similarity between the time series. The resulting similarity scores for the heart rate and inter-beat-interval time series are sent using OSC to TouchDesigner.

## Installation

```console
pip install bleak
pip install python-osc
```

## Execution

Edit the `polar2osc.py` code to configure the address/addresses of the Polar H9 belt/belts that you want to use and to set the IP address (or localhost) and UDP port on which the OSC server is listening.

## Copyright

This is an adaptation of the polarbelt module from the EEGsynth software, see <https://github.com/eegsynth/eegsynth>.

Copyright (C) 2024, Robert Oostenveld
Copyright (C) 2017-2024 EEGsynth project

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.
