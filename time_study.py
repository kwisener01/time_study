import streamlit as st
import numpy as np
import time
import random
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

class WorkstationAnalyzer:
    """Demo workstation analyzer without computer vision dependencies"""
    
    def __init__(self):
        self.reset_analysis()
        self.activity_types = {
            'VA': ['Assembly Work', 'Welding', 'Tool Operation', 'Quality Check', 'Installation'],
            'NVA': ['Reaching', 'Waiting', 'Walking', 'Searching', 'Setup', 'Idle']
        }
        
    def reset_analysis(self):
        """Reset all analysis data"""
        self.analysis_data = {
            'session_start': time.time(),
            'value_added_time': 0,
            'non_value_added_time': 0,
            'current_activity': None,
            'activity_history': [],
            'productivity_score': 0,
            'cycle_count': 0
        }
        
    def simulate_activity_cycle(self):
        """Simulate a realistic work cycle"""
        # Generate a sequence of activities
        cycle_activities = []
        
        # Start with setup (NVA)
        setup_time = random.uniform(2, 8)
        cycle_activities.append({
            'type': 'NVA',
            'activity': 'Setup',
            'duration': setup_time,
            'efficiency': random.uniform(0.3, 0.6)
        })
        
        # Add 2-4 value-added activities
        va_count = random.randint(2, 4)
        for _ in range(va_count):
            activity = random.choice(self.activity_types['VA'])
            duration = random.uniform(15, 45)
            efficiency = random.uniform(0.7, 0.95)
            cycle_activities.append({
                'type': 'VA',
                'activity': activity,
                'duration': duration,
                'efficiency': efficiency
            })
            
            # Sometimes add NVA between VA activities
            if random.random() < 0.4:
                nva_activity = random.choice(self.activity_types['NVA'])
                nva_duration = random.uniform(3, 12)
                cycle_activities.append({
                    'type': 'NVA',
                    'activity': nva_activity,
                    'duration': nva_duration,
                    'efficiency': random.uniform(0.2, 0.5)
                })
        
        # Process the cycle
        for activity_data in cycle_activities:
            self.add_activity(
                f"{activity_data['type']}: {activity_data['activity']}",
                activity_data['duration'],
                activity_data['efficiency']
            )
        
        self.analysis_data['cycle_count'] += 1
        
    def add_activity(self, activity, duration, efficiency=None):
        """Add an activity to the analysis"""
        now = time.time()
        
        # Update timing
        if 'VA' in activity:
            self.analysis_data['value_added_time'] += duration
        else:
            self.analysis_data['non_value_added_time'] += duration
        
        # Record in history
        self.analysis_data['activity_history'].append({
            'activity': activity,
            'duration': duration,
            'timestamp': now,
            'efficiency': efficiency or random.uniform(0.5, 0.9)
        })
        
        self.analysis_data['current_activity'] = activity
        self.update_productivity_score()
        
    def update_productivity_score(self):
        """Calculate overall productivity score"""
        total_time = self.analysis_data['value_added_time'] + self.analysis_data['non_value_added_time']
        if total_time > 0:
            va_ratio = self.analysis_data['value_added_time'] / total_time
            
            # Factor in efficiency scores
            if self.analysis_data['activity_history']:
                avg_efficiency = np.mean([a['efficiency'] for a in self.analysis_data['activity_history']])
                self.analysis_data['productivity_score'] = (va_ratio * 0.7 + avg_efficiency * 0.3) * 100
            else:
                self.analysis_data['productivity_score'] = va_ratio * 100
    
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
            'current_activity': self.analysis_data['current_activity'] or 'No Activity',
            'session_duration': time.time() - self.analysis_data['session_start'],
            'productivity_score': self.analysis_data['productivity_score'],
            'cycle_count': self.analysis_data['cycle_count'],
            'activities_count': len(self.analysis_data['activity_history'])
        }
    
    def get_activity_breakdown(self):
        """Get detailed activity breakdown"""
        breakdown = {}
        for record in self.analysis_data['activity_history']:
            activity = record['activity']
            if activity not in breakdown:
                breakdown[activity] = {'total_time': 0, 'count': 0, 'avg_efficiency': 0}
            
            breakdown[activity]['total_time'] += record['duration']
            breakdown[activity]['count'] += 1
            breakdown[activity]['avg_efficiency'] = (
                breakdown[activity]['avg_efficiency'] + record['efficiency']
            ) / 2 if breakdown[activity]['avg_efficiency'] > 0 else record['efficiency']
        
        return breakdown

