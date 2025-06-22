import streamlit as st
import numpy as np
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

class WorkstationAnalyzer:
    """Real workstation analyzer for production use"""
    
    def __init__(self, station_id=None):
        self.station_id = station_id
        self.reset_analysis()
        self.activity_types = {
            'Value-Added': ['Assembly', 'Welding', 'Machining', 'Quality Check', 'Installation', 'Testing', 'Packaging'],
            'Non-Value-Added': ['Setup', 'Cleanup', 'Material Handling', 'Waiting', 'Rework', 'Walking', 'Searching']
        }
        
    def reset_analysis(self):
        """Reset all analysis data"""
        self.analysis_data = {
            'session_start': None,
            'session_end': None,
            'current_task_start': None,
            'activities': [],
            'is_timing': False
        }
        
    def start_timing(self):
        """Start the timing session"""
        current_time = datetime.now()
        self.analysis_data['session_start'] = current_time
        self.analysis_data['is_timing'] = True
        return current_time
    
    def stop_timing(self):
        """Stop the timing session"""
        if self.analysis_data['is_timing']:
            self.analysis_data['session_end'] = datetime.now()
            self.analysis_data['is_timing'] = False
            return True
        return False
    
    def add_task(self, task_name, activity_type, notes=""):
        """Add a task with automatic timing"""
        if not self.analysis_data['is_timing']:
            return False, "Timing session not active"
        
        current_time = datetime.now()
        
        # If there's a previous task running, close it
        if self.analysis_data['current_task_start']:
            duration = (current_time - self.analysis_data['current_task_start']).total_seconds()
            
            # Update the last activity with actual duration
            if self.analysis_data['activities']:
                self.analysis_data['activities'][-1]['end_time'] = current_time
                self.analysis_data['activities'][-1]['duration'] = duration
        
        # Add new task
        task_record = {
            'station_id': self.station_id,
            'task_name': task_name,
            'activity_type': activity_type,
            'start_time': current_time,
            'end_time': None,
            'duration': 0,
            'notes': notes,
            'operator': st.session_state.get('operator_name', 'Unknown')
        }
        
        self.analysis_data['activities'].append(task_record)
        self.analysis_data['current_task_start'] = current_time
        
        return True, f"Task '{task_name}' started"
    
    def finish_current_task(self):
        """Finish the currently running task"""
        if not self.analysis_data['current_task_start'] or not self.analysis_data['activities']:
            return False, "No active task to finish"
        
        current_time = datetime.now()
        duration = (current_time - self.analysis_data['current_task_start']).total_seconds()
        
        # Update the last activity
        self.analysis_data['activities'][-1]['end_time'] = current_time
        self.analysis_data['activities'][-1]['duration'] = duration
        
        self.analysis_data['current_task_start'] = None
        
        return True, f"Task completed - Duration: {duration:.1f} seconds"
    
    def get_current_stats(self):
        """Get current analysis statistics"""
        if not self.analysis_data['activities']:
            return {
                'total_time': 0,
                'va_time': 0,
                'nva_time': 0,
                'va_percentage': 0,
                'nva_percentage': 0,
                'current_task': 'No active task',
                'session_duration': 0,
                'task_count': 0,
                'avg_task_duration': 0
            }
        
        completed_activities = [a for a in self.analysis_data['activities'] if a['end_time'] is not None]
        
        if not completed_activities:
            return {
                'total_time': 0,
                'va_time': 0,
                'nva_time': 0,
                'va_percentage': 0,
                'nva_percentage': 0,
                'current_task': self.analysis_data['activities'][-1]['task_name'] if self.analysis_data['activities'] else 'No active task',
                'session_duration': (datetime.now() - self.analysis_data['session_start']).total_seconds() if self.analysis_data['session_start'] else 0,
                'task_count': len(self.analysis_data['activities']),
                'avg_task_duration': 0
            }
        
        va_time = sum(a['duration'] for a in completed_activities if a['activity_type'] == 'Value-Added')
        nva_time = sum(a['duration'] for a in completed_activities if a['activity_type'] == 'Non-Value-Added')
        total_time = va_time + nva_time
        
        va_percentage = (va_time / total_time * 100) if total_time > 0 else 0
        nva_percentage = (nva_time / total_time * 100) if total_time > 0 else 0
        
        avg_duration = total_time / len(completed_activities) if completed_activities else 0
        
        current_task = 'No active task'
        if self.analysis_data['current_task_start'] and self.analysis_data['activities']:
            current_task = self.analysis_data['activities'][-1]['task_name']
        
        session_duration = 0
        if self.analysis_data['session_start']:
            end_time = self.analysis_data['session_end'] or datetime.now()
            session_duration = (end_time - self.analysis_data['session_start']).total_seconds()
        
        return {
            'total_time': total_time,
            'va_time': va_time,
            'nva_time': nva_time,
            'va_percentage': va_percentage,
            'nva_percentage': nva_percentage,
            'current_task': current_task,
            'session_duration': session_duration,
            'task_count': len(completed_activities),
            'avg_task_duration': avg_duration
        }
    
    def get_activities_dataframe(self):
        """Get activities as a pandas DataFrame for export"""
        if not self.analysis_data['activities']:
            return pd.DataFrame()
        
        df_data = []
        for activity in self.analysis_data['activities']:
            df_data.append({
                'Station ID': activity['station_id'],
                'Task Name': activity['task_name'],
                'Activity Type': activity['activity_type'],
                'Start Time': activity['start_time'].strftime('%Y-%m-%d %H:%M:%S') if activity['start_time'] else '',
                'End Time': activity['end_time'].strftime('%Y-%m-%d %H:%M:%S') if activity['end_time'] else 'In Progress',
                'Duration (seconds)': round(activity['duration'], 2),
                'Duration (minutes)': round(activity['duration'] / 60, 2),
                'Operator': activity['operator'],
                'Notes': activity['notes']
            })
        
        return pd.DataFrame(df_data)

