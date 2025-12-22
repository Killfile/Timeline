import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import Dashboard from './components/Dashboard';
import EventsList from './components/EventsList';
import StatsPanel from './components/StatsPanel';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [stats, setStats] = useState(null);
  const [summary, setSummary] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    eventType: '',
    source: '',
    hours: 24
  });

  // Fetch stats
  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/stats`);
      setStats(response.data);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  // Fetch summary
  const fetchSummary = async () => {
    try {
      const response = await axios.get(`${API_URL}/summary`);
      setSummary(response.data);
    } catch (err) {
      console.error('Error fetching summary:', err);
    }
  };

  // Fetch events
  const fetchEvents = async () => {
    try {
      setLoading(true);
      const params = {
        limit: 50,
        hours: filters.hours
      };
      
      if (filters.eventType) {
        params.event_type = filters.eventType;
      }
      
      if (filters.source) {
        params.source = filters.source;
      }

      const response = await axios.get(`${API_URL}/events`, { params });
      setEvents(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching events:', err);
      setError('Failed to fetch events. Make sure the API is running.');
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      await Promise.all([fetchStats(), fetchSummary(), fetchEvents()]);
    };
    loadData();

    // Refresh data every 10 seconds
    const interval = setInterval(() => {
      loadData();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  // Reload events when filters change
  useEffect(() => {
    fetchEvents();
  }, [filters]);

  const handleFilterChange = (filterName, value) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: value
    }));
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>📊 Timeline Dashboard</h1>
        <p className="subtitle">Real-time Event Tracking and Analytics</p>
      </header>

      <main className="App-main">
        {error && (
          <div className="error-banner">
            <span>⚠️ {error}</span>
          </div>
        )}

        <StatsPanel stats={stats} />
        
        <Dashboard summary={summary} />
        
        <EventsList 
          events={events} 
          loading={loading}
          filters={filters}
          onFilterChange={handleFilterChange}
        />
      </main>

      <footer className="App-footer">
        <p>Timeline Application - Powered by Docker Compose</p>
      </footer>
    </div>
  );
}

export default App;
