import cv2
from ultralytics import YOLO
import time
import requests
import json
import os

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
                f"{address}/upload-photo", 
                files={'file': img_file})
    else:
        print(f"Error: File {file_path} does not exist.")
        response2 = None

    print(response1, response1.text)
    if response2:
        print(response2, response2.text)

def predict(chosen_model, img, classes=[], conf=0.,verbose = True):
    if classes:
        results = chosen_model.predict(img, classes=classes, conf=conf,verbose=verbose)
    else:
        results = chosen_model.predict(img, conf=conf)

    return results


def predict_and_detect(chosen_model, img, classes=[], conf=0.8, counts = 0,verbose=True):
    results = predict(chosen_model, img, classes, conf = conf,verbose = verbose)

    for result in results:
        for box in result.boxes:
            cv2.rectangle(img, (int(box.xyxy[0][0]), int(box.xyxy[0][1])),
                          (int(box.xyxy[0][2]), int(box.xyxy[0][3])), (255, 0, 0), 2)
            cv2.putText(img, f"{result.names[int(box.cls[0])]}",
                        (int(box.xyxy[0][0]), int(box.xyxy[0][1]) - 10),
                        cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0), 1)
            counts += 1
                        
    return img, results, counts

model = YOLO("yolov8l.pt")
starting_time = None
last_detecting_time = time.time()
duration = None
duration_list = {"Present": False, 
                 "duration" : None, 
                 "wet area": False, 
                 "moisture": 0, 
                 "temperature": 26}
present = False
sending_state = False
address = "http://42.2.115.185:8080"
video = cv2.VideoCapture(0)
object_frame = None

while True:
    ret, frame = video.read()
    if not ret:
        break

    new_frame, results, counts = predict_and_detect(model, frame, classes=[0], conf=0.6,verbose=False)

    if counts > 0:
        if present is False:
            starting_time = time.time()
            duration = None
            present = True
            duration_list["present"] = present
            object_frame = new_frame

    elif present is True:
        duration = time.time() - starting_time

        if duration < 10:
            present = False
            duration_list["duration"] = 0
            duration_list["present"] = present
            object_frame = new_frame
        else:
            duration_list["duration"] = int(duration)
            duration_list["present"] = present
            present = False

        starting_time = None
        sending_state = True
    
    elif time.time()-last_detecting_time > 12 and present is False:
        duration_list["duration"] = 0
        duration_list["present"] = present
        sending_state = True
        object_frame = new_frame
        last_detecting_time = time.time()

        
    if sending_state is True:
        print(duration_list)
        cv2.imwrite("frame.jpg", object_frame)
        upload(address, duration_list, "frame.jpg")
        sending_state = False
        
    cv2.imshow("Meow", new_frame)
    if cv2.waitKey(1) == ord("q"):
        break

    
        

            