def create_pie_chart(va_time, nva_time):
    """Create time distribution pie chart"""
    if va_time == 0 and nva_time == 0:
        return None
    
    fig = go.Figure(data=[go.Pie(
        labels=['Value-Added', 'Non-Value-Added'],
        values=[va_time, nva_time],
        marker=dict(colors=['#2E8B57', '#CD5C5C']),
        hole=0.4,
        textinfo='label+percent+value',
        texttemplate='%{label}<br>%{percent}<br>%{value:.1f}s'
    )])
    
    fig.update_layout(
        title="Time Distribution",
        height=350
    )
    
    return fig

def create_timeline_chart(activities):
    """Create activity timeline chart"""
    if not activities:
        return None
    
    completed_activities = [a for a in activities if a['end_time'] is not None]
    if not completed_activities:
        return None
    
    # Create timeline data
    timeline_data = []
    start_base = completed_activities[0]['start_time']
    
    for activity in completed_activities:
        start_offset = (activity['start_time'] - start_base).total_seconds()
        end_offset = start_offset + activity['duration']
        
        timeline_data.append({
            'Task': activity['task_name'],
            'Start': start_offset,
            'End': end_offset,
            'Type': activity['activity_type'],
            'Duration': activity['duration']
        })
    
    df = pd.DataFrame(timeline_data)
    
    fig = px.timeline(
        df,
        x_start="Start",
        x_end="End", 
        y="Task",
        color="Type",
        color_discrete_map={'Value-Added': '#2E8B57', 'Non-Value-Added': '#CD5C5C'},
        title="Task Timeline"
    )
    
    fig.update_layout(
        height=max(300, len(completed_activities) * 30),
        xaxis_title="Time (seconds from start)"
    )
    
    return fig

