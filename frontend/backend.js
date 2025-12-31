/**
 * Backend for Frontend (BFF)
 * 
 * Manages all API communication with the backend.
 * Translates between orchestrator query parameters and API calls.
 */

class TimelineBackend {
    constructor(orchestrator, apiUrl) {
        this.orchestrator = orchestrator;
        this.apiUrl = apiUrl;
    }
    
    /**
     * Load events for the current viewport
     * @param {Object} params - Query parameters
     * @param {number} params.viewportStart - Start year (absolute value)
     * @param {number} params.viewportEnd - End year (absolute value)
     * @param {boolean} params.isStartBC - Whether start is BC
     * @param {boolean} params.isEndBC - Whether end is BC
     * @param {number} params.limit - Maximum events to return
     * @param {string} params.category - Optional category filter
     */
    async loadViewportEvents(params) {
        try {
            let url = `${this.apiUrl}/events?viewport_start=${params.viewportStart}&viewport_end=${params.viewportEnd}&viewport_is_bc_start=${params.isStartBC}&viewport_is_bc_end=${params.isEndBC}&limit=${params.limit}`;
            
            if (params.category) {
                url += `&category=${encodeURIComponent(params.category)}`;
            }
            
            console.log('[Backend] Loading viewport events:', params);
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const events = await response.json();
            
            console.log('[Backend] Loaded', events.length, 'events');
            
            // Update orchestrator with new events
            this.orchestrator.setEvents(events);
            
            return events;
        } catch (error) {
            console.error('[Backend] Error loading viewport events:', error);
            throw error;
        }
    }
    
    /**
     * Load all categories
     */
    async loadCategories() {
        try {
            const response = await fetch(`${this.apiUrl}/categories`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const categories = await response.json();
            
            console.log('[Backend] Loaded', categories.length, 'categories');
            
            return categories;
        } catch (error) {
            console.error('[Backend] Error loading categories:', error);
            throw error;
        }
    }
    
    /**
     * Load database statistics
     */
    async loadStats() {
        try {
            const response = await fetch(`${this.apiUrl}/stats`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const stats = await response.json();
            
            console.log('[Backend] Loaded stats:', stats);
            
            // Update orchestrator stats
            this.orchestrator.updateStats({
                totalEvents: stats.total_events,
                eventsInScope: stats.total_events // Will be refined by viewport
            });
            
            return stats;
        } catch (error) {
            console.error('[Backend] Error loading stats:', error);
            throw error;
        }
    }
    
    /**
     * Search events by query
     * @param {string} query - Search query
     */
    async searchEvents(query) {
        try {
            const response = await fetch(`${this.apiUrl}/events?search=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const events = await response.json();
            
            console.log('[Backend] Search returned', events.length, 'events');
            
            return events;
        } catch (error) {
            console.error('[Backend] Error searching events:', error);
            throw error;
        }
    }

    // Convenience methods for simpler API
    async getStats() {
        return this.loadStats();
    }

    async getEvents(params = {}) {
        // Simple API that loads all events or with a limit
        // API maximum is 1000
        const limit = Math.min(params.limit || 1000, 1000);
        try {
            const response = await fetch(`${this.apiUrl}/events?limit=${limit}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const events = await response.json();
            
            console.log('[Backend] Loaded', events.length, 'events');
            
            // Update orchestrator with the events
            this.orchestrator.setEvents(events);
            
            return events;
        } catch (error) {
            console.error('[Backend] Error loading events:', error);
            throw error;
        }
    }

    async getCategories() {
        return this.loadCategories();
    }

    /**
     * Get extraction debug information for an event
     * @param {number} eventId - The event ID
     */
    async getExtractionDebug(eventId) {
        try {
            const response = await fetch(`${this.apiUrl}/events/${eventId}/extraction-debug`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const debug = await response.json();
            
            console.log('[Backend] Loaded extraction debug for event', eventId);
            
            return debug;
        } catch (error) {
            console.error('[Backend] Error loading extraction debug:', error);
            throw error;
        }
    }
}

// Initialize backend when orchestrator is ready
window.addEventListener('DOMContentLoaded', () => {
    const API_URL = window.location.protocol + '//' + window.location.hostname + ':8000';
    window.timelineBackend = new TimelineBackend(window.timelineOrchestrator, API_URL);
});
