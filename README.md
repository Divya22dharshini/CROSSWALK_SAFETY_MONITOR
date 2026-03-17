PROJECT OVERVIEW :
The project is based on the development of an intelligent crosswalk monitoring system based on Coligo AI. 
The application is aimed at enhancing the safety of pedestrians and assisting with smarter traffic control through the analysis of real-time camera feeds and delivering valuable real-time information. 
The issue with industrial automation that is solved here is that there is no automated and real-time footage of pedestrian crossings. 
In most places, there are either human oversight or programmed time, which may cause unsafe situations when individuals or vehicles act in an unpredictable manner. 
The given project will help fill this gap by offering the automatic detection and sharing of data to make the operations safer and more efficient. 
The system can detect crosswalks, number people and vehicles, and share this information immediately using a no-code platform with the assistance of Coligo AI. 

RASPBERRY-PI SETUP

The system consists of two main Python scripts that work together to provide intelligent crosswalk safety monitoring:

### Windows PC Component (python_code.py)
This script runs on a Windows machine and handles video processing and object detection:
- Captures real-time video feed from an ESP32-CAM camera stream
- Uses YOLOv8 (YOLOv8n.pt model) for detecting persons and vehicles in the video
- Detects the crosswalk area using HSV color thresholding and morphological operations
- Exposes detection data via an OPC-UA server running on port 4840
- Publishes variables including: total persons, persons on crosswalk, total vehicles, and crosswalk coordinates

### Raspberry Pi Component (RASPBERRY_CODE.py)
This script runs on a Raspberry Pi and manages the physical traffic control:
- Connects as an OPC-UA client to the Windows PC server
- Reads real-time data about persons detected on the crosswalk
- Controls GPIO pins for traffic lights (vehicle red/yellow/green, pedestrian red/green) and a buzzer
- Runs a timed traffic cycle: 10 seconds pedestrian phase followed by 20 seconds vehicle phase
- Activates the buzzer during vehicle phase if persons are detected on the crosswalk for enhanced safety

The two components communicate over the network using OPC-UA protocol, enabling real-time synchronization between AI-powered video analysis and automated traffic control. 