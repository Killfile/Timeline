import React from 'react';
import './EventsList.css';

function EventsList({ events, loading, filters, onFilterChange }) {
  if (loading) {
    return (
      <div className="card">
        <h2>📋 Recent Events</h2>
        <div className="loading">Loading events...</div>
      </div>
    );
  }

  const formatEventTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getEventTypeColor = (eventType) => {
    const colors = {
      'user_login': '#4caf50',
      'user_logout': '#f44336',
      'page_view': '#2196f3',
      'button_click': '#ff9800',
      'form_submit': '#9c27b0',
      'api_call': '#00bcd4',
      'error_occurred': '#e91e63'
    };
    return colors[eventType] || '#666';
  };

  return (
    <div className="card events-list">
      <h2>📋 Recent Events</h2>
      
      <div className="filters">
        <div className="filter-group">
          <label htmlFor="hours-filter">Time Range:</label>
          <select
            id="hours-filter"
            value={filters.hours}
            onChange={(e) => onFilterChange('hours', parseInt(e.target.value))}
          >
            <option value={1}>Last Hour</option>
            <option value={6}>Last 6 Hours</option>
            <option value={24}>Last 24 Hours</option>
            <option value={168}>Last Week</option>
          </select>
        </div>
      </div>

      {events.length === 0 ? (
        <p className="empty-message">No events found matching the filters.</p>
      ) : (
        <>
          <div className="events-count">
            Showing {events.length} events
          </div>
          
          <div className="events-container">
            {events.map((event) => (
              <div key={event.id} className="event-card">
                <div className="event-header">
                  <span 
                    className="event-type-badge" 
                    style={{ backgroundColor: getEventTypeColor(event.event_type) }}
                  >
                    {event.event_type}
                  </span>
                  <span className="event-source">{event.source}</span>
                  <span className="event-time">{formatEventTime(event.event_time)}</span>
                </div>
                
                <div className="event-details">
                  {event.event_value !== null && event.event_value !== undefined && (
                    <div className="event-value">
                      <strong>Value:</strong> {event.event_value}
                    </div>
                  )}
                  
                  {event.event_metadata && Object.keys(event.event_metadata).length > 0 && (
                    <div className="event-metadata">
                      <strong>Metadata:</strong>
                      <ul>
                        {Object.entries(event.event_metadata).map(([key, value]) => (
                          value && (
                            <li key={key}>
                              <span className="metadata-key">{key}:</span> {String(value)}
                            </li>
                          )
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default EventsList;
