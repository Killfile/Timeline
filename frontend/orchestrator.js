/**
 * Orchestrator (Event Bus)
 * 
 * Central communication hub for all timeline components.
 * Manages state and facilitates communication between modules.
 */

class TimelineOrchestrator {
    constructor() {
        // State
        this.events = [];
        this.laneAssignments = new Map(); // eventId -> laneIndex
        this.totalLanes = 1;
        this.availableLanes = 10; // Fixed number of visible lanes
        this.categoryColors = new Map(); // category -> color
        this.viewport = null; // Current viewport (startDate, endDate, transform)
        this.stats = {
            totalEvents: 0,
            eventsInScope: 0,
            loadedEvents: 0,
            eventsPlaced: 0,
            timeRange: { start: 0, end: 0 }
        };
        
        // Subscribers for state changes
        this.subscribers = {
            events: [],
            eventsUpdated: [], // Alias for events
            laneAssignments: [],
            laneAssignmentsUpdated: [], // Alias for laneAssignments
            categoryColors: [],
            categoryColorsUpdated: [], // Alias for categoryColors
            stats: [],
            scale: [],
            viewport: []
        };
        
        // Current scale (for zoom/pan)
        this.currentScale = null;
    }
    
    // Subscribe to state changes
    subscribe(topic, callback) {
        if (this.subscribers[topic]) {
            this.subscribers[topic].push(callback);
        } else {
            console.warn(`Unknown topic: ${topic}`);
        }
    }
    
    // Notify subscribers of a change
    notify(topic, data) {
        if (this.subscribers[topic]) {
            this.subscribers[topic].forEach(callback => callback(data));
        }
    }
    
    // Update events from backend
    setEvents(events) {
        this.events = events;
        this.stats.loadedEvents = events.length;
        this.notify('events', events);
        this.notify('eventsUpdated', events); // Also notify Updated subscribers
    }
    
    // Get current events
    getEvents() {
        return this.events;
    }
    
    // Update lane assignments from packing module
    setLaneAssignments(assignments, totalLanes, skippedEvents) {
        this.laneAssignments = assignments;
        this.totalLanes = totalLanes;
        this.stats.eventsPlaced = assignments.size;
        const data = { assignments, totalLanes, skippedEvents };
        this.notify('laneAssignments', data);
        this.notify('laneAssignmentsUpdated', data); // Also notify Updated subscribers
    }
    
    // Get lane assignment for an event
    getLaneForEvent(eventId) {
        return this.laneAssignments.get(eventId);
    }
    
    // Get total lanes
    getTotalLanes() {
        return this.totalLanes;
    }
    
    // Set available lanes (from renderer based on screen height)
    setAvailableLanes(count) {
        this.availableLanes = count;
    }
    
    // Get available lanes
    getAvailableLanes() {
        return this.availableLanes;
    }
    
    // Update category colors from legend module
    setCategoryColors(colorMap) {
        this.categoryColors = colorMap;
        this.notify('categoryColors', colorMap);
        this.notify('categoryColorsUpdated', colorMap); // Also notify Updated subscribers
    }
    
    // Get color for a category
    getCategoryColor(category) {
        return this.categoryColors.get(category) || '#666';
    }
    
    // Update stats
    updateStats(updates) {
        Object.assign(this.stats, updates);
        this.notify('stats', this.stats);
    }
    
    // Get stats
    getStats() {
        return this.stats;
    }
    
    // Update current scale (for zoom/pan)
    setScale(scale) {
        this.currentScale = scale;
        this.notify('scale', scale);
    }
    
    // Get current scale
    getScale() {
        return this.currentScale;
    }

    // Set viewport
    setViewport(viewport) {
        this.viewport = viewport;
        this.notify('viewport', viewport);
    }

    // Get viewport
    getViewport() {
        return this.viewport;
    }

    // Get entire state (convenience method)
    getState() {
        return {
            events: this.events,
            laneAssignments: this.laneAssignments,
            totalLanes: this.totalLanes,
            availableLanes: this.availableLanes,
            categoryColors: this.categoryColors,
            stats: this.stats,
            scale: this.currentScale,
            viewport: this.viewport
        };
    }

    // Set state (convenience method for bulk updates)
    setState(updates) {
        if (updates.events !== undefined) {
            this.setEvents(updates.events);
        }
        if (updates.laneAssignments !== undefined) {
            this.setLaneAssignments(updates.laneAssignments, updates.totalLanes || this.totalLanes, updates.skippedEvents || []);
        }
        if (updates.categoryColors !== undefined) {
            this.setCategoryColors(updates.categoryColors);
        }
        if (updates.stats !== undefined) {
            this.updateStats(updates.stats);
        }
        if (updates.scale !== undefined) {
            this.setScale(updates.scale);
        }
        if (updates.availableLanes !== undefined) {
            this.setAvailableLanes(updates.availableLanes);
        }
        if (updates.viewport !== undefined) {
            this.setViewport(updates.viewport);
        }
    }
}

// Create global orchestrator instance
window.timelineOrchestrator = new TimelineOrchestrator();
