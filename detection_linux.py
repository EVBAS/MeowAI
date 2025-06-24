import cv2
from ultralytics import YOLO
import time
import requests
import json
import os
import adafruit_dht
import time
import board
from gpiozero import DigitalInputDevice
from gpiozero import LED
from picamera2 import Picamera2

def upload(address,list,img_path):
    headers = {'Content-Type': 'application/json'}

    response1 = requests.post(
        f"{address}/submit-data", 
        data=json.dumps(list),
        headers=headers)
    time.sleep(1)

    file_path = img_path

    if os.path.exists(file_path):
        with open(file_path, 'rb') as img_file:
            response2 = requests.post(
                f"{address}/upload-photo/0", 
                files={'file': img_file})
    else:
        print(f"Error: File {file_path} does not exist.")
        response2 = None

    print(response1, response1.text)
    if response2:
        print(response2, response2.text)

def predict(chosen_model, img, classes=[], conf=0.,verbose = False):
    if classes:
        results = chosen_model.predict(img, classes=classes, conf=conf,verbose=verbose)
    else:
        results = chosen_model.predict(img, conf=conf, verbose=verbose)

    return results


def predict_and_detect(chosen_model, img, classes=[], conf=0.8, class_counts = {"cat": 0, "pood": 0}, verbose=True):
    results = predict(chosen_model, img, classes, conf = conf,verbose = verbose)

    for result in results:
        for box in result.boxes:
            
            class_name = result.names[int(box.cls[0])]
            if class_name in class_counts:
                class_counts[class_name] += 1
            else:
                class_counts[class_name] = 1
            cv2.rectangle(img, (int(box.xyxy[0][0]), int(box.xyxy[0][1])),
                          (int(box.xyxy[0][2]), int(box.xyxy[0][3])), (255, 0, 0), 2)
            cv2.putText(img, f"{result.names[int(box.cls[0])]}",
                        (int(box.xyxy[0][0]), int(box.xyxy[0][1]) - 10),
                        cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0), 1)
                        
    return img, results, class_counts

model = YOLO("MeowAI_ncnn_model")
starting_time = None
last_detecting_time = time.time()
duration = None
duration_list = {"Present": False, 
                 "duration" : None, 
                 "wet area": False, 
                 "moisture": 0, 
                 "temperature": 26, 
                 "no. of faeces": 0}
present = False
sending_state = False
address = "http://172.19.12.75:8080/"
picam2 = Picamera2()
picam2.preview_configuration.main.size=(980,540) #full screen : 3280 2464
picam2.preview_configuration.main.format = "RGB888" #8 bits
picam2.start()
object_frame = None
dht11 = adafruit_dht.DHT11(board.D2)
moisture_sensor = DigitalInputDevice(17)
led_red = LED(21)
led_green = LED(20)
led_blue = LED(16)
t = 0
m = 0
h = 0
while True:
    frame = picam2.capture_array()

    new_frame, results, class_counts = predict_and_detect(model, frame, classes=[], conf=0.55, verbose=False, class_counts = {"cat": 0, "poop": 0})

    if class_counts["cat"] > 0:
        print(class_counts["cat"])
        if present is False:
            starting_time = time.time()
            duration = None
            present = True
            duration_list["Present"] = present
            object_frame = new_frame

    elif present is True:
        duration = time.time() - starting_time

        if duration < 10:
            present = False
            duration_list["duration"] = 0
            duration_list["Present"] = present
            object_frame = new_frame
        else:
            duration_list["duration"] = int(duration)
            duration_list["Present"] = present
            present = False

        starting_time = None
        sending_state = True
    
    elif time.time()-last_detecting_time > 12 and present is False:
        duration_list["duration"] = 0
        duration_list["Present"] = present
        sending_state = True
        object_frame = new_frame
    try:
        t = int(dht11.temperature)
        h = dht11.humidity
        m = moisture_sensor.is_active
        if m:
            m = False
        else:
            m = True
        duration_list["wet area"] = m
        duration_list["moisture"] = h
        duration_list["temperature"] = t
        duration_list["no. of faeces"] = class_counts["poop"]
    except:
        pass
    if t > 28:
        led_red.value = 255
        print("too hot!")
    else:
        led_red.value = 0

    if m is False:
        led_green.value = 255
    else:
        led_green.value = 0

    if h > 125:
        led_blue.value = 255
    else:
        led_blue.value = 0

    if sending_state is True:
        print(duration_list)
        cv2.imwrite("frame.jpg", object_frame)
        upload(address, duration_list, "frame.jpg")
        sending_state = False
        last_detecting_time = time.time()
        
    cv2.imshow("Meow", new_frame)
    if cv2.waitKey(1) == ord("q"):
        break
picam2.stop()
