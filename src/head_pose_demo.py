import cv2
import time
from pathlib import Path

from .head_pose_detector import HeadPoseDetector
from .camera_handler import CameraHandler

def run_head_pose_demo():
    """
    Run a demo of head pose detection using the webcam
    """
    # Initialize camera
    camera = CameraHandler()
    if not camera.start():
        print("Failed to start camera")
        return
        
    # Initialize head pose detector
    head_pose = HeadPoseDetector()
    
    # Process frames from camera
    def process_frame(frame):
        # Get head pose
        pose_result = head_pose.get_head_pose_simple(frame)
        
        # Draw pose information on frame
        annotated_frame = head_pose.draw_pose_info(frame, pose_result)
        
        return annotated_frame
    
    # Show preview with pose detection
    print("Starting head pose detection demo...")
    print("Position your head and observe the pose detection.")
    print("Press 'q' to quit")
    
    camera.show_preview(
        window_name="Head Pose Detection", 
        process_frame=process_frame,
        show_fps=True
    )
    
if __name__ == "__main__":
    run_head_pose_demo() 