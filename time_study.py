import streamlit as st
import cv2
import time
import numpy as np
import mediapipe as mp
from collections import defaultdict
import threading
from datetime import datetime, timedelta

class WorkstationAnalyzer:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5, 
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Initialize analysis data
        self.reset_analysis()
        
        # Activity classification thresholds
        self.activity_thresholds = {
            'hand_above_shoulder': 0.1,  # Hand significantly above shoulder
            'hand_movement_speed': 0.05,  # Movement speed threshold
            'pose_stability': 0.03       # Stability threshold
        }
        
        self.previous_landmarks = None
        self.movement_history = []
        
    def reset_analysis(self):
        """Reset analysis data for new session"""
        self.analysis_data = {
            'session_start': time.time(),
            'cycle_start': None,
            'value_added_time': 0,
            'non_value_added_time': 0,
            'current_activity': None,
            'activity_history': [],
            'total_cycles': 0
        }
        
    def calculate_movement_speed(self, current_landmarks, previous_landmarks):
        """Calculate overall body movement speed"""
        if previous_landmarks is None:
            return 0
            
        total_movement = 0
        key_points = [
            self.mp_pose.PoseLandmark.LEFT_WRIST,
            self.mp_pose.PoseLandmark.RIGHT_WRIST,
            self.mp_pose.PoseLandmark.LEFT_ELBOW,
            self.mp_pose.PoseLandmark.RIGHT_ELBOW
        ]
        
        for point in key_points:
            curr = current_landmarks[point]
            prev = previous_landmarks[point]
            movement = np.sqrt((curr.x - prev.x)**2 + (curr.y - prev.y)**2)
            total_movement += movement
            
        return total_movement / len(key_points)
    
    def classify_activity(self, landmarks):
        """Enhanced rule-based activity classification"""
        # Get key landmarks
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        left_elbow = landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW]
        right_elbow = landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW]
        
        # Calculate movement speed
        movement_speed = self.calculate_movement_speed(landmarks, self.previous_landmarks)
        self.movement_history.append(movement_speed)
        if len(self.movement_history) > 10:  # Keep last 10 measurements
            self.movement_history.pop(0)
        
        avg_movement = np.mean(self.movement_history) if self.movement_history else 0
        
        # Classification rules
        shoulder_height = (left_shoulder.y + right_shoulder.y) / 2
        hands_elevated = (left_wrist.y < shoulder_height - 0.1) or (right_wrist.y < shoulder_height - 0.1)
        high_movement = avg_movement > self.activity_thresholds['hand_movement_speed']
        
        # Activity classification logic
        if hands_elevated and high_movement:
            if left_wrist.y < left_elbow.y or right_wrist.y < right_elbow.y:
                return 'VA: Assembly Work'
            else:
                return 'VA: Tool Operation'
        elif high_movement:
            return 'NVA: Material Handling'
        elif hands_elevated:
            return 'NVA: Reaching/Positioning'
        else:
            return 'NVA: Idle/Waiting'
    
    def analyze_frame(self, frame):
        """Analyze a single frame for pose and activity"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frame)
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            activity = self.classify_activity(landmarks)
            self.update_timers(activity)
            
            # Draw pose landmarks
            self.mp_drawing.draw_landmarks(
                frame, 
                results.pose_landmarks, 
                self.mp_pose.POSE_CONNECTIONS,
                self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                self.mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2)
            )
            
            # Add activity and timing information
            cv2.putText(frame, activity, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Add timing info
            total_time = time.time() - self.analysis_data['session_start']
            cv2.putText(frame, f"Session: {total_time:.1f}s", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            self.previous_landmarks = landmarks
            
        return frame, results.pose_landmarks is not None
    
    def update_timers(self, activity):
        """Update timing data based on current activity"""
        now = time.time()
        
        if self.analysis_data['current_activity'] != activity:
            # Record previous activity duration
            if self.analysis_data['cycle_start'] is not None:
                duration = now - self.analysis_data['cycle_start']
                
                if self.analysis_data['current_activity']:
                    if 'VA' in self.analysis_data['current_activity']:
                        self.analysis_data['value_added_time'] += duration
                    else:
                        self.analysis_data['non_value_added_time'] += duration
                    
                    # Record activity in history
                    self.analysis_data['activity_history'].append({
                        'activity': self.analysis_data['current_activity'],
                        'duration': duration,
                        'timestamp': now
                    })
            
            self.analysis_data['current_activity'] = activity
            self.analysis_data['cycle_start'] = now
    
    def get_current_stats(self):
        """Get current analysis statistics"""
        total_time = self.analysis_data['value_added_time'] + self.analysis_data['non_value_added_time']
        
        if total_time > 0:
            va_percentage = (self.analysis_data['value_added_time'] / total_time) * 100
            nva_percentage = (self.analysis_data['non_value_added_time'] / total_time) * 100
        else:
            va_percentage = nva_percentage = 0
        
        return {
            'total_time': total_time,
            'va_time': self.analysis_data['value_added_time'],
            'nva_time': self.analysis_data['non_value_added_time'],
            'va_percentage': va_percentage,
            'nva_percentage': nva_percentage,
            'current_activity': self.analysis_data['current_activity'] or 'Not Detected',
            'session_duration': time.time() - self.analysis_data['session_start']
        }
    
    def generate_detailed_report(self):
        """Generate comprehensive analysis report"""
        stats = self.get_current_stats()
        
        # Activity breakdown
        activity_summary = defaultdict(float)
        for record in self.analysis_data['activity_history']:
            activity_summary[record['activity']] += record['duration']
        
        report = f"""
