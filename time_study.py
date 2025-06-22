import streamlit as st
import numpy as np
import time
from datetime import datetime
import io
import base64

# Try to import optional dependencies with fallbacks
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    st.error("OpenCV not available. Please install opencv-python-headless")

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    st.error("MediaPipe not available. Please install mediapipe")

class MockWorkstationAnalyzer:
    """Simplified analyzer for demo purposes when dependencies aren't available"""
    
    def __init__(self):
        self.analysis_data = {
            'session_start': time.time(),
            'value_added_time': 0,
            'non_value_added_time': 0,
            'current_activity': 'Demo Mode',
            'activity_history': []
        }
        
    def simulate_analysis(self):
        """Simulate analysis for demo purposes"""
        import random
        activities = ['VA: Assembly Work', 'VA: Tool Operation', 'NVA: Reaching', 'NVA: Waiting']
        activity = random.choice(activities)
        
        # Simulate timing
        now = time.time()
        duration = random.uniform(1, 5)
        
        if 'VA' in activity:
            self.analysis_data['value_added_time'] += duration
        else:
            self.analysis_data['non_value_added_time'] += duration
            
        self.analysis_data['current_activity'] = activity
        self.analysis_data['activity_history'].append({
            'activity': activity,
            'duration': duration,
            'timestamp': now
        })
        
    def get_current_stats(self):
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
            'current_activity': self.analysis_data['current_activity'],
            'session_duration': time.time() - self.analysis_data['session_start']
        }

