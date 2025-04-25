import cv2
import time
import argparse
from pathlib import Path

from .head_pose_detector import HeadPoseDetector
from .camera_handler import CameraHandler

def run_head_pose_demo(use_3d_pose: bool = False, skip_frames: int = 1):
    """
    Run a demo of head pose detection using the webcam
    
    Args:
        use_3d_pose: Whether to use 3D pose estimation with solvePnP
        skip_frames: Process every Nth frame (0 = process all frames)
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
        if use_3d_pose:
            pose_result = head_pose.get_head_pose_3d(frame)
        else:
            pose_result = head_pose.get_head_pose_simple(frame, skip_frames=skip_frames)
        
        # Draw pose information on frame
        annotated_frame = head_pose.draw_pose_info(frame, pose_result)
        
        # Display additional info about which method is being used
        method_text = "3D Pose (solvePnP)" if use_3d_pose else f"Simple Pose (skipping {skip_frames} frames)"
        cv2.putText(
            annotated_frame,
            method_text,
            (10, annotated_frame.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1
        )
        
        return annotated_frame
    
    # Show preview with pose detection
    print("Starting head pose detection demo...")
    print(f"Using {'3D pose estimation (solvePnP)' if use_3d_pose else 'simple pose estimation'}")
    print(f"Frame processing: {f'every {skip_frames+1}th frame' if skip_frames > 0 else 'all frames'}")
    print("Position your head and observe the pose detection.")
    print("Press 'q' to quit")
    
    camera.show_preview(
        window_name="Head Pose Detection", 
        process_frame=process_frame,
        show_fps=True
    )

def main():
    """Command-line interface for the head pose demo"""
    parser = argparse.ArgumentParser(description="Head Pose Detection Demo")
    parser.add_argument("--3d", dest="use_3d", action="store_true", 
                        help="Use 3D pose estimation with solvePnP")
    parser.add_argument("--skip", type=int, default=1,
                        help="Process every Nth frame (0 = process all frames)")
    args = parser.parse_args()
    
    run_head_pose_demo(use_3d_pose=args.use_3d, skip_frames=args.skip)
    
if __name__ == "__main__":
    main() 