# Workstation Analysis Report
**Session Duration:** {stats['session_duration']:.1f} seconds
**Analysis Period:** {stats['total_time']:.1f} seconds

## Efficiency Metrics
- **Value-Added Time:** {stats['va_time']:.1f}s ({stats['va_percentage']:.1f}%)
- **Non-Value-Added Time:** {stats['nva_time']:.1f}s ({stats['nva_percentage']:.1f}%)

## Activity Breakdown
"""
        
        for activity, duration in sorted(activity_summary.items(), key=lambda x: x[1], reverse=True):
            percentage = (duration / stats['total_time'] * 100) if stats['total_time'] > 0 else 0
            report += f"- **{activity}:** {duration:.1f}s ({percentage:.1f}%)\n"
        
        return report

# Streamlit App
def main():
    st.set_page_config(
        page_title="Workstation Analysis",
        page_icon="🏭",
        layout="wide"
    )
    
    st.title("🏭 Real-time Workstation Analysis")
    st.markdown("Monitor and analyze worker activities for process optimization")
    
    # Initialize session state
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = WorkstationAnalyzer()
    if 'is_running' not in st.session_state:
        st.session_state.is_running = False
    
    analyzer = st.session_state.analyzer
    
    # Control panel
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Reset Analysis"):
            analyzer.reset_analysis()
            st.success("Analysis data reset!")
    
    with col2:
        camera_source = st.selectbox("Camera Source", [0, 1, 2], index=0)
    
    with col3:
        confidence_threshold = st.slider("Detection Confidence", 0.1, 1.0, 0.5, 0.1)
    
    # Main content area
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("📹 Live Feed")
        camera_placeholder = st.empty()
        
        # Camera controls
        start_button = st.button("▶️ Start Analysis")
        stop_button = st.button("⏹️ Stop Analysis")
        
        if start_button:
            st.session_state.is_running = True
        if stop_button:
            st.session_state.is_running = False
    
    with col_right:
        st.subheader("📊 Real-time Stats")
        stats_placeholder = st.empty()
        
        st.subheader("🎯 Current Activity")
        activity_placeholder = st.empty()
    
    # Analysis section
    st.subheader("📈 Analysis Results")
    report_placeholder = st.empty()
    
    # Main processing loop
    if st.session_state.is_running:
        try:
            cap = cv2.VideoCapture(camera_source)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Update pose detection confidence
            analyzer.pose = analyzer.mp_pose.Pose(
                min_detection_confidence=confidence_threshold,
                min_tracking_confidence=confidence_threshold
            )
            
            while st.session_state.is_running:
                ret, frame = cap.read()
                if not ret:
                    st.error("Failed to capture from camera")
                    break
                
                # Analyze frame
                processed_frame, pose_detected = analyzer.analyze_frame(frame)
                
                # Display processed frame
                camera_placeholder.image(processed_frame, channels="BGR", use_column_width=True)
                
                # Update statistics
                stats = analyzer.get_current_stats()
                
                with stats_placeholder.container():
                    metric_col1, metric_col2 = st.columns(2)
                    with metric_col1:
                        st.metric("Value-Added Time", f"{stats['va_time']:.1f}s", 
                                f"{stats['va_percentage']:.1f}%")
                    with metric_col2:
                        st.metric("Non-Value-Added Time", f"{stats['nva_time']:.1f}s", 
                                f"{stats['nva_percentage']:.1f}%")
                
                # Update current activity
                activity_status = "🟢 Detected" if pose_detected else "🔴 Not Detected"
                activity_placeholder.info(f"**{stats['current_activity']}** - {activity_status}")
                
                # Update report
                if stats['total_time'] > 5:  # Only show report after 5 seconds of data
                    report_placeholder.markdown(analyzer.generate_detailed_report())
                
                time.sleep(0.1)  # Small delay to prevent overwhelming
            
            cap.release()
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.session_state.is_running = False
    
    # Instructions
    with st.expander("ℹ️ How to Use"):
        st.markdown("""
        1. **Select Camera Source**: Choose your camera (usually 0 for built-in camera)
        2. **Adjust Confidence**: Set detection sensitivity (higher = more strict)
        3. **Start Analysis**: Click "Start Analysis" to begin monitoring
        4. **Position Yourself**: Stand in front of the camera with your full body visible
        5. **Perform Activities**: The system will automatically classify your movements
        6. **View Results**: Monitor real-time statistics and detailed reports
        
        **Activity Classifications:**
        - **VA (Value-Added)**: Assembly work, tool operations
        - **NVA (Non-Value-Added)**: Reaching, waiting, idle time
        """)

if __name__ == "__main__":
    main()
