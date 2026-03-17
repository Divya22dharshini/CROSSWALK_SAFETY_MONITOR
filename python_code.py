from ultralytics import YOLO
import cv2, numpy as np, time
from opcua import Server
from datetime import datetime

# ------------------------ VIDEO SOURCE ------------------------
ESP_STREAM = "http://10.153.146.211:81/stream"

print("[INFO] Starting ESP32-CAM stream...")
cap = cv2.VideoCapture(ESP_STREAM)
if not cap.isOpened():
    print("ERROR: Cannot access ESP32-CAM stream.")
    exit()

# ------------------------ YOLO MODEL ------------------------
model = YOLO("yolov8n.pt")
PERSON = {"person"}
VEHICLE = {"car", "truck", "bus", "motorbike"}

W, H = 1280, 720

# ------------------------ CROSSWALK DETECT ------------------------
def detect_crosswalk(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0,0,180), (180,50,255))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_RECT,(9,9)),
                            iterations=2)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    largest = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(largest) < 3000:
        return None

    x, y, w, h = cv2.boundingRect(largest)
    if w / float(h) < 1.5:
        return None

    return x, y, w, h

# ------------------------ OPC-UA SERVER ------------------------
server = Server()
server.set_endpoint("opc.tcp://0.0.0.0:4840/")
server.set_server_name("CrosswalkMonitorOPCUA")

ns = server.register_namespace("CrosswalkMonitor")
root = server.get_objects_node()
cw_obj = root.add_object(ns, "CrosswalkData")

# Variables
var_cw_detected = cw_obj.add_variable(ns, "CrosswalkDetected", 0)
var_cw_x        = cw_obj.add_variable(ns, "Crosswalk_X", 0)
var_cw_y        = cw_obj.add_variable(ns, "Crosswalk_Y", 0)
var_cw_w        = cw_obj.add_variable(ns, "Crosswalk_Width", 0)
var_cw_h        = cw_obj.add_variable(ns, "Crosswalk_Height", 0)
var_p_total     = cw_obj.add_variable(ns, "TotalPersons", 0)
var_p_on_cw     = cw_obj.add_variable(ns, "PersonsOnCrosswalk", 0)
var_v_total     = cw_obj.add_variable(ns, "TotalVehicles", 0)

for v in [var_cw_detected, var_cw_x, var_cw_y, var_cw_w, var_cw_h,
          var_p_total, var_p_on_cw, var_v_total]:
    v.set_writable()

server.start()
print("[INFO] OPC-UA server started:", server.endpoint.geturl())

# ------------------------ MAIN LOOP ------------------------
crosswalk = None
cw_candidates = []
CW_FRAMES = 25

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            print("[WARN] Stream lost. Attempting reconnect...")
            time.sleep(1)
            cap = cv2.VideoCapture(ESP_STREAM)
            continue

        frame = cv2.resize(frame, (W, H))

        # ---- Lock crosswalk once ----
        if crosswalk is None:
            box = detect_crosswalk(frame)
            if box:
                cw_candidates.append(box)
            if len(cw_candidates) >= CW_FRAMES:
                avg = np.mean(np.array(cw_candidates), axis=0)
                crosswalk = tuple(map(int, avg))
                print("[INFO] Crosswalk detected:", crosswalk)

        # ---------------- YOLO DETECTION ----------------
        result = model(frame, verbose=False)[0]

        total_persons = 0
        persons_on_cw = 0
        total_vehicles = 0

        for b in result.boxes:
            cls = int(b.cls[0])
            label = model.names[cls]
            x1, y1, x2, y2 = map(int, b.xyxy[0])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # Person logic
            if label in PERSON:
                total_persons += 1
                if crosswalk:
                    x, y, w, h = crosswalk
                    if x <= cx <= x+w and y <= cy <= y+h:
                        persons_on_cw += 1
                cv2.rectangle(frame, (x1,y1),(x2,y2),(0,255,0),2)

            # Vehicle logic
            elif label in VEHICLE:
                total_vehicles += 1
                cv2.rectangle(frame, (x1,y1),(x2,y2),(255,0,0),2)

        # ---------------- WRITE TO OPC-UA ----------------
        if crosswalk:
            x, y, w, h = crosswalk
            var_cw_detected.set_value(1)
            var_cw_x.set_value(x)
            var_cw_y.set_value(y)
            var_cw_w.set_value(w)
            var_cw_h.set_value(h)
        else:
            var_cw_detected.set_value(0)
            var_cw_x.set_value(0)
            var_cw_y.set_value(0)
            var_cw_w.set_value(0)
            var_cw_h.set_value(0)

        var_p_total.set_value(total_persons)
        var_p_on_cw.set_value(persons_on_cw)
        var_v_total.set_value(total_vehicles)

        # ---------------- DISPLAY ----------------
        cv2.putText(frame, f"Persons: {total_persons}", (10,25),
                    cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,255),2)
        cv2.putText(frame, f"On Crosswalk: {persons_on_cw}", (10,55),
                    cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,255),2)
        cv2.putText(frame, f"Vehicles: {total_vehicles}", (10,85),
                    cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,255),2)

        if crosswalk:
            x, y, w, h = crosswalk
            cv2.rectangle(frame, (x,y),(x+w,y+h),(0,0,255),3)

        cv2.imshow("Crosswalk Monitor", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass

finally:
    cap.release()
    cv2.destroyAllWindows()
    server.stop()
    print("[INFO] OPC-UA server stopped.")