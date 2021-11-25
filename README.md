# dd-to-osc
Converts a Datadog monitor into OSC messages

## requirements
- Datadog API and APP keys must be added to environment variables as DATADOG_API_KEY and DATADOG_APP_KEY respectively. 
- run pip3 install -r requirements.txt

## usage
`python3 dd_to_osc.py --ip <IP ADDRESS OF OSC SERVER> --port <PORT OF OSC SERVER> --monitor <DATADOG MONITOR ID> --scope <MONITOR SCOPE (REQUIRED ONLY IF MULTIPLE SCOPES AVAILABLE)> --value <OSC channel for monitor query values> --threshold <OSC channel for monitor threshold statuses>`

## vcv rack usage
The vcv rack patch in `dd-to-osc-vcv-rack.vcv` is meant to provide a way to experience the effects of the python script. By default the patch is running an OSC server on localhost with port 7051. You can learn how to install VCV Rack and VCV Rack plugins at https://community.vcvrack.com/t/getting-started-with-vcv-rack/747 The required plugins for this patch will appear as a pop up when opening `dd-to-osc-vcv-rack.vcv`.