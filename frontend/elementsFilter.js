/**
 * Elements Filter Module
 *
 * Manages multi-select filtering by timeline elements (strategies).
 * Provides UI for selecting/deselecting elements and communicates changes to orchestrator.
 */

class ElementsFilter {
    constructor(orchestrator) {
        this.orchestrator = orchestrator;
        this.allElements = []; // Array of element names
        this.selectedElements = new Set(); // Set of selected element names
        this.totalEventsCount = null; // Cache for total events count

        // DOM elements
        this.container = null;
        this.list = null;
        this.selectAllCheckbox = null;
        this.countSpan = null;

        this.initialize();
    }

    /**
     * Initialize the filter UI
     */
    initialize() {
        // Create container
        this.container = document.createElement('div');
        this.container.id = 'elements-filter';
        this.container.className = 'filter-container';

        // Create header
        const header = document.createElement('div');
        header.className = 'filter-header';

        const title = document.createElement('h3');
        title.textContent = 'Timeline Elements';
        header.appendChild(title);

        // Select All checkbox
        this.selectAllCheckbox = document.createElement('input');
        this.selectAllCheckbox.type = 'checkbox';
        this.selectAllCheckbox.id = 'select-all-elements';
        this.selectAllCheckbox.checked = true;

        const selectAllLabel = document.createElement('label');
        selectAllLabel.htmlFor = 'select-all-elements';
        selectAllLabel.textContent = 'Select All';

        header.appendChild(this.selectAllCheckbox);
        header.appendChild(selectAllLabel);

        // Count display
        const countContainer = document.createElement('div');
        countContainer.className = 'filter-count';
        countContainer.textContent = 'Selected: ';
        this.countSpan = document.createElement('span');
        this.countSpan.textContent = '0';
        countContainer.appendChild(this.countSpan);
        header.appendChild(countContainer);

        this.container.appendChild(header);

        // Create elements list
        this.list = document.createElement('div');
        this.list.className = 'filter-list';
        this.container.appendChild(this.list);

        // Bind events
        this.selectAllCheckbox.addEventListener('change', () => {
            if (this.selectAllCheckbox.checked) {
                this.selectAll();
            } else {
                this.deselectAll();
            }
        });

        // Load elements from backend
        this.loadElements();

        // Insert into DOM
        const timelineControls = document.getElementById('timeline-controls');
        if (timelineControls) {
            timelineControls.appendChild(this.container);
        } else {
            console.warn('[ElementsFilter] Could not find #timeline-controls element');
        }
    }

    /**
     * Load elements from backend
     */
    async loadElements() {
        try {
            console.log('[ElementsFilter] Loading elements from backend...');
            const response = await fetch(`${window.location.protocol}//${window.location.hostname}:8000/strategies`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.allElements = data.strategies.map(s => s.name).sort();

            console.log(`[ElementsFilter] Loaded ${this.allElements.length} elements:`, this.allElements);

            // Cache total events count for filtering logic
            this.totalEventsCount = data.strategies.reduce((sum, s) => sum + s.event_count, 0);

            // Initially select all elements
            this.selectedElements = new Set(this.allElements);

            this.renderElementsList();
            this.updateSelectAllState();
            this.updateCount();

        } catch (error) {
            console.error('[ElementsFilter] Error loading elements:', error);
            this.showError('Failed to load timeline elements');
        }
    }

    /**
     * Render the elements list
     */
    renderElementsList() {
        this.list.innerHTML = '';

        this.allElements.forEach(element => {
            const item = document.createElement('div');
            item.className = 'filter-item';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `element-${element.replace(/\s+/g, '-').toLowerCase()}`;
            checkbox.checked = this.selectedElements.has(element);

            const label = document.createElement('label');
            label.htmlFor = checkbox.id;
            label.textContent = element;

            item.appendChild(checkbox);
            item.appendChild(label);

            // Bind event
            checkbox.addEventListener('change', () => {
                this.handleElementToggle(element, checkbox.checked);
            });

            this.list.appendChild(item);
        });
    }

    /**
     * Show error message
     */
    showError(message) {
        this.list.innerHTML = `<div class="filter-error">${message}</div>`;
    }

    /**
     * Handle individual element checkbox toggle
     */
    handleElementToggle(element, isChecked) {
        if (isChecked) {
            this.selectedElements.add(element);
        } else {
            this.selectedElements.delete(element);
        }

        this.updateSelectAllState();
        this.updateCount();
        this.notifyFilterChange();
    }

    /**
     * Select all elements
     */
    selectAll() {
        this.selectedElements = new Set(this.allElements);

        // Update all checkboxes
        const checkboxes = this.list.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => cb.checked = true);

        this.updateCount();
        this.notifyFilterChange();
    }

    /**
     * Deselect all elements
     */
    deselectAll() {
        this.selectedElements.clear();

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
        const allSelected = this.selectedElements.size === this.allElements.length;
        const noneSelected = this.selectedElements.size === 0;

        this.selectAllCheckbox.checked = allSelected;
        this.selectAllCheckbox.indeterminate = !allSelected && !noneSelected;
    }

    /**
     * Update the selected count display
     */
    updateCount() {
        this.countSpan.textContent = this.selectedElements.size;
    }

    /**
     * Notify orchestrator of filter change
     */
    notifyFilterChange() {
        const selectedArray = Array.from(this.selectedElements);
        console.log('[ElementsFilter] Notifying filter change:', selectedArray.length, 'elements selected');
        console.log('[ElementsFilter] Selected elements:', selectedArray);
        this.orchestrator.setSelectedElements(selectedArray);
    }

    /**
     * Get currently selected elements
     */
    getSelectedElements() {
        return Array.from(this.selectedElements);
    }

    /**
     * Programmatically set selected elements
     */
    setSelectedElements(elements) {
        this.selectedElements = new Set(elements);
        this.renderElementsList();
        this.updateSelectAllState();
        this.updateCount();
        this.notifyFilterChange();
    }

    /**
     * Toggle a single element on/off
     * Returns the new state (true if enabled, false if disabled)
     */
    toggleElement(element) {
        const isCurrentlySelected = this.selectedElements.has(element);

        if (isCurrentlySelected) {
            this.selectedElements.delete(element);
        } else {
            this.selectedElements.add(element);
        }

        // Update UI
        this.renderElementsList();
        this.updateSelectAllState();
        this.updateCount();
        this.notifyFilterChange();

        return !isCurrentlySelected;
    }

    /**
     * Check if an element is currently selected
     */
    isElementSelected(element) {
        return this.selectedElements.has(element);
    }
}

// Export to global scope
window.timelineElementsFilter = null;

// Initialize after DOM loaded
document.addEventListener('DOMContentLoaded', () => {
    window.timelineElementsFilter = new ElementsFilter(window.timelineOrchestrator);
    console.log('[ElementsFilter] Module initialized');
});