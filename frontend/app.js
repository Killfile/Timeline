/**
 * Application Bootstrap Module
 * 
 * This file initializes the entire timeline application by:
 * 1. Loading initial data from the backend
 * 2. Processing data through the packing algorithm
 * 3. Assigning colors via the legend module
 * 4. Triggering initial renders
 */

/**
 * Bootstrap the application
 * Loads data and initializes all modules
 */
async function initializeApp() {
    try {
        console.log('Timeline app initializing...');

        // Step 1: Load database stats
        const stats = await window.timelineBackend.getStats();
        console.log('Loaded stats:', stats);

        // Step 2: Load events for the initial viewport (3000 BC to 2024 AD)
        // This matches the initial scale domain in timeline.js
        const events = await window.timelineBackend.loadViewportEvents({
            viewportStart: 3000,
            viewportEnd: 2024,
            isStartBC: true,
            isEndBC: false,
            limit: 100
        });
        console.log(`Loaded ${events.length} events for initial viewport`);

        // Step 3: Assign colors to categories
        window.timelineLegend.assignColors(events);
        console.log('Assigned category colors');

        // Step 4: Render the legend
        window.timelineLegend.render();
        console.log('Rendered legend');

        // Lane assignments will be calculated by timeline.js after initialization

        console.log('Timeline app initialized successfully');
    } catch (error) {
        console.error('Failed to initialize timeline app:', error);
        alert(`Failed to load timeline data: ${error.message}`);
    }
}

// Start the application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Small delay to ensure all modules are loaded
    setTimeout(initializeApp, 100);
});
