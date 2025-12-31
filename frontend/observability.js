/**
 * Observability Module
 * 
 * Manages and displays timeline statistics and metrics.
 * Subscribes to orchestrator state changes and updates UI.
 */

class TimelineObservability {
    constructor(orchestrator) {
        this.orchestrator = orchestrator;
        
        // Subscribe to stats updates
        this.orchestrator.subscribe('stats', (stats) => this.updateDisplay(stats));
        this.orchestrator.subscribe('laneAssignments', () => this.updateFromOrchestrator());
        this.orchestrator.subscribe('events', () => this.updateFromOrchestrator());
    }
    
    /**
     * Update display with new stats
     */
    updateDisplay(stats) {
        // Total events in database
        const totalEventsEl = document.getElementById('total-events');
        if (totalEventsEl) {
            totalEventsEl.textContent = stats.totalEvents || 0;
        }
        
        // Events in scope (in current time range)
        const eventsInScopeEl = document.getElementById('events-in-scope');
        if (eventsInScopeEl) {
            eventsInScopeEl.textContent = stats.eventsInScope || 0;
        }
        
        // Loaded events (returned from API, capped by limit)
        const loadedEventsEl = document.getElementById('loaded-events');
        if (loadedEventsEl) {
            loadedEventsEl.textContent = stats.loadedEvents || 0;
        }
        
        // Events placed (successfully rendered on timeline)
        const eventsPlacedEl = document.getElementById('events-placed');
        if (eventsPlacedEl) {
            eventsPlacedEl.textContent = stats.eventsPlaced || 0;
        }
        
        // Time range
        const timeRangeEl = document.getElementById('time-range');
        if (timeRangeEl && stats.timeRange) {
            const startLabel = this.formatYear(stats.timeRange.start);
            const endLabel = this.formatYear(stats.timeRange.end);
            timeRangeEl.textContent = `${startLabel} to ${endLabel}`;
        }
        
        console.log('[Observability] Stats updated:', stats);
    }
    
    /**
     * Update stats from current orchestrator state
     */
    updateFromOrchestrator() {
        const stats = this.orchestrator.getStats();
        stats.loadedEvents = this.orchestrator.getEvents().length;
        stats.eventsPlaced = this.orchestrator.laneAssignments.size;
        this.updateDisplay(stats);
    }
    
    /**
     * Format year for display (handle BC/AD)
     */
    formatYear(year) {
        if (year === null || year === undefined) return '?';
        
        if (year < 0) {
            return `${Math.abs(Math.round(year))} BC`;
        } else if (year === 0) {
            return '1 BC'; // No year 0
        } else {
            return `${Math.round(year)} AD`;
        }
    }
    
    /**
     * Update time range display based on scale
     */
    updateTimeRange(scale) {
        if (!scale) return;
        
        const [start, end] = scale.domain();
        const stats = this.orchestrator.getStats();
        stats.timeRange = { start, end };
        this.orchestrator.updateStats(stats);
    }
}

// Initialize observability module when orchestrator is ready
window.addEventListener('DOMContentLoaded', () => {
    window.timelineObservability = new TimelineObservability(window.timelineOrchestrator);
});
