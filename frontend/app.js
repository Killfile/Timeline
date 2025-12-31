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

        // Step 2: Load categories and initialize category filter
        await window.timelineCategoryFilter.loadCategories(window.timelineBackend);
        console.log('Category filter initialized');

        // Step 3: Load events for the initial viewport (3000 BC to 2024 AD)
        // This matches the initial scale domain in timeline.js
        // Use the selected categories from the filter (all by default)
        const selectedCategories = window.timelineCategoryFilter.getSelectedCategories();
        const events = await window.timelineBackend.loadViewportEvents({
            viewportStart: 3000,
            viewportEnd: 2024,
            isStartBC: true,
            isEndBC: false,
            limit: 100,
            categories: selectedCategories.length > 0 ? selectedCategories : undefined
        });
        console.log(`Loaded ${events.length} events for initial viewport`);

        // Step 4: Assign colors to categories
        window.timelineLegend.assignColors(events);
        console.log('Assigned category colors');

        // Step 5: Render the legend
        window.timelineLegend.render();
        console.log('Rendered legend');
        
        // Step 6: Update category filter to show colors
        window.timelineCategoryFilter.renderCategoryList();
        console.log('Updated category filter with colors');

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
