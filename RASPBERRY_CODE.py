import time
import threading
from opcua import Client
import RPi.GPIO as GPIO

# =========================================================
#               GPIO SETUP (Traffic Light)
# =========================================================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

RED_VEH = 17
YEL_VEH = 27
GRN_VEH = 22
RED_PED = 23
GRN_PED = 24
BUZZ = 25

all_pins = [RED_VEH, YEL_VEH, GRN_VEH, RED_PED, GRN_PED, BUZZ]
for p in all_pins:
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, GPIO.LOW)

# ---------------- TRAFFIC LIGHT FUNCTIONS ----------------
def vehicle_stop():
    GPIO.output(RED_VEH, GPIO.HIGH)
    GPIO.output(YEL_VEH, GPIO.LOW)
    GPIO.output(GRN_VEH, GPIO.LOW)

def vehicle_go():
    GPIO.output(RED_VEH, GPIO.LOW)
    GPIO.output(YEL_VEH, GPIO.LOW)
    GPIO.output(GRN_VEH, GPIO.HIGH)

def pedestrian_go():
    GPIO.output(GRN_PED, GPIO.HIGH)
    GPIO.output(RED_PED, GPIO.LOW)

def pedestrian_stop():
    GPIO.output(GRN_PED, GPIO.LOW)
    GPIO.output(RED_PED, GPIO.HIGH)

def buzzer_on():
    GPIO.output(BUZZ, GPIO.HIGH)

def buzzer_off():
    GPIO.output(BUZZ, GPIO.LOW)


# =========================================================
#               GLOBAL DATA (from OPC-UA)
# =========================================================
persons_on_crosswalk = 0
total_persons = 0
vehicle_session_active = False

# =========================================================
#               OPC-UA CLIENT THREAD
# =========================================================
OPC_URL = "opc.tcp://10.218.192.79:4840/"   # Windows-side server

def opcua_reader():
    global persons_on_crosswalk, total_persons

    while True:
        try:
            print("[PI] Connecting to OPC-UA server...")
            client = Client(OPC_URL)
            client.connect()
            print("[PI] Connected!")

            # Get CrosswalkData node
            objects = client.get_objects_node()

            crosswalk_node = None
            for child in objects.get_children():
                if child.get_display_name().Text == "CrosswalkData":
                    crosswalk_node = child
                    print("[PI] Found CrosswalkData node")
                    break

            if crosswalk_node is None:
                print("[PI-ERROR] CrosswalkData not found!")
                time.sleep(2)
                continue

            # Load all variables dynamically
            vars = {}
            for child in crosswalk_node.get_children():
                name = child.get_display_name().Text
                vars[name] = child
                print("[PI] Found variable:", name)

            required = ["PersonsOnCrosswalk", "TotalPersons"]
            for key in required:
                if key not in vars:
                    print("[PI-ERROR] Missing variable on server:", key)

            print("[PI] Starting read loop...")

            # Real-time read loop
            while True:
                persons_on_crosswalk = int(vars["PersonsOnCrosswalk"].get_value())
                total_persons = int(vars["TotalPersons"].get_value())

                print("[OPCUA] Persons Total =", total_persons,
                      "On Crosswalk =", persons_on_crosswalk)

                time.sleep(1)

        except Exception as e:
            print("[PI] Connection lost, retrying in 3 sec...", e)
            time.sleep(3)


# =========================================================
#               TRAFFIC LIGHT CONTROLLER
# =========================================================
def run_traffic_controller():
    global vehicle_session_active, persons_on_crosswalk

    CYCLES = 10

    for cycle in range(CYCLES):
        print("\n---- CYCLE", cycle + 1, "----")

        # Pedestrian phase
        print("[PI] Pedestrian session 10 sec")

        vehicle_session_active = False
        vehicle_stop()
        pedestrian_go()
        buzzer_off()

        for _ in range(10):
            time.sleep(1)

        # Vehicle phase
        print("[PI] Vehicle session 20 sec")

        vehicle_session_active = True
        vehicle_go()
        pedestrian_stop()

        for _ in range(20):
            if persons_on_crosswalk > 0:
                buzzer_on()
            else:
                buzzer_off()
            time.sleep(1)

        buzzer_off()

    GPIO.cleanup()
    print("[PI] Traffic Light system stopped")


# =========================================================
#                       MAIN
# =========================================================
def main():
    threading.Thread(target=opcua_reader, daemon=True).start()

    time.sleep(2)

    run_traffic_controller()


if __name__ == "__main__":
    main()