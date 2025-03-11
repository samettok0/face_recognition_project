import cv2
import face_recognition
import numpy as np

# Open webcam
video_capture = cv2.VideoCapture(0)

while True:
    ret, frame = video_capture.read()
    
    # Debug: Print frame details
    print(f"Frame shape: {frame.shape}, dtype: {frame.dtype}")

    # Ensure frame is valid
    if not ret or frame is None:
        print("Error: Couldn't capture frame")
        continue

    # Convert to RGB (OpenCV loads images in BGR format)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Explicitly ensure image is 8-bit uint format
    rgb_frame = np.array(rgb_frame, dtype=np.uint8)

    # Debug: Print frame properties before detection
    print(f"Processed Frame shape: {rgb_frame.shape}, dtype: {rgb_frame.dtype}")

    # Detect faces
    face_locations = face_recognition.face_locations(rgb_frame)

    # Draw rectangles around detected faces
    for (top, right, bottom, left) in face_locations:
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

    # Display the video feed
    cv2.imshow("Webcam Face Detection", frame)

    # Exit on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Release webcam and close OpenCV windows
video_capture.release()
cv2.destroyAllWindows()