class WorkstationAnalyzer:
    """Full analyzer when all dependencies are available"""
    
    def __init__(self):
        if not (CV2_AVAILABLE and MEDIAPIPE_AVAILABLE):
            raise ImportError("Required dependencies not available")
            
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.analysis_data = {
            'session_start': time.time(),
            'cycle_start': None,
            'value_added_time': 0,
            'non_value_added_time': 0,
            'current_activity': None,
            'activity_history': []
        }
        
        self.previous_landmarks = None
        self.movement_history = []
    
    def calculate_movement_speed(self, current_landmarks, previous_landmarks):
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
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        left_elbow = landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW]
        right_elbow = landmarks[self.mp_pose.PoseLandmark.RIGHT_ELBOW]
        
        movement_speed = self.calculate_movement_speed(landmarks, self.previous_landmarks)
        self.movement_history.append(movement_speed)
        if len(self.movement_history) > 10:
            self.movement_history.pop(0)
        
        avg_movement = np.mean(self.movement_history) if self.movement_history else 0
        shoulder_height = (left_shoulder.y + right_shoulder.y) / 2
        hands_elevated = (left_wrist.y < shoulder_height - 0.1) or (right_wrist.y < shoulder_height - 0.1)
        high_movement = avg_movement > 0.05
        
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
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb_frame)
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            activity = self.classify_activity(landmarks)
            self.update_timers(activity)
            
            self.mp_drawing.draw_landmarks(
                frame, 
                results.pose_landmarks, 
                self.mp_pose.POSE_CONNECTIONS
            )
            
            cv2.putText(frame, activity, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            self.previous_landmarks = landmarks
            
        return frame, results.pose_landmarks is not None
    
    def update_timers(self, activity):
        now = time.time()
        
        if self.analysis_data['current_activity'] != activity:
            if self.analysis_data['cycle_start'] is not None:
                duration = now - self.analysis_data['cycle_start']
                
                if self.analysis_data['current_activity']:
                    if 'VA' in self.analysis_data['current_activity']:
                        self.analysis_data['value_added_time'] += duration
                    else:
                        self.analysis_data['non_value_added_time'] += duration
                    
                    self.analysis_data['activity_history'].append({
                        'activity': self.analysis_data['current_activity'],
                        'duration': duration,
                        'timestamp': now
                    })
            
            self.analysis_data['current_activity'] = activity
            self.analysis_data['cycle_start'] = now
    
    def get_current_stats(self):
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

def main():
    st.set_page_config(
        page_title="Workstation Analysis",
        page_icon="🏭",
        layout="wide"
    )
    
    st.title("🏭 Workstation Analysis System")
    
    # Check dependencies
    if not CV2_AVAILABLE or not MEDIAPIPE_AVAILABLE:
        st.warning("⚠️ Running in Demo Mode - Some dependencies are missing")
        st.info("""
        **Missing Dependencies:**
        - OpenCV: ❌ if CV2_AVAILABLE else ✅
        - MediaPipe: ❌ if MEDIAPIPE_AVAILABLE else ✅
        
        **To enable full functionality:**
        1. Install dependencies locally: `pip install opencv-python mediapipe`
        2. Run locally instead of on Streamlit Cloud
        """.replace("❌ if CV2_AVAILABLE else ✅", "✅" if CV2_AVAILABLE else "❌")
          .replace("❌ if MEDIAPIPE_AVAILABLE else ✅", "✅" if MEDIAPIPE_AVAILABLE else "❌"))
        
        # Use mock analyzer
        if 'mock_analyzer' not in st.session_state:
            st.session_state.mock_analyzer = MockWorkstationAnalyzer()
        
        analyzer = st.session_state.mock_analyzer
        
        # Demo interface
        st.subheader("📊 Demo Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎲 Simulate Activity"):
                analyzer.simulate_analysis()
                st.success("Activity simulated!")
        
        with col2:
            if st.button("🔄 Reset Demo"):
                st.session_state.mock_analyzer = MockWorkstationAnalyzer()
                st.success("Demo reset!")
        
        # Display stats
        stats = analyzer.get_current_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Value-Added Time", f"{stats['va_time']:.1f}s", f"{stats['va_percentage']:.1f}%")
        with col2:
            st.metric("Non-Value-Added Time", f"{stats['nva_time']:.1f}s", f"{stats['nva_percentage']:.1f}%")
        with col3:
            st.metric("Current Activity", stats['current_activity'])
        
        # Activity history
        if analyzer.analysis_data['activity_history']:
            st.subheader("📈 Activity History")
            for i, record in enumerate(analyzer.analysis_data['activity_history'][-5:]):  # Last 5 activities
                st.write(f"{i+1}. **{record['activity']}** - {record['duration']:.1f}s")
        
    else:
        # Full functionality with camera
        st.success("✅ All dependencies available - Full functionality enabled")
        
        if 'analyzer' not in st.session_state:
            st.session_state.analyzer = WorkstationAnalyzer()
        if 'is_running' not in st.session_state:
            st.session_state.is_running = False
        
        analyzer = st.session_state.analyzer
        
        # Camera interface
        st.subheader("📹 Camera Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            camera_source = st.selectbox("Camera Source", [0, 1, 2], index=0)
        with col2:
            confidence = st.slider("Detection Confidence", 0.3, 0.9, 0.5)
        
        # Control buttons
        col1, col2 = st.columns(2)
        with col1:
            start_camera = st.button("▶️ Start Camera Analysis")
        with col2:
            stop_camera = st.button("⏹️ Stop Analysis")
        
        if start_camera:
            st.session_state.is_running = True
        if stop_camera:
            st.session_state.is_running = False
        
        # Camera processing would go here
        # Note: Real-time camera processing in Streamlit Cloud is limited
        if st.session_state.is_running:
            st.info("Camera analysis would run here. Note: Real-time camera processing works best when running locally.")
    
    # Instructions
    with st.expander("📖 Instructions & Troubleshooting"):
        st.markdown("""
        ## Setup Instructions
        
        ### For Local Development:
        ```bash
        # Create virtual environment
        python -m venv workstation_env
        source workstation_env/bin/activate  # Windows: workstation_env\\Scripts\\activate
        
        # Install dependencies
        pip install streamlit opencv-python mediapipe numpy
        
        # Run application
        streamlit run app.py
        ```
        
        ### For Streamlit Cloud Deployment:
        1. Use `opencv-python-headless` instead of `opencv-python`
        2. Pin specific versions in requirements.txt
        3. Camera access is limited on cloud platforms
        
        ### Common Issues:
        - **"installer returned a non-zero exit code"**: Try pinning specific package versions
        - **MediaPipe installation fails**: Ensure Python version is 3.8-3.11
        - **Camera not working**: Check permissions and ensure camera isn't in use by other apps
        
        ### Activity Classifications:
        - **VA (Value-Added)**: Assembly work, tool operations, productive movements
        - **NVA (Non-Value-Added)**: Reaching, waiting, idle time, non-productive movements
        """)

if __name__ == "__main__":
    main()
