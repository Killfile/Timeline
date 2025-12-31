/**
 * Category Filter Module
 * 
 * Manages multi-select category filtering with checkbox UI.
 * Responsibilities:
 * - Load and display categories
 * - Handle checkbox interactions
 * - Maintain selected categories state
 * - Emit filter changes to orchestrator
 * - Default to "all selected" state
 */

class CategoryFilter {
    constructor(orchestrator) {
        this.orchestrator = orchestrator;
        this.allCategories = []; // All available categories
        this.selectedCategories = new Set(); // Currently selected categories
        
        // DOM elements
        this.toggle = document.getElementById('category-filter-toggle');
        this.dropdown = document.getElementById('category-filter-dropdown');
        this.list = document.getElementById('category-filter-list');
        this.selectAllCheckbox = document.getElementById('select-all-categories');
        this.countSpan = document.getElementById('selected-category-count');
        
        this.initializeEventListeners();
    }
    
    /**
     * Initialize event listeners for UI interactions
     */
    initializeEventListeners() {
        // Toggle dropdown visibility
        this.toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            this.dropdown.classList.toggle('hidden');
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.toggle.contains(e.target) && !this.dropdown.contains(e.target)) {
                this.dropdown.classList.add('hidden');
            }
        });
        
        // Handle "Select All" checkbox
        this.selectAllCheckbox.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            if (isChecked) {
                this.selectAll();
            } else {
                this.deselectAll();
            }
        });
    }
    
    /**
     * Load categories from backend and populate UI
     */
    async loadCategories(backend) {
        try {
            const categories = await backend.loadCategories();
            // API returns [{category: "name", count: 42}, ...]
            this.allCategories = categories.map(cat => cat.category);
            
            // Default: select all categories
            this.selectedCategories = new Set(this.allCategories);
            
            this.renderCategoryList();
            this.updateCount();
            
            console.log('[CategoryFilter] Loaded', this.allCategories.length, 'categories');
            
            // Store initial state in orchestrator WITHOUT triggering reload
            // (The initial event load happens in app.js)
            const selectedArray = Array.from(this.selectedCategories);
            this.orchestrator.selectedCategories = selectedArray;
            console.log('[CategoryFilter] Initial state set:', selectedArray.length, 'categories');
        } catch (error) {
            console.error('[CategoryFilter] Error loading categories:', error);
        }
    }
    
    /**
     * Render the category checkbox list
     */
    renderCategoryList() {
        // Clear existing list
        this.list.innerHTML = '';
        
        // Sort categories alphabetically
        const sortedCategories = [...this.allCategories].sort();
        
        // Get color map from orchestrator
        const state = this.orchestrator.getState();
        const colorMap = state ? state.categoryColors : null;
        
        // Create checkbox for each category
        sortedCategories.forEach(category => {
            const item = document.createElement('label');
            item.className = 'category-filter-item';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = category;
            checkbox.checked = this.selectedCategories.has(category);
            
            checkbox.addEventListener('change', (e) => {
                this.handleCategoryToggle(category, e.target.checked);
            });
            
            const label = document.createElement('span');
            label.className = 'category-label';
            label.textContent = category;
            
            // Add color indicator if color is available
            const color = colorMap ? colorMap.get(category) : null;
            if (color) {
                const colorIndicator = document.createElement('span');
                colorIndicator.className = 'category-color-indicator';
                colorIndicator.style.backgroundColor = color;
                item.appendChild(checkbox);
                item.appendChild(label);
                item.appendChild(colorIndicator);
            } else {
                item.appendChild(checkbox);
                item.appendChild(label);
            }
            
            this.list.appendChild(item);
        });
    }
    
    /**
     * Handle individual category checkbox toggle
     */
    handleCategoryToggle(category, isChecked) {
        if (isChecked) {
            this.selectedCategories.add(category);
        } else {
            this.selectedCategories.delete(category);
        }
        
        this.updateSelectAllState();
        this.updateCount();
        this.notifyFilterChange();
    }
    
    /**
     * Select all categories
     */
    selectAll() {
        this.selectedCategories = new Set(this.allCategories);
        
        // Update all checkboxes
        const checkboxes = this.list.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => cb.checked = true);
        
        this.updateCount();
        this.notifyFilterChange();
    }
    
    /**
     * Deselect all categories
     */
    deselectAll() {
        this.selectedCategories.clear();
        
        // Update all checkboxes
        const checkboxes = this.list.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => cb.checked = false);
        
        this.updateCount();
        this.notifyFilterChange();
    }
    
    /**
     * Update "Select All" checkbox state based on individual selections
     */
    updateSelectAllState() {
        const allSelected = this.selectedCategories.size === this.allCategories.length;
        const noneSelected = this.selectedCategories.size === 0;
        
        this.selectAllCheckbox.checked = allSelected;
        this.selectAllCheckbox.indeterminate = !allSelected && !noneSelected;
    }
    
    /**
     * Update the selected count display
     */
    updateCount() {
        this.countSpan.textContent = this.selectedCategories.size;
    }
    
    /**
     * Notify orchestrator of filter change
     */
    notifyFilterChange() {
        const selectedArray = Array.from(this.selectedCategories);
        console.log('[CategoryFilter] Notifying filter change:', selectedArray.length, 'categories selected');
        console.log('[CategoryFilter] Selected categories:', selectedArray);
        this.orchestrator.setSelectedCategories(selectedArray);
    }
    
    /**
     * Get currently selected categories
     */
    getSelectedCategories() {
        return Array.from(this.selectedCategories);
    }
    
    /**
     * Programmatically set selected categories
     */
    setSelectedCategories(categories) {
        this.selectedCategories = new Set(categories);
        this.renderCategoryList();
        this.updateSelectAllState();
        this.updateCount();
        this.notifyFilterChange();
    }
}

// Export to global scope
window.timelineCategoryFilter = null;

// Initialize after DOM loaded
document.addEventListener('DOMContentLoaded', () => {
    window.timelineCategoryFilter = new CategoryFilter(window.timelineOrchestrator);
    console.log('[CategoryFilter] Module initialized');
});
