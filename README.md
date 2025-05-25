# Nebby
---
Measurement toolkit for identifying congestion control algorithms in the wild

## Dependancies: 
1. Mahimahi ([install instructions here](http://mahimahi.mit.edu/))
2. Use pip to install : matplotlib, pprint, textwrap, datetime.
3. Install google-chrome since all selenium clients use chrome. 

## Running tests:
1. Update choice of client in ```scripts/client.sh```.
2. Launch ```scripts/run_test.sh <descriptor> <pre-ow-delay> <post-ow-delay> <bottleneck linkspeed in Kbps> <Buffer size in BDP>``` For example, ```./run_test.sh sample-test 1 50 200 2```.
3. Run a post test analysis using ```analysis/pif-tcp-perflow.py <descriptor>```. For example, ```python3 pif-tcp-perflow.py sample-test```.

#### Running flow semantic analysis
4. Run ```analysis/semantics-perflow.py <descriptor>```. For example, ```python3 semantics-perflow.py sample-test```.  The summary json file, summary text file and the charts will be stored in ```Nebby/logs/results/``` as ```<descriptor>.json, <descriptor>.txt and <descriptor>.png```. 

5. To get the detailed information about the port, go to ```Nebby\analysis```. Run ```python3 port_info.py <descriptor>```. This file reads the json data file and asks you for the port you want the info about. Enter the port number and press enter to look at the data for that port.

### Notes:
* Run ```scripts/clean.sh``` to clear old files, queues, etc. before a fresh test
* While measuring video, choose a relatively higher bandwidth (>500kbps). 200kbps is sufficient for static webpages.

### (Darshil Notes)
For training,
```
1. cd local_sv
2. sudo ./setup_cca.sh
3. cd ..
3a. Make sure to adjust the ip based on the container's ip. 
4. ./nebby-train.sh
5. ./rename-files.sh
6. ./nebby-train.sh (with capture portion commented out)
```

