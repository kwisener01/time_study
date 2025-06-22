import cv2
import time
import numpy as np
import mediapipe as mp
from collections import defaultdict

class WorkstationAnalyzer:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.analysis_data = {
            'cycle_start': None,
            'value_added_time': 0,
            'non_value_added_time': 0,
            'current_activity': None
        }
        self.activity_definitions = {
            'VA': ['assembling', 'welding', 'installing'],
            'NVA': ['reaching', 'waiting', 'searching']
        }

    def classify_activity(self, landmarks):
        """Rule-based activity classification (expand with ML model later)"""
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_hand = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        
        # Example rule: If hand is above waist level = productive motion
        if right_hand.y < left_shoulder.y:
            return 'VA: assembling'
        else:
            return 'NVA: reaching'

    def analyze_frame(self, frame):
        results = self.pose.process(frame)
        if results.pose_landmarks:
            activity = self.classify_activity(results.pose_landmarks.landmark)
            self.update_timers(activity)
            
            # Draw skeleton and activity label
            mp.solutions.drawing_utils.draw_landmarks(
                frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
            cv2.putText(frame, activity, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return frame

    def update_timers(self, activity):
        now = time.time()
        if self.analysis_data['current_activity'] != activity:
            # Record previous activity duration
            if self.analysis_data['cycle_start']:
                duration = now - self.analysis_data['cycle_start']
                if 'VA' in activity:
                    self.analysis_data['value_added_time'] += duration
                else:
                    self.analysis_data['non_value_added_time'] += duration
            
            self.analysis_data['current_activity'] = activity
            self.analysis_data['cycle_start'] = now

    def generate_report(self):
        total = self.analysis_data['value_added_time'] + self.analysis_data['non_value_added_time']
        return f"""
        Process Analysis Report:
        Value-Added Time: {self.analysis_data['value_added_time']:.2f}s ({self.analysis_data['value_added_time']/total:.1%})
        Non-Value-Added Time: {self.analysis_data['non_value_added_time']:.2f}s ({self.analysis_data['non_value_added_time']/total:.1%})
        """

    def run(self):
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
                
            frame = self.analyze_frame(frame)
            cv2.imshow('Workstation Analysis', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()
        print(self.generate_report())

if __name__ == "__main__":
    analyzer = WorkstationAnalyzer()
    analyzer.run()