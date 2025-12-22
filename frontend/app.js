// API Configuration
const API_URL = window.location.protocol + '//' + window.location.hostname + ':8000';

// State
let refreshInterval;
let currentFilters = {
    hours: 24
};

// Event type colors
const eventTypeColors = {
    'user_login': '#4caf50',
    'user_logout': '#f44336',
    'page_view': '#2196f3',
    'button_click': '#ff9800',
    'form_submit': '#9c27b0',
    'api_call': '#00bcd4',
    'error_occurred': '#e91e63'
};

// Utility functions
function formatNumber(num) {
    return num.toLocaleString();
}

function formatDateTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
}

function showError(message) {
    const errorBanner = document.getElementById('error-banner');
    const errorMessage = document.getElementById('error-message');
    errorMessage.textContent = '⚠️ ' + message;
    errorBanner.classList.remove('hidden');
}

function hideError() {
    const errorBanner = document.getElementById('error-banner');
    errorBanner.classList.add('hidden');
}

// API Calls
async function fetchStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        const data = await response.json();
        updateStatsPanel(data);
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

async function fetchSummary() {
    try {
        const response = await fetch(`${API_URL}/summary`);
        const data = await response.json();
        updateSummaryTable(data);
    } catch (error) {
        console.error('Error fetching summary:', error);
    }
}

async function fetchEvents() {
    try {
        const params = new URLSearchParams({
            limit: 50,
            hours: currentFilters.hours
        });
        
        const response = await fetch(`${API_URL}/events?${params}`);
        const data = await response.json();
        updateEventsList(data);
        hideError();
    } catch (error) {
        console.error('Error fetching events:', error);
        showError('Failed to fetch events. Make sure the API is running.');
    }
}

// Update UI
function updateStatsPanel(stats) {
    document.getElementById('stat-total-events').textContent = formatNumber(stats.total_events);
    document.getElementById('stat-raw-events').textContent = formatNumber(stats.total_raw_events);
    document.getElementById('stat-event-types').textContent = stats.event_types_count;
    document.getElementById('stat-latest-event').textContent = stats.latest_event_time ? formatTime(stats.latest_event_time) : 'N/A';
}

function updateSummaryTable(summary) {
    const tbody = document.getElementById('summary-tbody');
    
    if (!summary || summary.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-message">No events processed yet. Waiting for data...</td></tr>';
        return;
    }
    
    tbody.innerHTML = summary.map(item => `
        <tr>
            <td class="event-type">${item.event_type}</td>
            <td class="count">${formatNumber(item.event_count)}</td>
            <td>${item.avg_value !== null ? item.avg_value.toFixed(2) : 'N/A'}</td>
            <td>${item.first_event ? formatDateTime(item.first_event) : 'N/A'}</td>
            <td>${item.last_event ? formatDateTime(item.last_event) : 'N/A'}</td>
        </tr>
    `).join('');
}

function updateEventsList(events) {
    const container = document.getElementById('events-container');
    const countElement = document.getElementById('events-count');
    
    countElement.textContent = `Showing ${events.length} events`;
    
    if (!events || events.length === 0) {
        container.innerHTML = '<p class="empty-message">No events found matching the filters.</p>';
        return;
    }
    
    container.innerHTML = events.map(event => {
        const color = eventTypeColors[event.event_type] || '#666';
        let metadataHTML = '';
        
        if (event.event_metadata && Object.keys(event.event_metadata).length > 0) {
            metadataHTML = `
                <div class="event-metadata">
                    <strong>Metadata:</strong>
                    <ul>
                        ${Object.entries(event.event_metadata)
                            .filter(([key, value]) => value)
                            .map(([key, value]) => `
                                <li>
                                    <span class="metadata-key">${key}:</span> ${value}
                                </li>
                            `).join('')}
                    </ul>
                </div>
            `;
        }
        
        return `
            <div class="event-card">
                <div class="event-header">
                    <span class="event-type-badge" style="background-color: ${color}">
                        ${event.event_type}
                    </span>
                    <span class="event-source">${event.source}</span>
                    <span class="event-time">${formatDateTime(event.event_time)}</span>
                </div>
                <div class="event-details">
                    ${event.event_value !== null && event.event_value !== undefined ? `
                        <div class="event-value">
                            <strong>Value:</strong> ${event.event_value}
                        </div>
                    ` : ''}
                    ${metadataHTML}
                </div>
            </div>
        `;
    }).join('');
}

// Load all data
async function loadAllData() {
    await Promise.all([
        fetchStats(),
        fetchSummary(),
        fetchEvents()
    ]);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Load initial data
    loadAllData();
    
    // Set up refresh interval (every 10 seconds)
    refreshInterval = setInterval(loadAllData, 10000);
    
    // Set up event listeners
    document.getElementById('hours-filter').addEventListener('change', (e) => {
        currentFilters.hours = parseInt(e.target.value);
        fetchEvents();
    });
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});
