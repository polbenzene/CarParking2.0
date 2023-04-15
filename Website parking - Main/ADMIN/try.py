import cv2

# Load the YOLO object detection model
net = cv2.dnn.readNetFromDarknet('yolov3.cfg', 'yolov3.weights')

# Define the classes that the YOLO model can detect
classes = ['car']

# Load the video
cap = cv2.VideoCapture('carpark.mp4')

while True:
    # Read a frame from the video
    ret, frame = cap.read()
    
    if ret:
        # Run the YOLO object detector on the frame
        blob = cv2.dnn.blobFromImage(frame, 1/255, (416, 416), swapRB=True)
        net.setInput(blob)
        detections = net.forward()
        
        # Loop through the detections and extract the coordinates of the car bounding box
        for detection in detections:
            class_id = int(detection[1])
            confidence = detection[2]
            
            if classes[class_id] == 'car' and confidence > 0.5:
                x, y, w, h = detection[3:7] * [frame.shape[1], frame.shape[0], frame.shape[1], frame.shape[0]]
                x = int(x - w/2)
                y = int(y - h/2)
                w = int(w)
                h = int(h)
                
                # Draw a rectangle around the car
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
        # Display the frame
        cv2.imshow('Frame', frame)
        cv2.waitKey(1)
        
    else:
        break
        
cap.release()
cv2.destroyAllWindows()
