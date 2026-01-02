/**
 * LLM Categorization Experiment Script
 * 
 * Handles the experiment workflow:
 * 1. Fetch uncategorized events from API
 * 2. Submit to LLM for categorization
 * 3. Display results with categories, confidence, and reasoning
 */

const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`;

// Category colors (matching timeline)
const CATEGORY_COLORS = {
    'Politics': '#4285F4',
    'War & Conflict': '#EA4335',
    'Science & Technology': '#34A853',
    'Arts & Culture': '#FBBC04',
    'Religion': '#9C27B0',
    'Economics & Trade': '#FF9800',
    'Natural Disasters': '#795548',
    'Exploration & Discovery': '#00BCD4',
    'Social Movements': '#E91E63',
    'Other': '#9E9E9E'
};

// State
let currentEvents = [];
let currentResults = [];

// DOM elements
const modelSelect = document.getElementById('model-select');
const eventCountInput = document.getElementById('event-count');
const runBtn = document.getElementById('run-experiment-btn');
const clearBtn = document.getElementById('clear-results-btn');
const loadingSpinner = document.getElementById('loading-spinner');
const errorContainer = document.getElementById('error-container');
const resultsSection = document.getElementById('results-section');
const eventResultsContainer = document.getElementById('event-results');

// Event listeners
runBtn.addEventListener('click', runExperiment);
clearBtn.addEventListener('click', clearResults);

/**
 * Main experiment workflow
 */
async function runExperiment() {
    // Clear previous errors
    clearError();
    
    // Get form values
    const model = modelSelect.value;
    const count = parseInt(eventCountInput.value, 10);
    
    // Validate
    if (count < 1 || count > 100) {
        showError('Please enter a number between 1 and 100');
        return;
    }
    
    // Disable form and show loading
    setLoading(true);
    
    try {
        // Step 1: Fetch uncategorized events
        console.log(`Fetching ${count} uncategorized events...`);
        const events = await fetchUncategorizedEvents(count);
        
        if (!events || events.length === 0) {
            showError('No uncategorized events found in the database.');
            setLoading(false);
            return;
        }
        
        console.log(`Fetched ${events.length} events`);
        currentEvents = events;
        
        // Step 2: Submit to LLM for categorization
        console.log(`Categorizing events using ${model}...`);
        const results = await categorizeEvents(events, model);
        
        console.log(`Received ${results.length} categorization results`);
        currentResults = results;
        
        // Step 3: Display results
        displayResults(events, results, model);
        
    } catch (error) {
        console.error('Experiment failed:', error);
        showError(`Experiment failed: ${error.message}`);
    } finally {
        setLoading(false);
    }
}

/**
 * Fetch uncategorized events from the API
 */
async function fetchUncategorizedEvents(count) {
    const response = await fetch(`${API_BASE_URL}/uncategorized-events?limit=${count}`);
    
    if (!response.ok) {
        throw new Error(`Failed to fetch events: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.events || [];
}

/**
 * Submit events to LLM for categorization
 */
async function categorizeEvents(events, model) {
    const response = await fetch(`${API_BASE_URL}/categorize-events`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            events: events,
            model: model
        })
    });
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to categorize events: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.results || [];
}

/**
 * Display categorization results
 */
function displayResults(events, results, model) {
    // Create map of event_id -> result for easy lookup
    const resultMap = new Map();
    results.forEach(result => {
        resultMap.set(result.event_id, result);
    });
    
    // Calculate statistics
    const avgConfidence = results.reduce((sum, r) => sum + r.confidence, 0) / results.length;
    
    // Update results header
    document.getElementById('result-model').textContent = model;
    document.getElementById('result-count').textContent = results.length;
    document.getElementById('result-avg-confidence').textContent = (avgConfidence * 100).toFixed(1) + '%';
    
    // Clear and populate event cards
    eventResultsContainer.innerHTML = '';
    
    events.forEach(event => {
        const result = resultMap.get(event.id);
        if (!result) {
            console.warn(`No result found for event ${event.id}`);
            return;
        }
        
        const card = createEventCard(event, result);
        eventResultsContainer.appendChild(card);
    });
    
    // Show results section and clear button
    resultsSection.classList.add('visible');
    clearBtn.style.display = 'inline-block';
}

