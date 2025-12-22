import React from 'react';
import './StatsPanel.css';

function StatsPanel({ stats }) {
  if (!stats) {
    return <div className="loading">Loading statistics...</div>;
  }

  return (
    <div className="stats-panel">
      <div className="stat-card">
        <div className="stat-icon">📝</div>
        <div className="stat-content">
          <div className="stat-value">{stats.total_events.toLocaleString()}</div>
          <div className="stat-label">Processed Events</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon">📥</div>
        <div className="stat-content">
          <div className="stat-value">{stats.total_raw_events.toLocaleString()}</div>
          <div className="stat-label">Raw Events</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon">🏷️</div>
        <div className="stat-content">
          <div className="stat-value">{stats.event_types_count}</div>
          <div className="stat-label">Event Types</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon">⏰</div>
        <div className="stat-content">
          <div className="stat-value">
            {stats.latest_event_time ? new Date(stats.latest_event_time).toLocaleTimeString() : 'N/A'}
          </div>
          <div className="stat-label">Latest Event</div>
        </div>
      </div>
    </div>
  );
}

export default StatsPanel;
