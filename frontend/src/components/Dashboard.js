import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './Dashboard.css';

function Dashboard({ summary }) {
  if (!summary || summary.length === 0) {
    return (
      <div className="card">
        <h2>📊 Event Summary</h2>
        <p className="empty-message">No events processed yet. Waiting for data...</p>
      </div>
    );
  }

  return (
    <div className="card dashboard">
      <h2>📊 Event Summary by Type</h2>
      
      <div className="chart-container">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={summary}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="event_type" angle={-45} textAnchor="end" height={80} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="event_count" fill="#667eea" name="Event Count" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="summary-table">
        <table>
          <thead>
            <tr>
              <th>Event Type</th>
              <th>Count</th>
              <th>Avg Value</th>
              <th>First Event</th>
              <th>Last Event</th>
            </tr>
          </thead>
          <tbody>
            {summary.map((item, index) => (
              <tr key={index}>
                <td className="event-type">{item.event_type}</td>
                <td className="count">{item.event_count}</td>
                <td>{item.avg_value ? item.avg_value.toFixed(2) : 'N/A'}</td>
                <td>{item.first_event ? new Date(item.first_event).toLocaleString() : 'N/A'}</td>
                <td>{item.last_event ? new Date(item.last_event).toLocaleString() : 'N/A'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Dashboard;
