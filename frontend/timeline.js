// API Configuration
const API_URL = window.location.protocol + '//' + window.location.hostname + ':8000';

// Timeline state
let allEvents = [];
let filteredEvents = [];
let selectedEvent = null;

// D3 timeline variables
let svg, xScale, yScale, xAxis, zoom;
const margin = { top: 40, right: 40, bottom: 60, left: 60 };

// Color scale for categories
const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initializeTimeline();
    loadCategories();
    loadEvents();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('search-btn').addEventListener('click', handleSearch);
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
    document.getElementById('category-select').addEventListener('change', handleCategoryFilter);
    document.getElementById('reset-zoom-btn').addEventListener('click', resetZoom);
    document.getElementById('refresh-btn').addEventListener('click', loadEvents);
    document.getElementById('close-details-btn').addEventListener('click', closeEventDetails);
}

// Load categories from API
async function loadCategories() {
    try {
        const response = await fetch(`${API_URL}/categories`);
        const data = await response.json();
        
        const select = document.getElementById('category-select');
        data.categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.category;
            option.textContent = `${cat.category} (${cat.count})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

// Load events from API
async function loadEvents(category = null) {
    try {
        let url = `${API_URL}/events?limit=500`;
        if (category) {
            url += `&category=${encodeURIComponent(category)}`;
        }
        
        const response = await fetch(url);
        allEvents = await response.json();
        filteredEvents = [...allEvents];
        
        updateStats();
        renderTimeline();
    } catch (error) {
        console.error('Error loading events:', error);
        showError('Failed to load events. Please refresh the page.');
    }
}

// Load statistics
async function updateStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        const stats = await response.json();
        
        document.getElementById('total-events').textContent = stats.total_events;
        document.getElementById('loaded-events').textContent = filteredEvents.length;
        
        if (stats.earliest_year && stats.latest_year) {
            const earliest = formatYearDisplay(stats.earliest_year);
            const latest = formatYearDisplay(stats.latest_year);
            document.getElementById('time-range').textContent = `${earliest} to ${latest}`;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Format year for display
function formatYearDisplay(year) {
    if (year < 0) {
        return `${Math.abs(year)} BC`;
    } else {
        return `${year} AD`;
    }
}

// Initialize D3 timeline
function initializeTimeline() {
    const container = document.getElementById('timeline-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    svg = d3.select('#timeline')
        .attr('width', width)
        .attr('height', height);
    
    // Create scales
    xScale = d3.scaleLinear()
        .range([margin.left, width - margin.right]);
    
    yScale = d3.scaleLinear()
        .range([height - margin.bottom, margin.top]);
    
    // Create axes
    xAxis = d3.axisBottom(xScale)
        .tickFormat(d => formatYearDisplay(d));
    
    // Add zoom behavior
    zoom = d3.zoom()
        .scaleExtent([0.5, 10])
        .translateExtent([[0, 0], [width, height]])
        .extent([[0, 0], [width, height]])
        .on('zoom', zoomed);
    
    svg.call(zoom);
    
    // Add axis group
    svg.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(0, ${height - margin.bottom})`);
    
    // Add title
    svg.append('text')
        .attr('class', 'timeline-title')
        .attr('x', width / 2)
        .attr('y', 25)
        .attr('text-anchor', 'middle')
        .style('font-size', '16px')
        .style('font-weight', 'bold')
        .text('Historical Timeline (Zoom and Pan)');
}

// Render timeline with events
function renderTimeline() {
    if (filteredEvents.length === 0) {
        return;
    }
    
    // Extract years and convert BC years to negative
    const years = filteredEvents
        .filter(e => e.start_year !== null)
        .map(e => e.is_bc_start ? -e.start_year : e.start_year);
    
    if (years.length === 0) {
        return;
    }
    
    const minYear = Math.min(...years);
    const maxYear = Math.max(...years);
    const padding = (maxYear - minYear) * 0.1;
    
    xScale.domain([minYear - padding, maxYear + padding]);
    yScale.domain([0, 1]);
    
    // Update axis
    svg.select('.x-axis')
        .call(xAxis);
    
    // Bind data
    const events = svg.selectAll('.timeline-event')
        .data(filteredEvents.filter(e => e.start_year !== null), d => d.id);
    
    // Exit
    events.exit().remove();
    
    // Enter + Update
    const eventsEnter = events.enter()
        .append('circle')
        .attr('class', 'timeline-event')
        .merge(events);
    
    eventsEnter
        .attr('cx', d => xScale(d.is_bc_start ? -d.start_year : d.start_year))
        .attr('cy', (d, i) => yScale(0.5))
        .attr('r', 6)
        .attr('fill', d => colorScale(d.category || 'Unknown'))
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .style('opacity', 0.8)
        .on('click', (event, d) => showEventDetails(d))
        .append('title')
        .text(d => d.title);
}

// Zoom handler
function zoomed(event) {
    const newXScale = event.transform.rescaleX(xScale);
    
    svg.select('.x-axis').call(xAxis.scale(newXScale));
    
    svg.selectAll('.timeline-event')
        .attr('cx', d => newXScale(d.is_bc_start ? -d.start_year : d.start_year));
}

// Reset zoom
function resetZoom() {
    svg.transition()
        .duration(750)
        .call(zoom.transform, d3.zoomIdentity);
}

// Handle search
async function handleSearch() {
    const query = document.getElementById('search-input').value.trim();
    
    if (query.length < 3) {
        alert('Please enter at least 3 characters to search');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}&limit=100`);
        filteredEvents = await response.json();
        
        updateStats();
        renderTimeline();
    } catch (error) {
        console.error('Error searching events:', error);
        showError('Search failed. Please try again.');
    }
}

// Handle category filter
function handleCategoryFilter(event) {
    const category = event.target.value;
    
    if (category) {
        loadEvents(category);
    } else {
        loadEvents();
    }
}

// Show event details
function showEventDetails(event) {
    selectedEvent = event;
    
    document.getElementById('event-title').textContent = event.title;
    document.getElementById('event-period').textContent = event.display_year || 'Unknown';
    document.getElementById('event-category').textContent = event.category || 'Uncategorized';
    document.getElementById('event-description').textContent = event.description || 'No description available.';
    
    const wikipediaLink = document.getElementById('event-wikipedia-link');
    if (event.wikipedia_url) {
        wikipediaLink.href = event.wikipedia_url;
        wikipediaLink.style.display = 'inline-block';
    } else {
        wikipediaLink.style.display = 'none';
    }
    
    document.getElementById('event-details').classList.remove('hidden');
    
    // Highlight selected event
    svg.selectAll('.timeline-event')
        .classed('timeline-event-selected', d => d.id === event.id);
}

// Close event details
function closeEventDetails() {
    document.getElementById('event-details').classList.add('hidden');
    selectedEvent = null;
    
    // Remove highlight
    svg.selectAll('.timeline-event')
        .classed('timeline-event-selected', false);
}

// Show error message
function showError(message) {
    const container = document.getElementById('timeline-container');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    container.insertBefore(errorDiv, container.firstChild);
    
    setTimeout(() => errorDiv.remove(), 5000);
}

// Handle window resize
window.addEventListener('resize', () => {
    initializeTimeline();
    renderTimeline();
});