/**
 * Create an event card with categorization result
 */
function createEventCard(event, result) {
    const card = document.createElement('div');
    card.className = 'event-card';
    
    // Format date display
    const dateStr = formatEventDate(event);
    
    // Get category color
    const categoryColor = CATEGORY_COLORS[result.category] || CATEGORY_COLORS['Other'];
    
    // Confidence level
    const confidenceLevel = result.confidence >= 0.8 ? 'high' : 
                           result.confidence >= 0.5 ? 'medium' : 'low';
    
    card.innerHTML = `
        <div class="event-card-header">
            <h3 class="event-title">${escapeHtml(event.title)}</h3>
            <div class="event-category-badge" style="background: ${categoryColor}; color: white;">
                ${escapeHtml(result.category)}
            </div>
        </div>
        
        <div class="event-meta">
            <div><strong>Event ID:</strong> ${event.id}</div>
            <div><strong>Date:</strong> ${dateStr}</div>
            <div class="confidence-indicator">
                <strong>Confidence:</strong>
                <div class="confidence-bar">
                    <div class="confidence-fill ${confidenceLevel}" 
                         style="width: ${result.confidence * 100}%"></div>
                </div>
                <span>${(result.confidence * 100).toFixed(0)}%</span>
            </div>
        </div>
        
        ${event.description ? `
            <div class="event-description">
                ${escapeHtml(truncateText(event.description, 300))}
            </div>
        ` : ''}
        
        ${result.reasoning ? `
            <div class="event-reasoning">
                <div class="event-reasoning-label">LLM Reasoning:</div>
                <div class="event-reasoning-text">${escapeHtml(result.reasoning)}</div>
            </div>
        ` : ''}
    `;
    
    return card;
}

/**
 * Format event date for display
 */
function formatEventDate(event) {
    if (!event.start_year) {
        return 'Date unknown';
    }
    
    const startEra = event.is_bc_start ? 'BC' : 'AD';
    const endEra = event.is_bc_end ? 'BC' : 'AD';
    
    let startStr = `${event.start_year}`;
    if (event.start_month) {
        startStr += `-${String(event.start_month).padStart(2, '0')}`;
        if (event.start_day) {
            startStr += `-${String(event.start_day).padStart(2, '0')}`;
        }
    }
    startStr += ` ${startEra}`;
    
    if (event.end_year && event.end_year !== event.start_year) {
        let endStr = `${event.end_year}`;
        if (event.end_month) {
            endStr += `-${String(event.end_month).padStart(2, '0')}`;
            if (event.end_day) {
                endStr += `-${String(event.end_day).padStart(2, '0')}`;
            }
        }
        endStr += ` ${endEra}`;
        return `${startStr} to ${endStr}`;
    }
    
    return startStr;
}

/**
 * Clear results and reset UI
 */
function clearResults() {
    currentEvents = [];
    currentResults = [];
    eventResultsContainer.innerHTML = '';
    resultsSection.classList.remove('visible');
    clearBtn.style.display = 'none';
    clearError();
}

/**
 * Show error message
 */
function showError(message) {
    errorContainer.innerHTML = `
        <div class="error-message">
            <strong>Error:</strong> ${escapeHtml(message)}
        </div>
    `;
}

/**
 * Clear error message
 */
function clearError() {
    errorContainer.innerHTML = '';
}

/**
 * Set loading state
 */
function setLoading(isLoading) {
    runBtn.disabled = isLoading;
    modelSelect.disabled = isLoading;
    eventCountInput.disabled = isLoading;
    
    if (isLoading) {
        loadingSpinner.classList.add('active');
    } else {
        loadingSpinner.classList.remove('active');
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Truncate text to specified length
 */
function truncateText(text, maxLength) {
    if (text.length <= maxLength) {
        return text;
    }
    return text.substring(0, maxLength) + '...';
}
