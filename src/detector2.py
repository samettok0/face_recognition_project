import cv2
import face_recognition
from src.camera import Camera
from src.utils import draw_face_boxes

def main():
    camera = Camera()
    while True:
        frame = camera.get_frame()
        if frame is None:
            break

        face_locations = face_recognition.face_locations(frame)
        draw_face_boxes(frame, face_locations)

        cv2.imshow("Face Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()