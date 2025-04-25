import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Optional, Tuple, List, Union, Any

from .config import (YAW_MULTIPLIER, PITCH_MULTIPLIER, ROLL_MULTIPLIER, 
                    WIDTH_FACTOR, YAW_THRESHOLD, PITCH_THRESHOLD, 
                    ROLL_THRESHOLD, CENTERING_TOLERANCE)


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
        
        # Cache for frame skipping/reuse
        self._last_frame_result = None
        self._frame_count = 0
        
        # 3D model points for solvePnP
        # Key facial landmarks in 3D space (normalized)
        self.model_points = np.array([
            (0.0, 0.0, 0.0),       # Nose tip (origin)
            (0.0, -63.6, -12.5),   # Chin
            (-43.3, 32.7, -26.0),  # Left eye left corner
            (43.3, 32.7, -26.0),   # Right eye right corner
            (-28.9, -28.9, -24.1), # Left mouth corner
            (28.9, -28.9, -24.1)   # Right mouth corner
        ], dtype=np.float32)
        
        # Corresponding facial landmark indices in MediaPipe
        # Nose tip, chin, left eye corner, right eye corner, left mouth, right mouth
        self.face_landmarks_indices = [1, 152, 33, 263, 61, 291]
        
        # Camera matrix (will be set based on frame dimensions)
        self.camera_matrix = None
        self.dist_coeffs = np.zeros((4, 1))  # Assuming no lens distortion
        
    def _enhance_low_light(self, frame: np.ndarray) -> np.ndarray:
        """
        Enhance frames in low light conditions for better landmark detection
        
        Args:
            frame: Input camera frame
            
        Returns:
            Enhanced frame
        """
        # Simple contrast and brightness adjustment
        return cv2.convertScaleAbs(frame, alpha=1.2, beta=15)
        
    def _get_largest_face(self, multi_face_landmarks) -> Tuple[Any, float]:
        """
        Find the largest face in the frame (closest to camera)
        
        Args:
            multi_face_landmarks: List of detected face landmarks from MediaPipe
            
        Returns:
            Tuple of (landmark, size) for the largest face
        """
        largest_face = None
        largest_area = 0
        
        for i, landmarks in enumerate(multi_face_landmarks):
            # Calculate bounding box
            x_coords = [lm.x for lm in landmarks.landmark]
            y_coords = [lm.y for lm in landmarks.landmark]
            
            # Find min/max coordinates
            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)
            
            # Calculate area
            area = (max_x - min_x) * (max_y - min_y)
            
            # Update if this face is larger
            if area > largest_area:
                largest_area = area
                largest_face = landmarks
                
        return largest_face, largest_area
    
    def get_head_pose_3d(self, frame: np.ndarray) -> dict:
        """
        Estimate head pose using solvePnP for true 3D angles
        
        Args:
            frame: Input camera frame (BGR)
            
        Returns:
            Dictionary with yaw, pitch, roll in degrees and pose_label
        """
        h, w, _ = frame.shape
        
        # Update camera matrix if needed (focal length based on frame size)
        if self.camera_matrix is None:
            focal_length = w
            center = (w / 2, h / 2)
            self.camera_matrix = np.array(
                [[focal_length, 0, center[0]],
                 [0, focal_length, center[1]],
                 [0, 0, 1]], dtype=np.float32
            )
            
        # Convert to RGB and process
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        # Prepare default result
        pose_result = {
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "pose_label": "Unknown",
            "face_detected": False,
            "is_centered": False,
            "rotation_vector": None,
            "translation_vector": None
        }
        
        if not results.multi_face_landmarks:
            return pose_result
            
        # Get largest face if multiple faces detected
        if len(results.multi_face_landmarks) > 1:
            face_landmarks, _ = self._get_largest_face(results.multi_face_landmarks)
        else:
            face_landmarks = results.multi_face_landmarks[0]
        
        # Map 2D points from face landmarks
        image_points = np.array([
            (face_landmarks.landmark[idx].x * w, face_landmarks.landmark[idx].y * h)
            for idx in self.face_landmarks_indices
        ], dtype=np.float32)
        
        # Solve for pose
        success, rotation_vector, translation_vector = cv2.solvePnP(
            self.model_points, image_points, self.camera_matrix, self.dist_coeffs
        )
        
        if not success:
            return pose_result
            
        # Convert rotation vector to rotation matrix
        rotation_mat, _ = cv2.Rodrigues(rotation_vector)
        
        # Extract Euler angles (yaw, pitch, roll) in degrees
        proj_mat = np.hstack((rotation_mat, translation_vector))
        euler_angles = self._rotation_matrix_to_euler_angles(rotation_mat) * 180 / np.pi
        
        # Assign values from Euler angles
        pitch, yaw, roll = euler_angles
        
        # Determine pose based on thresholds
        if abs(yaw) > YAW_THRESHOLD:
            pose_label = "Left" if yaw > 0 else "Right"
        elif abs(pitch) > PITCH_THRESHOLD:
            pose_label = "Down" if pitch > 0 else "Up"
        else:
            pose_label = "Forward"
        
        # Check centering
        nose = face_landmarks.landmark[1]
        nose_screen_x = int(nose.x * w)
        nose_screen_y = int(nose.y * h)
        center_x = w // 2
        center_y = h // 2
        tolerance = CENTERING_TOLERANCE * w
        
        is_centered = (abs(nose_screen_x - center_x) < tolerance and
                      abs(nose_screen_y - center_y) < tolerance)
        
        # Update result with calculated values
        pose_result.update({
            "yaw": yaw,
            "pitch": pitch,
            "roll": roll,
            "pose_label": pose_label,
            "face_detected": True,
            "is_centered": is_centered,
            "rotation_vector": rotation_vector,
            "translation_vector": translation_vector
        })
        
        return pose_result
        
    def _rotation_matrix_to_euler_angles(self, R):
        """
        Convert rotation matrix to Euler angles
        
        Args:
            R: Rotation matrix
            
        Returns:
            Numpy array with Euler angles [pitch, yaw, roll]
        """
        # Check if the rotation matrix has gimbal lock
        sy = np.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
        singular = sy < 1e-6
        
        if not singular:
            x = np.arctan2(R[2, 1], R[2, 2])  # pitch
            y = np.arctan2(-R[2, 0], sy)      # yaw
            z = np.arctan2(R[1, 0], R[0, 0])  # roll
        else:
            x = np.arctan2(-R[1, 2], R[1, 1])
            y = np.arctan2(-R[2, 0], sy)
            z = 0
            
        return np.array([x, y, z])
        
    def get_head_pose_simple(self, frame: np.ndarray, skip_frames: int = 0) -> dict:
        """
        Estimate head pose simply based on nose and eye positions (no solvePnP)
        Args:
            frame: Input camera frame (BGR)
            skip_frames: Number of frames to skip processing (reuse last result)
        Returns:
            Dictionary with yaw, pitch, roll and pose_label
        """
        # If frame skipping is enabled and not first frame
        if skip_frames > 0 and self._last_frame_result is not None:
            self._frame_count += 1
            if self._frame_count % (skip_frames + 1) != 0:
                return self._last_frame_result
                
        # Reset frame counter if we're processing this frame
        self._frame_count = 0
        
        # Enhance frame for better detection in low light
        enhanced_frame = self._enhance_low_light(frame)
        
        # Convert to RGB (MediaPipe requires RGB input)
        rgb_frame = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)
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
            # Cache and return result
            self._last_frame_result = pose_result
            return pose_result
            
        # If multiple faces, get largest
        if len(results.multi_face_landmarks) > 1:
            face_landmarks, _ = self._get_largest_face(results.multi_face_landmarks)
        else:
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
        yaw_offset = (nose_x - eye_center_x) * w  # pixel offset
        yaw = yaw_offset / (w * WIDTH_FACTOR) * YAW_MULTIPLIER
        
        # When looking down, nose is below the midpoint between eyes and mouth
        face_height = mouth_center_y - eye_center_y
        pitch_offset = (nose_y - eye_center_y - face_height/2)
        # Invert the pitch value so positive means looking up
        pitch = -pitch_offset * PITCH_MULTIPLIER
        
        # Rough roll estimation
        eye_diff_y = (left_eye.y - right_eye.y) * w
        roll = eye_diff_y * ROLL_MULTIPLIER

        # Determine pose with thresholds from config
        if yaw < -YAW_THRESHOLD:
            pose_label = "Left"
        elif yaw > YAW_THRESHOLD:
            pose_label = "Right"
        elif pitch < -PITCH_THRESHOLD:  # Looking down (negative pitch after inversion)
            pose_label = "Down"
        elif pitch > PITCH_THRESHOLD:   # Looking up (positive pitch after inversion)
            pose_label = "Up"
        else:
            pose_label = "Forward"

        # Check centering (for Forward pose)
        nose_screen_x = int(nose.x * w)
        nose_screen_y = int(nose.y * h)
        center_x = w // 2
        center_y = h // 2
        tolerance = CENTERING_TOLERANCE * w

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
        
        # Cache this result for frame skipping
        self._last_frame_result = pose_result

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
            
            # If we have 3D pose data, visualize the head orientation
            if "rotation_vector" in pose_result and pose_result["rotation_vector"] is not None:
                self._draw_pose_axes(annotated_frame, pose_result)
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
        
    def _draw_pose_axes(self, frame: np.ndarray, pose_result: dict, axis_length: float = 50.0) -> None:
        """
        Draw 3D axes on the face to visualize head orientation
        
        Args:
            frame: Image to draw on
            pose_result: Result from get_head_pose_3d containing rotation/translation
            axis_length: Length of the axes to draw in pixels
        """
        h, w, _ = frame.shape
        
        # If camera matrix not set, initialize it
        if self.camera_matrix is None:
            focal_length = w
            center = (w / 2, h / 2)
            self.camera_matrix = np.array(
                [[focal_length, 0, center[0]],
                 [0, focal_length, center[1]],
                 [0, 0, 1]], dtype=np.float32
            )
        
        rotation_vector = pose_result["rotation_vector"]
        translation_vector = pose_result["translation_vector"]
        
        # Define axis points
        axis_points = np.float32([[axis_length, 0, 0],
                                  [0, axis_length, 0],
                                  [0, 0, axis_length]])
        
        # Project 3D points to image plane
        imgpts, jac = cv2.projectPoints(axis_points, rotation_vector, translation_vector, 
                                        self.camera_matrix, self.dist_coeffs)
        
        # Get nose point as origin
        nose = tuple(np.int32(imgpts[0].ravel()))
        
        # Draw axes
        origin = tuple(np.int32(translation_vector.ravel()[:2]))
        
        # Draw X axis in red
        xpt = tuple(np.int32(imgpts[0].ravel()))
        cv2.line(frame, origin, xpt, (0, 0, 255), 3)
        
        # Draw Y axis in green
        ypt = tuple(np.int32(imgpts[1].ravel()))
        cv2.line(frame, origin, ypt, (0, 255, 0), 3)
        
        # Draw Z axis in blue
        zpt = tuple(np.int32(imgpts[2].ravel()))
        cv2.line(frame, origin, zpt, (255, 0, 0), 3)