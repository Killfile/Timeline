/**
 * Legend Module
 * 
 * Manages category colors and legend display.
 * Assigns colors to categories and maintains the visual legend.
 */

class TimelineLegend {
    constructor(orchestrator) {
        this.orchestrator = orchestrator;
        this.colorScale = d3.scaleOrdinal(d3.schemeCategory10);
        this.categories = new Set();
        
        // Subscribe to events changes to update categories
        this.orchestrator.subscribe('events', (events) => this.updateFromEvents(events));
        
        // Subscribe to category filter changes to update visual state
        this.orchestrator.subscribe('categoriesFilterChanged', () => {
            this.updateLegendDisplay();
        });
    }
    
    /**
     * Update categories and colors from event list
     */
    updateFromEvents(events) {
        // Extract unique categories from events
        const newCategories = new Set();
        events.forEach(event => {
            if (event.category) {
                newCategories.add(event.category);
            }
        });
        
        // Update color assignments
        const colorMap = new Map();
        newCategories.forEach(category => {
            colorMap.set(category, this.colorScale(category));
        });
        
        this.categories = newCategories;
        
        // Push to orchestrator
        this.orchestrator.setCategoryColors(colorMap);
        
        // Update legend display
        this.updateLegendDisplay();
        
        console.log('[Legend] Updated', newCategories.size, 'categories');
    }
    
    /**
     * Update the visual legend in the UI
     */
    updateLegendDisplay() {
        const legendContainer = document.getElementById('category-legend');
        if (!legendContainer) return;
        
        // Clear existing legend items
        legendContainer.innerHTML = '';
        
        // Sort categories alphabetically
        const sortedCategories = Array.from(this.categories).sort();
        
        // Create legend items
        sortedCategories.forEach(category => {
            const color = this.orchestrator.getCategoryColor(category);
            
            const item = document.createElement('div');
            item.className = 'legend-item';
            item.dataset.category = category;
            
            // Check if category is currently selected
            const isSelected = window.timelineCategoryFilter ? 
                window.timelineCategoryFilter.isCategorySelected(category) : true;
            
            if (!isSelected) {
                item.classList.add('legend-item-disabled');
            }
            
            item.innerHTML = `
                <span class="legend-color" style="background-color: ${color}"></span>
                <span class="legend-label">${category}</span>
            `;
            
            // Add click handler to toggle category
            item.style.cursor = 'pointer';
            item.addEventListener('click', () => {
                if (window.timelineCategoryFilter) {
                    const newState = window.timelineCategoryFilter.toggleCategory(category);
                    // Update visual state
                    if (newState) {
                        item.classList.remove('legend-item-disabled');
                    } else {
                        item.classList.add('legend-item-disabled');
                    }
                }
            });
            
            legendContainer.appendChild(item);
        });
    }
    
    /**
     * Get color for a category
     */
    getColor(category) {
        return this.orchestrator.getCategoryColor(category);
    }
    
    /**
     * Load categories from backend and populate legend
     */
    async loadCategories(backend) {
        try {
            const categories = await backend.loadCategories();
            
            // Create color assignments for all categories
            const colorMap = new Map();
            categories.forEach(cat => {
                this.categories.add(cat.name);
                colorMap.set(cat.name, this.colorScale(cat.name));
            });
            
            this.orchestrator.setCategoryColors(colorMap);
            this.updateLegendDisplay();
        } catch (error) {
            console.error('[Legend] Error loading categories:', error);
        }
    }

    // Convenience methods for simpler API
    assignColors(events) {
        this.updateFromEvents(events);
    }

    render() {
        this.updateLegendDisplay();
    }
}

// Initialize legend module when orchestrator is ready
window.addEventListener('DOMContentLoaded', () => {
    window.timelineLegend = new TimelineLegend(window.timelineOrchestrator);
});
