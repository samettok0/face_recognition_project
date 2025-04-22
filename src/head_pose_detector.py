import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Optional, Tuple


class HeadPoseDetector:
    """Class for detecting and analyzing head pose using MediaPipe Face Mesh."""
    
    def __init__(self, static_image_mode: bool = False, max_num_faces: int = 1, 
                 min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5):
        """
        Initialize the head pose detector.
        
        Args:
            static_image_mode: Whether to treat input as static images (vs video)
            max_num_faces: Maximum number of faces to detect
            min_detection_confidence: Minimum confidence for face detection
            min_tracking_confidence: Minimum confidence for face tracking
        """
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=static_image_mode,
            max_num_faces=max_num_faces,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
    def get_head_pose_simple(self, frame: np.ndarray) -> dict:
        """
        Estimate head pose simply based on nose and eye positions (no solvePnP)
        Args:
            frame: Input camera frame (BGR)
        Returns:
            Dictionary with yaw, pitch, roll and pose_label
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        pose_result = {
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "pose_label": "Unknown",
            "face_detected": False,
            "is_centered": False
        }

        if not results.multi_face_landmarks:
            return pose_result

        face_landmarks = results.multi_face_landmarks[0]
        h, w, _ = frame.shape

        # Get key landmarks
        nose = face_landmarks.landmark[1]
        left_eye = face_landmarks.landmark[33]
        right_eye = face_landmarks.landmark[263]
        mouth_left = face_landmarks.landmark[61]
        mouth_right = face_landmarks.landmark[291]

        # X coordinates
        nose_x = nose.x
        left_eye_x = left_eye.x
        right_eye_x = right_eye.x

        eye_center_x = (left_eye_x + right_eye_x) / 2.0

        # Y coordinates
        nose_y = nose.y
        eye_center_y = (left_eye.y + right_eye.y) / 2.0
        mouth_center_y = (mouth_left.y + mouth_right.y) / 2.0

        # Estimate yaw: nose horizontal offset from eye center
        # Significantly increase sensitivity by adjusting multiplier
        yaw_offset = (nose_x - eye_center_x) * w  # pixel offset
        yaw = yaw_offset / (w * 0.05) * 30  # Much higher sensitivity for left/right detection
        
        # FIXING: Invert the pitch calculation
        # When looking down, nose is below the midpoint between eyes and mouth
        face_height = mouth_center_y - eye_center_y
        pitch_offset = (nose_y - eye_center_y - face_height/2)
        # Invert the pitch value so positive means looking up
        pitch = -pitch_offset * 500  # rough scaling with inverted value
        
        # Rough roll estimation (optional)
        eye_diff_y = (left_eye.y - right_eye.y) * w
        roll = eye_diff_y * 0.5  # very rough

        # Determine pose with adjusted thresholds for better left/right detection
        if yaw < -10:  # Reduced threshold from -15 to -10
            pose_label = "Left"
        elif yaw > 10:  # Reduced threshold from 15 to 10
            pose_label = "Right"
        elif pitch < -10:  # Looking down (negative pitch after inversion)
            pose_label = "Down"
        elif pitch > 10:   # Looking up (positive pitch after inversion)
            pose_label = "Up"
        else:
            pose_label = "Forward"

        # Check centering (for Forward pose)
        nose_screen_x = int(nose.x * w)
        nose_screen_y = int(nose.y * h)
        center_x = w // 2
        center_y = h // 2
        tolerance = 0.1 * w  # 10% screen width

        is_centered = (abs(nose_screen_x - center_x) < tolerance and
                      abs(nose_screen_y - center_y) < tolerance)

        pose_result.update({
            "yaw": yaw,
            "pitch": pitch,
            "roll": roll,
            "pose_label": pose_label,
            "face_detected": True,
            "is_centered": is_centered
        })

        return pose_result
        
    def draw_pose_info(self, frame: np.ndarray, pose_result: dict) -> np.ndarray:
        """
        Draw head pose information on the frame
        
        Args:
            frame: Input camera frame
            pose_result: Result from get_head_pose_simple
            
        Returns:
            Frame with pose information drawn
        """
        h, w, _ = frame.shape
        y_offset = 30
        
        # Create a copy of the frame to avoid modifying the original
        annotated_frame = frame.copy()
        
        if pose_result["face_detected"]:
            # Draw pose label
            cv2.putText(
                annotated_frame, 
                f"Pose: {pose_result['pose_label']}", 
                (10, y_offset), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, 
                (0, 255, 0) if pose_result["pose_label"] == "Forward" else (0, 165, 255), 
                2
            )
            
            # Draw centering info if looking forward
            if pose_result["pose_label"] == "Forward":
                cv2.putText(
                    annotated_frame, 
                    f"Centered: {pose_result['is_centered']}", 
                    (10, y_offset + 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.7, 
                    (0, 255, 0) if pose_result["is_centered"] else (0, 0, 255), 
                    2
                )
                
            # Draw numeric values
            cv2.putText(
                annotated_frame, 
                f"Yaw: {pose_result['yaw']:.1f} Pitch: {pose_result['pitch']:.1f}", 
                (10, y_offset + 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.6, 
                (255, 255, 255), 
                1
            )
        else:
            cv2.putText(
                annotated_frame, 
                "No face detected", 
                (10, y_offset), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, 
                (0, 0, 255), 
                2
            )
            
        return annotated_frame