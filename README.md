# POLAR2OSC

This repository contains two Python scripts designed to provide real-time audience engagement feedback. A sufficiently large selection of people in the audience are wearing a Polar H9/H10 heart rate belt. The basic idea is that if they all pay attention to the performance and are similarly exited (or bored) hy it, their heart rates will increase or decerase simultaneously. The data from the Polar belts worn by th edifferent audience members is collected and combined by one script, and the similarity in the _fluctuations_ of the heart-rate and of the inter-beat-interval is computed by another script.

The communication is implemented using Open Sound Control (OSC) and the heart rate, inter-beat-intervals and similarity scores are sent to a software that provides the feedback, such as TouchDesigner. The feedback software can be running on another computer.

The `polar2osc.py` script receives heart rate and inter-beat interval data over Bluetooth from the Polar H9/H10 belts. It computes the heart rate variability from the inter-beat intervals. It transmits the heart rate and variability using OSC to another process that analyzes and/or visualize the heart data.

The `polar2similarity.py` script receives the updates of the heart rate and variability over OSC, organizes them as a time series in a matrix (one row per person wearing a Polar belt), and at fixed intervals computes the similarity between these time series. The resulting similarity scores are sent using OSC to the software that provides the feedback, such a TouchDesigner.

Besides the feedback on the _engagement_ provided by the synchronicity between people, the _exitement_ of the people can be estimated from the actual heart rate and variability.

See also <https://en.wikipedia.org/wiki/Interbeat_interval> and <https://en.wikipedia.org/wiki/Heart_rate_variability>.

## Installation

Open an Anaconda terminal and type

```console
conda create -n polar2osc 'python>=3' 'numpy>=2'
conda activate polar2osc
pip install bleak
pip install python-osc
```

This installation only needs to be done one. On subsequent occasions you would activate the conda environment that you have set up using

```console
conda activate polar2osc
```

## Execution

Edit the `polar2osc.py` script to configure the list of addresses of the Polar H9 belt/belts that you want to use and to set the IP addresses and ports on which the OSC server is listening. One OSC connection is to be configured for the `polar2similarity.py` script, another OSC connection can be made to the feedback software.

Edit the `polar2similarity.py` script to configure the address of the incoming and outgoing OSC IP addresses and ports. There are some parameters for the similarity computation that can be tweaked.

Open an Anaconda terminal and type

```console
conda activate polar2osc
python polar2osc.py
```

Open another Anaconda terminal and type

```console
conda activate polar2osc
python polar2similarity.py
```

You should keep an eye open for warning and error messages that might appear in the terminal.

To stop the software, you have to press ctrl-c.

## Copyright

This is an adaptation of the polarbelt module from the EEGsynth software, see <https://github.com/eegsynth/eegsynth>.

Copyright (C) 2024, Robert Oostenveld 
Copyright (C) 2017-2024 EEGsynth project

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.
