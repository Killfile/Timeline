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
        this.totalCategoriesCount = null; // Cache for total categories
    }
    
    /**
     * Load events for the current viewport
     * @param {Object} params - Query parameters
     * @param {number} params.viewportStart - Start year (absolute value)
     * @param {number} params.viewportEnd - End year (absolute value)
     * @param {boolean} params.isStartBC - Whether start is BC
     * @param {boolean} params.isEndBC - Whether end is BC
     * @param {number} params.limit - Maximum events to return
     * @param {string} params.category - Optional single category filter (legacy)
     * @param {Array} params.categories - Optional array of categories to filter
     */
    async loadViewportEvents(params) {
        try {
            let url = `${this.apiUrl}/events?viewport_start=${params.viewportStart}&viewport_end=${params.viewportEnd}&viewport_is_bc_start=${params.isStartBC}&viewport_is_bc_end=${params.isEndBC}&limit=${params.limit}`;
            
            // Handle multiple categories (if provided as array)
            // Only send category filter if specific categories are selected
            // If all categories are selected, don't filter - this allows NULL/uncategorized events through
            const shouldFilterCategories = params.categories && 
                                          Array.isArray(params.categories) && 
                                          params.categories.length > 0 &&
                                          this.totalCategoriesCount &&
                                          params.categories.length < this.totalCategoriesCount;
            
            if (shouldFilterCategories) {
                // Add each category as a separate query parameter
                console.log('[Backend] Filtering by', params.categories.length, 'of', this.totalCategoriesCount, 'categories');
                params.categories.forEach(cat => {
                    url += `&category=${encodeURIComponent(cat)}`;
                });
            } else {
                console.log('[Backend] Not filtering categories (all selected or none) - will include uncategorized events');
            }
            
            if (params.category) {
                // Legacy: single category support
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
            
            // Also fetch the total count of events in this viewport
            await this.updateViewportCount(params);
            
            return events;
        } catch (error) {
            console.error('[Backend] Error loading viewport events:', error);
            throw error;
        }
    }
    
    /**
     * Load events for a specific zone in the 15-bin system.
     * 
     * @param {Object} params - Query parameters
     * @param {number} params.viewportCenter - Center of the viewport (fractional year, negative for BC)
     * @param {number} params.viewportSpan - Width of the viewport in years
     * @param {string} params.zone - Which zone to load: 'left', 'center', or 'right'
     * @param {Array} params.categories - Optional array of categories to filter
     * @param {number} params.limit - Maximum events per bin (default 100)
     * @returns {Promise<Array>} Array of events with bin metadata
     */
    async loadEventsByBins(params) {
        try {
            let url = `${this.apiUrl}/events/bins?viewport_center=${params.viewportCenter}&viewport_span=${params.viewportSpan}&zone=${params.zone}&limit=${params.limit || 100}`;
            
            // Handle category filtering
            const shouldFilterCategories = params.categories && 
                                          Array.isArray(params.categories) && 
                                          params.categories.length > 0 &&
                                          this.totalCategoriesCount &&
                                          params.categories.length < this.totalCategoriesCount;
            
            if (shouldFilterCategories) {
                console.log(`[Backend] Loading ${params.zone} zone with ${params.categories.length} category filters`);
                params.categories.forEach(cat => {
                    url += `&category=${encodeURIComponent(cat)}`;
                });
            } else {
                console.log(`[Backend] Loading ${params.zone} zone (all categories)`);
            }
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const events = await response.json();
            
            console.log(`[Backend] Loaded ${events.length} events for ${params.zone} zone`);
            
            return events;
        } catch (error) {
            console.error(`[Backend] Error loading events for ${params.zone} zone:`, error);
            throw error;
        }
    }
    
    /**
     * Update the eventsInScope count based on viewport
     * @param {Object} params - Viewport parameters
     */
    async updateViewportCount(params) {
        try {
            // Use the count endpoint with viewport params
            let url = `${this.apiUrl}/events/count?viewport_start=${params.viewportStart}&viewport_end=${params.viewportEnd}&viewport_is_bc_start=${params.isStartBC}&viewport_is_bc_end=${params.isEndBC}`;
            
            // Only send category filter if specific categories are selected
            const shouldFilterCategories = params.categories && 
                                          Array.isArray(params.categories) && 
                                          params.categories.length > 0 &&
                                          this.totalCategoriesCount &&
                                          params.categories.length < this.totalCategoriesCount;
            
            if (shouldFilterCategories) {
                params.categories.forEach(cat => {
                    url += `&category=${encodeURIComponent(cat)}`;
                });
            }
            
            if (params.category) {
                // Legacy: single category support
                url += `&category=${encodeURIComponent(params.category)}`;
            }
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            console.log('[Backend] Events in viewport:', data.count);
            
            // Update eventsInScope stat
            const currentStats = this.orchestrator.getStats();
            this.orchestrator.updateStats({
                ...currentStats,
                eventsInScope: data.count
            });
            
            return data.count;
        } catch (error) {
            console.error('[Backend] Error fetching viewport count:', error);
            // Don't throw - this is a nice-to-have stat
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
            
            const data = await response.json();
            const categories = data.categories || [];
            
            // Cache the total count for category filtering logic
            this.totalCategoriesCount = categories.length;
            
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