def main():
    st.set_page_config(
        page_title="Workstation Analysis - MVP",
        page_icon="🏭",
        layout="wide"
    )
    
    st.title("🏭 Workstation Time Analysis - MVP")
    st.markdown("*Track and analyze workstation productivity in real-time*")
    
    # Sidebar for session setup
    with st.sidebar:
        st.header("📋 Session Setup")
        
        # Station ID input
        station_id = st.text_input("Station ID/Number", value="WS-001", help="Enter the workstation identifier")
        
        # Operator name
        operator_name = st.text_input("Operator Name", value="", help="Enter operator name (optional)")
        st.session_state['operator_name'] = operator_name
        
        # Initialize or update analyzer
        if 'analyzer' not in st.session_state or st.session_state.get('current_station') != station_id:
            st.session_state.analyzer = WorkstationAnalyzer(station_id)
            st.session_state.current_station = station_id
        
        analyzer = st.session_state.analyzer
        analyzer.station_id = station_id  # Update station ID if changed
        
        st.divider()
        
        # Session controls
        st.header("⏱️ Session Controls")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if not analyzer.analysis_data['is_timing']:
                if st.button("▶️ Start Timing", type="primary", use_container_width=True):
                    start_time = analyzer.start_timing()
                    st.success(f"Session started at {start_time.strftime('%H:%M:%S')}")
                    st.rerun()
            else:
                if st.button("⏹️ Stop Session", type="secondary", use_container_width=True):
                    if analyzer.stop_timing():
                        st.success("Session stopped")
                        st.rerun()
        
        with col2:
            if st.button("🔄 Reset All", use_container_width=True):
                st.session_state.analyzer = WorkstationAnalyzer(station_id)
                st.success("Session reset")
                st.rerun()
        
        # Current session status
        if analyzer.analysis_data['is_timing']:
            st.success("🔴 **Session Active**")
            if analyzer.analysis_data['session_start']:
                elapsed = (datetime.now() - analyzer.analysis_data['session_start']).total_seconds()
                st.metric("Elapsed Time", f"{elapsed/60:.1f} min")
        else:
            st.info("⚪ Session Inactive")
    
    # Main content area
    if not analyzer.analysis_data['is_timing']:
        st.info("👈 Start a timing session from the sidebar to begin tracking tasks")
        return
    
    # Task input section
    st.subheader("➕ Add Task")
    
    col1, col2, col3 = st.columns([3, 2, 1])
    
    with col1:
        task_name = st.text_input("Task Name", placeholder="e.g., Assemble motor housing")
    
    with col2:
        activity_type = st.selectbox("Activity Type", ['Value-Added', 'Non-Value-Added'])
    
    with col3:
        st.write("") # Spacing
        if st.button("➕ Add Task", type="primary"):
            if task_name.strip():
                success, message = analyzer.add_task(task_name.strip(), activity_type)
                if success:
                    st.success(message)
                else:
                    st.error(message)
                st.rerun()
            else:
                st.warning("Please enter a task name")
    
    # Finish current task button
    if analyzer.analysis_data['current_task_start']:
        col1, col2, col3 = st.columns([1, 1, 2])
        with col2:
            if st.button("✅ Finish Current Task", type="secondary"):
                success, message = analyzer.finish_current_task()
                if success:
                    st.success(message)
                else:
                    st.error(message)
                st.rerun()
    
    # Current Statistics
    stats = analyzer.get_current_stats()
    
    st.subheader("📊 Current Session Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        efficiency = stats['va_percentage'] if stats['total_time'] > 0 else 0
        st.metric("Efficiency", f"{efficiency:.1f}%", help="Percentage of time spent on value-added activities")
    
    with col2:
        st.metric("Total Tasks", stats['task_count'], help="Number of completed tasks")
    
    with col3:
        st.metric("Total Time", f"{stats['total_time']/60:.1f} min", help="Total time for completed tasks")
    
    with col4:
        st.metric("Avg Task Time", f"{stats['avg_task_duration']/60:.1f} min", help="Average duration per task")
    
    # Current task indicator
    if stats['current_task'] != 'No active task':
        st.info(f"🔵 **Current Task:** {stats['current_task']}")
    
    # Charts
    if stats['total_time'] > 0:
        st.subheader("📈 Analysis Charts")
        
        col1, col2 = st.columns(2)
        
        with col1:
            pie_chart = create_pie_chart(stats['va_time'], stats['nva_time'])
            if pie_chart:
                st.plotly_chart(pie_chart, use_container_width=True)
        
        with col2:
            timeline_chart = create_timeline_chart(analyzer.analysis_data['activities'])
            if timeline_chart:
                st.plotly_chart(timeline_chart, use_container_width=True)
    
    # Data table and export
    st.subheader("📋 Task Data")
    
    df = analyzer.get_activities_dataframe()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # Export options
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            # CSV download
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"workstation_{station_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Excel download
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Task Data', index=False)
                
                # Add summary sheet
                summary_df = pd.DataFrame([
                    ['Station ID', station_id],
                    ['Operator', operator_name or 'Not specified'],
                    ['Session Start', analyzer.analysis_data['session_start'].strftime('%Y-%m-%d %H:%M:%S') if analyzer.analysis_data['session_start'] else ''],
                    ['Total Tasks', stats['task_count']],
                    ['Total Time (min)', f"{stats['total_time']/60:.2f}"],
                    ['Value-Added Time (min)', f"{stats['va_time']/60:.2f}"],
                    ['Non-Value-Added Time (min)', f"{stats['nva_time']/60:.2f}"],
                    ['Efficiency %', f"{stats['va_percentage']:.1f}%"],
                ], columns=['Metric', 'Value'])
                
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            st.download_button(
                label="📊 Download Excel",
                data=buffer.getvalue(),
                file_name=f"workstation_{station_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No task data available yet. Add some tasks to see the data table.")
    
    # Quick tips
    with st.expander("💡 Quick Tips"):
        st.markdown("""
        **How to use this app:**
        1. Enter your station ID and operator name in the sidebar
        2. Click "Start Timing" to begin your session
        3. Add tasks as you work - each new task automatically stops the previous one
        4. Use "Finish Current Task" when you're done with the last task
        5. Download your data as CSV or Excel for further analysis
        
        **Activity Types:**
        - **Value-Added**: Activities that directly contribute to the product (assembly, machining, quality checks)
        - **Non-Value-Added**: Necessary but non-productive activities (setup, cleanup, waiting, walking)
        
        **Tips for best results:**
        - Be consistent with task naming
        - Add tasks in real-time for accurate timing
        - Use descriptive but concise task names
        - Remember to finish your last task before ending the session
        """)

if __name__ == "__main__":
    main()
