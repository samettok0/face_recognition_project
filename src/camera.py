import cv2

class Camera:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(self.camera_index)

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def is_opened(self):
        return self.cap.isOpened()