def main():
    st.set_page_config(
        page_title="Workstation Analysis Demo",
        page_icon="🏭",
        layout="wide"
    )
    
    st.title("🏭 Workstation Analysis System - Demo")
    st.markdown("*Interactive demonstration of workstation productivity analysis*")
    
    # Initialize analyzer
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = WorkstationAnalyzer()
    
    analyzer = st.session_state.analyzer
    
    # Control Panel
    st.subheader("🎛️ Control Panel")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🚀 Simulate Work Cycle", type="primary"):
            analyzer.simulate_activity_cycle()
            st.success(f"Work cycle #{analyzer.analysis_data['cycle_count']} completed!")
    
    with col2:
        if st.button("➕ Add Single Activity"):
            activities = ['VA: Assembly', 'VA: Quality Check', 'NVA: Waiting', 'NVA: Reaching']
            activity = random.choice(activities)
            duration = random.uniform(10, 30)
            analyzer.add_activity(activity, duration)
            st.success(f"Added: {activity}")
    
    with col3:
        if st.button("🔄 Reset Analysis"):
            st.session_state.analyzer = WorkstationAnalyzer()
            st.success("Analysis reset!")
    
    with col4:
        auto_simulate = st.checkbox("🔁 Auto-simulate")
    
    # Auto-simulation
    if auto_simulate:
        if 'last_auto_sim' not in st.session_state:
            st.session_state.last_auto_sim = time.time()
        
        if time.time() - st.session_state.last_auto_sim > 3:  # Every 3 seconds
            analyzer.add_activity(
                random.choice(['VA: Assembly', 'VA: Tool Operation', 'NVA: Waiting', 'NVA: Reaching']),
                random.uniform(2, 8)
            )
            st.session_state.last_auto_sim = time.time()
            st.rerun()
    
    # Current Statistics
    stats = analyzer.get_current_stats()
    
    st.subheader("📊 Real-time Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Productivity Score", 
            f"{stats['productivity_score']:.1f}%",
            delta=f"Cycle {stats['cycle_count']}" if stats['cycle_count'] > 0 else None
        )
    
    with col2:
        st.metric(
            "Value-Added Time", 
            f"{stats['va_time']:.1f}s",
            delta=f"{stats['va_percentage']:.1f}%"
        )
    
    with col3:
        st.metric(
            "Non-Value-Added Time", 
            f"{stats['nva_time']:.1f}s",
            delta=f"{stats['nva_percentage']:.1f}%"
        )
    
    with col4:
        st.metric(
            "Total Activities", 
            stats['activities_count'],
            delta=f"Current: {stats['current_activity'][:20]}..." if len(stats['current_activity']) > 20 else stats['current_activity']
        )
    
    # Visualizations
    if stats['total_time'] > 0:
        st.subheader("📈 Analysis Visualizations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Time breakdown pie chart
            fig_pie = go.Figure(data=[go.Pie(
                labels=['Value-Added', 'Non-Value-Added'],
                values=[stats['va_time'], stats['nva_time']],
                colors=['#2E8B57', '#CD5C5C'],
                hole=0.4
            )])
            fig_pie.update_layout(
                title="Time Distribution",
                height=300,
                showlegend=True
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Activity breakdown
            breakdown = analyzer.get_activity_breakdown()
            if breakdown:
                activities = list(breakdown.keys())
                times = [breakdown[act]['total_time'] for act in activities]
                colors = ['#2E8B57' if 'VA' in act else '#CD5C5C' for act in activities]
                
                fig_bar = go.Figure(data=[go.Bar(
                    x=activities,
                    y=times,
                    marker_color=colors
                )])
                fig_bar.update_layout(
                    title="Activity Time Breakdown",
                    xaxis_title="Activity",
                    yaxis_title="Time (seconds)",
                    height=300
                )
                fig_bar.update_xaxis(tickangle=45)
                st.plotly_chart(fig_bar, use_container_width=True)
        
        # Timeline
        if len(analyzer.analysis_data['activity_history']) > 1:
            st.subheader("⏱️ Activity Timeline")
            
            # Create timeline data
            timeline_data = []
            cumulative_time = 0
            
            for i, record in enumerate(analyzer.analysis_data['activity_history'][-20:]):  # Last 20 activities
                timeline_data.append({
                    'Activity': record['activity'],
                    'Start': cumulative_time,
                    'Duration': record['duration'],
                    'End': cumulative_time + record['duration'],
                    'Efficiency': record['efficiency'],
                    'Type': 'VA' if 'VA' in record['activity'] else 'NVA'
                })
                cumulative_time += record['duration']
            
            df = pd.DataFrame(timeline_data)
            
            fig_timeline = px.timeline(
                df, 
                x_start="Start", 
                x_end="End", 
                y="Activity",
                color="Type",
                color_discrete_map={'VA': '#2E8B57', 'NVA': '#CD5C5C'},
                title="Recent Activity Timeline"
            )
            fig_timeline.update_layout(height=400)
            st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Detailed Analysis
    with st.expander("📋 Detailed Analysis Report"):
        if stats['total_time'] > 0:
            st.markdown(f"""
            ## Session Summary
            - **Session Duration**: {stats['session_duration']:.1f} seconds
            - **Analysis Period**: {stats['total_time']:.1f} seconds
            - **Productivity Score**: {stats['productivity_score']:.1f}%
            - **Work Cycles Completed**: {stats['cycle_count']}
            
            ## Time Analysis
            - **Value-Added Activities**: {stats['va_time']:.1f}s ({stats['va_percentage']:.1f}%)
            - **Non-Value-Added Activities**: {stats['nva_time']:.1f}s ({stats['nva_percentage']:.1f}%)
            
            ## Recommendations
            """)
            
            if stats['va_percentage'] < 60:
                st.warning("⚠️ **Low Value-Added Ratio**: Consider reducing setup time and eliminating unnecessary movements.")
            elif stats['va_percentage'] < 75:
                st.info("ℹ️ **Moderate Efficiency**: Look for opportunities to streamline non-value-added activities.")
            else:
                st.success("✅ **High Efficiency**: Excellent value-added ratio! Maintain current practices.")
            
            # Activity breakdown table
            breakdown = analyzer.get_activity_breakdown()
            if breakdown:
                st.markdown("### Activity Breakdown")
                breakdown_df = pd.DataFrame([
                    {
                        'Activity': activity,
                        'Total Time (s)': data['total_time'],
                        'Count': data['count'],
                        'Avg Duration (s)': data['total_time'] / data['count'],
                        'Avg Efficiency': f"{data['avg_efficiency']:.1%}"
                    }
                    for activity, data in breakdown.items()
                ])
                st.dataframe(breakdown_df, use_container_width=True)
        else:
            st.info("Start simulating activities to see detailed analysis!")
    
    # Instructions
    with st.expander("📖 How to Use This Demo"):
        st.markdown("""
        ## Getting Started
        1. **Simulate Work Cycle**: Click to generate a realistic sequence of work activities
        2. **Add Single Activity**: Add individual activities to see immediate impact
        3. **Auto-simulate**: Enable continuous activity generation for live demonstration
        4. **Reset Analysis**: Clear all data and start fresh
        
        ## Understanding the Metrics
        - **Productivity Score**: Overall efficiency combining time utilization and activity efficiency
        - **Value-Added (VA)**: Activities that directly contribute to the final product
        - **Non-Value-Added (NVA)**: Necessary but non-productive activities (setup, waiting, etc.)
        
        ## Activity Types
        **Value-Added Activities:**
        - Assembly Work, Welding, Tool Operation, Quality Check, Installation
        
        **Non-Value-Added Activities:**
        - Reaching, Waiting, Walking, Searching, Setup, Idle
        
        ## Real Implementation
        This demo simulates what a real computer vision system would detect:
        - Hand and body position tracking
        - Movement pattern analysis  
        - Automatic activity classification
        - Real-time productivity metrics
        """)

if __name__ == "__main__":
    main()
