// Candidate 5: Alternative Rendering for Low-Precision Events
// Low-precision events (precision = 0) are always rendered as small dots regardless of visual width

const API_URL = 'http://localhost:8000';

class TimelineRenderer {
    constructor() {
        this.canvas = document.getElementById('timeline-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.tooltip = document.getElementById('tooltip');

        // Viewport state
        this.viewportCenter = 0;
        this.viewportSpan = 2000;
        this.minSpan = 1;
        this.maxSpan = 10000;

        // Controls
        this.settingsButton = document.getElementById('settings-button');
        this.settingsMenu = document.getElementById('settings-menu');
        this.filterPanel = document.getElementById('filter-panel');
        this.searchPanel = document.getElementById('search-panel');
        this.searchInput = document.getElementById('search-input');
        this.searchResults = document.getElementById('search-results');

        // Category filtering
        this.activeCategories = new Set();
        this.allCategories = new Set();
        this.allCategoryData = []; // Store full category data from API
        this.categorySearchInput = document.getElementById('category-search');
        this.filteredEvents = null; // null means no filtering active

        // Viewport-aware loading system
        this.eventCache = new Map();
        this.currentLoadingStrategy = 'standard';
        this.loadingStrategies = {
            // Very zoomed out - load major events only, with strict viewport filtering
            'overview': {
                spanRange: [5000, 10000],
                limit: 100, // Higher limit since we're filtering strictly
                weightMultiplier: 8, // Higher weight for major events
                cacheSize: 25,
                description: 'Overview Mode (Filtered)',
                viewportBuffer: 0.1 // 10% buffer for loading
            },
            // Medium zoom - standard loading with viewport awareness
            'standard': {
                spanRange: [1000, 4999],
                limit: 200,
                weightMultiplier: 3,
                cacheSize: 20,
                description: 'Standard Mode (Filtered)',
                viewportBuffer: 0.2 // 20% buffer
            },
            // Zoomed in - detailed loading with strict viewport bounds
            'detailed': {
                spanRange: [100, 999],
                limit: 400,
                weightMultiplier: 1.5,
                cacheSize: 15,
                description: 'Detailed Mode (Filtered)',
                viewportBuffer: 0.3 // 30% buffer for smoother panning
            },
            // Very zoomed in - high density with minimal buffer
            'micro': {
                spanRange: [1, 99],
                limit: 600,
                weightMultiplier: 0.8,
                cacheSize: 8,
                description: 'Micro Mode (Filtered)',
                viewportBuffer: 0.5 // 50% buffer for very zoomed in views
            }
        };

        // Loading state
        this.isLoading = false;
        this.loadingIndicator = document.getElementById('loading-indicator');

        // Rendering
        this.events = [];
        this.isDragging = false;
        this.lastMouseX = 0;
        this.lastMouseY = 0;
        this.hoveredEvent = null;

        // Band system
        this.bandLayers = 1;
        this.bandHeight = 60;
        this.minEventWidth = 20;
        this.maxEventWidth = 150;

        // Colors for different event types/categories
        this.eventColors = [
            '#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe',
            '#43e97b', '#38f9d7', '#fa709a', '#fee140', '#ffa751'
        ];

        // Animation
        this.animationTime = 0;

        this.setupCanvas();
        this.setupEventListeners();
        this.determineLoadingStrategy();
        this.loadEventsForViewport();
        this.animate();
    }

    setupCanvas() {
        const resize = () => {
            this.canvas.width = window.innerWidth * window.devicePixelRatio;
            this.canvas.height = window.innerHeight * window.devicePixelRatio;
            this.canvas.style.width = window.innerWidth + 'px';
            this.canvas.style.height = window.innerHeight + 'px';
            this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
            this.render();
        };
        window.addEventListener('resize', resize);
        resize();
    }

    setupEventListeners() {
        this.canvas.addEventListener('mousedown', (e) => {
            this.isDragging = false; // Reset drag state
            this.dragStartX = e.clientX;
            this.dragStartY = e.clientY;
            this.lastMouseX = e.clientX;
            this.lastMouseY = e.clientY;
            this.hasDragged = false; // Track if significant drag occurred
        });

        window.addEventListener('mousemove', (e) => {
            if (this.dragStartX !== undefined) {
                const dx = e.clientX - this.dragStartX;
                const dy = e.clientY - this.dragStartY;
                const distance = Math.sqrt(dx * dx + dy * dy);

                // Consider it a drag if moved more than 5 pixels
                if (distance > 5) {
                    this.isDragging = true;
                    // Only set hasDragged when we actually start dragging (not just moving mouse)
                    if (!this.hasDragged) {
                        this.hasDragged = true;
                        this.canvas.parentElement.classList.add('dragging');
                    }
                }

                if (this.isDragging) {
                    const deltaX = e.clientX - this.lastMouseX;
                    const pixelsPerYear = this.canvas.width / window.devicePixelRatio / this.viewportSpan;
                    const deltaCenter = -deltaX / pixelsPerYear;

                    this.viewportCenter += deltaCenter;
                    this.lastMouseX = e.clientX;
                    this.lastMouseY = e.clientY;

                    this.loadEventsForViewport();
                    this.scheduleRender();
                } else {
                    this.updateHover(e);
                }
            }
        });

        // Add canvas mousemove for hover detection when not dragging
        this.canvas.addEventListener('mousemove', (e) => {
            if (this.dragStartX === undefined) {
                this.updateHover(e);
            }
        });

        window.addEventListener('mouseup', () => {
            if (this.isDragging) {
                this.canvas.parentElement.classList.remove('dragging');
            }
            this.isDragging = false;
            this.dragStartX = undefined;
            this.dragStartY = undefined;
        });

        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();

            // Debounced zoom with requestAnimationFrame
            const zoomDirection = e.deltaY > 0 ? 1 : -1;
            const scrollSpeed = Math.abs(e.deltaY);

            // Accumulate zoom changes
            if (!this.zoomAccumulator) this.zoomAccumulator = 0;
            const zoomFactor = 1 + (0.02 * (scrollSpeed / 100)); // Base zoom factor
            this.zoomAccumulator += zoomDirection * 0.02;

            // Debounce zoom updates
            if (!this.zoomTimeout) {
                this.zoomTimeout = setTimeout(() => {
                    this.applyZoomChange();
                }, 16); // ~60fps
            }
        }, { passive: false });

        // Controls
        // Settings Button
        this.settingsButton.addEventListener('click', () => {
            this.settingsMenu.classList.toggle('active');
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.settingsButton.contains(e.target) && !this.settingsMenu.contains(e.target)) {
                this.settingsMenu.classList.remove('active');
            }
        });

        // FAB Menu Items
        document.getElementById('fab-zoom-in').addEventListener('click', () => {
            const newSpan = Math.max(this.minSpan, this.viewportSpan * 0.8);
            if (newSpan !== this.viewportSpan) {
                const oldStrategy = this.currentLoadingStrategy;
                this.viewportSpan = newSpan;
                this.determineLoadingStrategy();

                if (oldStrategy !== this.currentLoadingStrategy) {
                    this.eventCache.clear();
                    this.updateCacheStatus();
                }

                this.loadEventsForViewport();
                this.scheduleRender();
            }
            // Don't collapse FAB menu for zoom buttons
        });

        document.getElementById('fab-zoom-out').addEventListener('click', () => {
            const newSpan = Math.min(this.maxSpan, this.viewportSpan * 1.2);
            if (newSpan !== this.viewportSpan) {
                const oldStrategy = this.currentLoadingStrategy;
                this.viewportSpan = newSpan;
                this.determineLoadingStrategy();

                if (oldStrategy !== this.currentLoadingStrategy) {
                    this.eventCache.clear();
                    this.updateCacheStatus();
                }

                this.loadEventsForViewport();
                this.scheduleRender();
            }
            // Don't collapse FAB menu for zoom buttons
        });

        document.getElementById('fab-reset').addEventListener('click', () => {
            this.viewportCenter = 0;
            this.viewportSpan = 10000; // Full timeline span
            this.eventCache.clear();
            this.determineLoadingStrategy();
            this.loadEventsForViewport();
            this.scheduleRender();
            this.settingsMenu.classList.remove('active');
        });

        document.getElementById('fab-filter').addEventListener('click', () => {
            this.showFilterPanel();
            this.settingsMenu.classList.remove('active');
        });

        document.getElementById('fab-search').addEventListener('click', () => {
            this.showSearchPanel();
            this.settingsMenu.classList.remove('active');
        });

        // Filter Panel
        document.getElementById('filter-close').addEventListener('click', () => {
            this.hideFilterPanel();
        });

        // Category search input
        this.categorySearchInput.addEventListener('input', (e) => {
            this.filterCategories(e.target.value);
        });

        // Search Panel
        document.getElementById('search-close').addEventListener('click', () => {
            this.hideSearchPanel();
        });

        this.searchInput.addEventListener('input', (e) => {
            this.performSearch(e.target.value);
        });

        // Event click handler for modal
        this.canvas.addEventListener('click', (e) => {
            if (this.hasDragged) {
                this.hasDragged = false; // Reset for next click
                return; // Don't open modal if we just finished dragging
            }

            const { x: mouseX, y: mouseY } = this.getCanvasCoordinates(e);

            for (const event of this.events) {
                if (event.visualBounds && event.y !== undefined) {
                    // Use the actual visual bounds that were rendered
                    const visualHeight = this.bandHeight * 0.7;
                    const bandTop = event.y - visualHeight/2;
                    const bandBottom = event.y + visualHeight/2;
                    
                    // Use visual bounds for horizontal detection
                    if (mouseX >= event.visualBounds.left && mouseX <= event.visualBounds.right &&
                        mouseY >= bandTop && mouseY <= bandBottom) {
                        this.showEventModal(event);
                        break;
                    }
                }
            }
        });

        // Modal event listeners
        document.getElementById('modal-close').addEventListener('click', () => {
            this.hideEventModal();
        });

        document.getElementById('event-modal').addEventListener('click', (e) => {
            if (e.target === document.getElementById('event-modal')) {
                this.hideEventModal();
            }
        });

        // Prevent wheel events in modal from triggering canvas zoom
        document.getElementById('event-modal').addEventListener('wheel', (e) => {
            e.stopPropagation();
        }, { passive: false });

        // Close modal on Escape key
        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && document.getElementById('event-modal').style.display === 'block') {
                this.hideEventModal();
            }
        });
    }

    determineLoadingStrategy() {
        for (const [strategyName, strategy] of Object.entries(this.loadingStrategies)) {
            const [minSpan, maxSpan] = strategy.spanRange;
            if (this.viewportSpan >= minSpan && this.viewportSpan <= maxSpan) {
                this.currentLoadingStrategy = strategyName;
                this.updateLoadingStrategyDisplay();
                return;
            }
        }
        // Default fallback
        this.currentLoadingStrategy = 'standard';
        this.updateLoadingStrategyDisplay();
    }

    updateLoadingStrategyDisplay() {
        const strategy = this.loadingStrategies[this.currentLoadingStrategy];
        document.getElementById('loading-strategy').textContent = strategy.description;
    }

    loadEventsForViewport() {
        const cacheKey = this.getCacheKey(this.viewportCenter, this.viewportSpan);

        if (this.eventCache.has(cacheKey)) {
            this.events = this.eventCache.get(cacheKey);
            this.calculateBandPositions();
            this.applyCategoryFilter();
            return;
        }

        // Load with viewport-aware strategy
        this.loadEventsWithViewportAwareness();
    }

    async loadEventsWithViewportAwareness() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoadingIndicator();

        const strategy = this.loadingStrategies[this.currentLoadingStrategy];

        // VIEWPORT-AWARE LOADING: Calculate extended viewport bounds for loading
        const viewportBuffer = strategy.viewportBuffer;
        const extendedSpan = this.viewportSpan * (1 + viewportBuffer);
        const extendedCenter = this.viewportCenter;

        // Use higher weight multiplier to prioritize events that fit within viewport
        const maxWeight = this.viewportSpan * strategy.weightMultiplier;

        try {
            // Request events from extended viewport but with higher weight requirements
            const response = await fetch(
                `${API_URL}/events/bins?viewport_center=${extendedCenter}&viewport_span=${extendedSpan}&zone=center&limit=${strategy.limit}&max_weight=${maxWeight}`
            );

            if (response.ok) {
                let events = await response.json();

                // VIEWPORT-AWARE FILTERING: Filter events that overlap with the viewport
                const viewportLeft = this.viewportCenter - this.viewportSpan / 2;
                const viewportRight = this.viewportCenter + this.viewportSpan / 2;

                events = events.filter(event => {
                    const startYear = this.calculateFractionalYear(event.start_year, event.is_bc_start, event.start_month, event.start_day);
                    const endYear = this.calculateFractionalYear(event.end_year, event.is_bc_end, event.end_month, event.end_day);
                    
                    // Include event if it overlaps with viewport (not entirely outside)
                    if (endYear < viewportLeft || startYear > viewportRight) {
                        return false;
                    }
                    
                    // Calculate what percentage of the event is visible in viewport
                    const eventDuration = endYear - startYear;
                    if (eventDuration === 0) {
                        return true; // Point events are always included if they overlap
                    }
                    
                    const visibleStart = Math.max(startYear, viewportLeft);
                    const visibleEnd = Math.min(endYear, viewportRight);
                    const visibleDuration = visibleEnd - visibleStart;
                    const visiblePercentage = visibleDuration / eventDuration;
                    
                    // Only include if at least 40% of the event is visible (less than 60% outside)
                    return visiblePercentage >= 0.4;
                });

                // HYBRID DEDUPLICATION: Combine multiple strategies for optimal event selection
                // Step 1: Remove exact ID duplicates (keep first occurrence)
                const seenIds = new Set();
                events = events.filter(event => {
                    if (seenIds.has(event.id)) {
                        return false;
                    }
                    seenIds.add(event.id);
                    return true;
                });

                // Step 2: Apply title-based deduplication with priority scoring
                const titleMap = new Map();
                events.forEach(event => {
                    const title = event.title || 'Untitled';
                    const startYear = this.calculateFractionalYear(event.start_year, event.is_bc_start, event.start_month, event.start_day);
                    const endYear = this.calculateFractionalYear(event.end_year, event.is_bc_end, event.end_month, event.end_day);
                    const duration = Math.abs(endYear - startYear);

                    // Calculate comprehensive priority score
                    let priority = duration; // Base priority on duration
                    if (event.description && event.description.length > 50) priority += 20;
                    if (event.start_month && event.end_month) priority += 15; // Complete date info
                    if (event.importance_score) priority += event.importance_score * 10;
                    if (title.length > 10 && title.length < 100) priority += 10; // Good title length
                    if (!title.includes('Untitled') && !title.includes('Unknown')) priority += 5;

                    if (!titleMap.has(title) || priority > titleMap.get(title).priority) {
                        titleMap.set(title, { event, priority, startYear, endYear });
                    }
                });

                // Step 3: Apply time-based conflict resolution for remaining events
                const finalEvents = [];
                const titleTimeSlots = new Map();

                for (const { event, startYear, endYear } of Array.from(titleMap.values()).map(item => item)) {
                    const title = event.title || 'Untitled';

                    if (!titleTimeSlots.has(title)) {
                        titleTimeSlots.set(title, []);
                    }

                    const timeSlots = titleTimeSlots.get(title);
                    let hasOverlap = false;

                    for (const slot of timeSlots) {
                        if (!(endYear <= slot.start || startYear >= slot.end)) {
                            hasOverlap = true;
                            break;
                        }
                    }

                    if (!hasOverlap) {
                        finalEvents.push(event);
                        timeSlots.push({ start: startYear, end: endYear });
                    }
                }

                events = finalEvents;

                const cacheKey = this.getCacheKey(this.viewportCenter, this.viewportSpan);
                this.eventCache.set(cacheKey, events);
                this.events = events;
                this.calculateBandPositions();
                this.applyCategoryFilter();
                this.render();

                // Clean up old cache entries if we exceed the limit
                this.cleanupCache(strategy.cacheSize);
                this.updateCacheStatus();
            }
        } catch (error) {
            console.error('Failed to load events:', error);
        } finally {
            this.isLoading = false;
            this.hideLoadingIndicator();
        }
    }

    getCacheKey(center, span) {
        // More precise cache keys for viewport-aware loading
        const strategy = this.loadingStrategies[this.currentLoadingStrategy];
        const centerRounding = Math.max(5, span / 200); // More precise for filtered results
        const spanRounding = Math.max(2, span / 400);

        const roundedCenter = Math.round(center / centerRounding) * centerRounding;
        const roundedSpan = Math.round(span / spanRounding) * spanRounding;
        return `${this.currentLoadingStrategy}-${roundedCenter}-${roundedSpan}`;
    }

    cleanupCache(maxSize) {
        if (this.eventCache.size <= maxSize) return;

        // Remove oldest entries (simple LRU approximation)
        const entries = Array.from(this.eventCache.entries());
        const toRemove = entries.slice(0, entries.length - maxSize);

        for (const [key] of toRemove) {
            this.eventCache.delete(key);
        }
    }

    updateCacheStatus() {
        document.getElementById('cache-status').textContent = `${this.eventCache.size} regions cached`;
    }

    showLoadingIndicator() {
        this.loadingIndicator.classList.add('visible');
    }

    hideLoadingIndicator() {
        this.loadingIndicator.classList.remove('visible');
    }

    calculateBandPositions() {
        const w = this.canvas.width / window.devicePixelRatio;
        const h = this.canvas.height / window.devicePixelRatio;

        // Sort events by start time for consistent processing
        this.events.sort((a, b) => {
            const aStart = this.calculateFractionalYear(a.start_year, a.is_bc_start, a.start_month, a.start_day);
            const bStart = this.calculateFractionalYear(b.start_year, b.is_bc_start, b.start_month, b.start_day);
            return aStart - bStart;
        });

        // Calculate event properties and visual dimensions
        const strategy = this.loadingStrategies[this.currentLoadingStrategy];
        const widthMultiplier = strategy.spanRange[1] / this.viewportSpan;

        for (const event of this.events) {
            // Skip events with invalid year data (check for null/undefined/NaN, but allow 0 which is valid for year 1 BC)
            if (event.start_year === null || event.start_year === undefined || !isFinite(event.start_year)) {
                console.warn(`Skipping event with invalid start_year: "${event.title}" (start_year=${event.start_year}, is_bc=${event.is_bc_start})`);
                continue;
            }
            if (event.end_year === null || event.end_year === undefined || !isFinite(event.end_year)) {
                console.warn(`Skipping event with invalid end_year: "${event.title}" (end_year=${event.end_year}, is_bc=${event.is_bc_end})`);
                continue;
            }

            const startYear = this.calculateFractionalYear(event.start_year, event.is_bc_start, event.start_month, event.start_day);
            const endYear = this.calculateFractionalYear(event.end_year, event.is_bc_end, event.end_month, event.end_day);
            const duration = Math.max(0.1, endYear - startYear);

            // Calculate visual width based on zoom level
            const isImportant = this.isImportantEvent(event);
            const importanceBoost = isImportant ? 1.3 : 1.0;
            
            let widthRatio;
            if (this.viewportSpan < 80) {
                widthRatio = Math.min((duration * importanceBoost) / 3, 1.0);
            } else if (this.viewportSpan < 250) {
                const linearRatio = (duration * importanceBoost) / 12;
                const logRatio = Math.log(duration + 1) / Math.log(25 + 1);
                widthRatio = (linearRatio * 0.6 + logRatio * 0.4);
            } else if (this.viewportSpan < 800) {
                const linearRatio = (duration * importanceBoost) / 40;
                const logRatio = Math.log(duration + 1) / Math.log(90 + 1);
                widthRatio = (linearRatio * 0.5 + logRatio * 0.5);
            } else if (this.viewportSpan < 3000) {
                const linearRatio = (duration * importanceBoost) / 120;
                const logRatio = Math.log(duration + 1) / Math.log(180 + 1);
                widthRatio = (linearRatio * 0.3 + logRatio * 0.7);
            } else {
                widthRatio = Math.max(0.1, Math.log(duration + 1) / Math.log(400 + 1)) * importanceBoost;
            }

            event.width = (this.minEventWidth + (this.maxEventWidth - this.minEventWidth) * Math.min(widthRatio, 1)) * widthMultiplier;
            event.startYear = startYear;
            event.endYear = endYear;
            event.duration = duration;
            event.color = this.eventColors[event.id % this.eventColors.length];
            
            // Calculate visual bounds for collision detection
            this.calculateEventVisualBounds(event);
        }

        // Position events with temporal conflict resolution
        this.positionEventsWithTemporalResolution();
    }

    calculateEventVisualBounds(event) {
        // Calculate the actual visual space occupied by each event type
        const startX = this.yearToX(event.startYear);
        const endX = this.yearToX(event.endYear);
        const visualWidth = Math.abs(endX - startX);
        
        // Determine render style and visual bounds
        if (visualWidth < 8) {
            // Dot: small circular area - use radius 6 to prevent overlap
            const dotRadius = 6;
            event.visualBounds = {
                left: startX - dotRadius,
                right: startX + dotRadius,
                width: dotRadius * 2,
                type: 'dot'
            };
        } else if (visualWidth < 20) {
            // Line: line with arrow, use actual visual width with minimum for visibility
            const lineLength = Math.max(visualWidth, 8);
            event.visualBounds = {
                left: startX,
                right: startX + lineLength,
                width: lineLength,
                type: 'line'
            };
        } else {
            // Bar: full width bar
            // Normalize left/right for BC events where endX < startX
            event.visualBounds = {
                left: Math.min(startX, endX),
                right: Math.max(startX, endX),
                width: visualWidth,
                type: 'bar'
            };
        }
    }

    positionEventsWithTemporalResolution() {
        const w = this.canvas.width / window.devicePixelRatio;
        const h = this.canvas.height / window.devicePixelRatio;
        const centerY = h / 2;
        const maxBands = Math.floor(h / this.bandHeight);
        
        // Validate canvas dimensions
        if (h <= 0 || maxBands <= 0) {
            console.warn('Invalid canvas dimensions for band positioning:', { w, h, maxBands, bandHeight: this.bandHeight });
            return;
        }
        
        // Special handling for low-precision events at deep zoom
        const isDeepZoom = this.viewportSpan <= 10;
        const lowPrecisionEvents = [];
        const normalEvents = [];
        
        // Separate events by precision
        for (const event of this.events) {
            if (isDeepZoom && event.precision === 0.0) {
                lowPrecisionEvents.push(event);
            } else {
                normalEvents.push(event);
            }
        }
        
        // Track band occupancy with temporal ranges and event references
        const bandOccupancy = new Map(); // band -> array of {event, startTime, endTime}
        
        // Position normal events with collision detection
        for (const event of normalEvents) {
            const eventStart = event.startYear;
            const eventEnd = event.endYear;
            
            // Debug: Check for invalid temporal data
            if (!isFinite(eventStart) || !isFinite(eventEnd)) {
                console.error('Event has invalid temporal data:', {
                    title: event.title,
                    startYear: eventStart,
                    endYear: eventEnd,
                    raw: { start_year: event.start_year, end_year: event.end_year }
                });
            }
            
            // Find available band with temporal conflict resolution
            let assignedBand = -1;
            
            // Try bands starting from outermost, working inward (skip band 0 for axis)
            const bandOrder = [];
            for (let i = 1; i < maxBands; i++) {
                // Alternate between upper and lower bands
                if (i % 2 === 1) {
                    bandOrder.push(Math.floor(i / 2) + 1); // Upper bands: 1, 2, 3...
                    bandOrder.push(-Math.floor(i / 2) - 1); // Lower bands: -1, -2, -3...
                }
            }
            
            const collisionInfo = [];
            
            for (const bandOffset of bandOrder) {
                const band = Math.floor(maxBands / 2) + bandOffset;
                if (band < 0 || band >= maxBands) continue;
                
                // Check for temporal conflicts in this band
                const bandEvents = bandOccupancy.get(band) || [];
                let hasConflict = false;
                const conflictingEvents = [];
                
                for (const occupant of bandEvents) {
                    // Pure temporal overlap check - if times overlap, can't share band
                    if (!(eventEnd <= occupant.startTime || eventStart >= occupant.endTime)) {
                        hasConflict = true;
                        conflictingEvents.push(occupant);
                    }
                }
                
                if (!hasConflict) {
                    assignedBand = band;
                    break;
                } else if (conflictingEvents.length > 0) {
                    // Record collision details for logging
                    collisionInfo.push({ band, conflicts: conflictingEvents });
                }
            }
            
            // If no conflict-free band found, skip this event
            if (assignedBand === -1) {
                // Build detailed collision report showing ALL conflicts
                let collisionReport = `SKIPPED EVENT: "${event.title}" (${eventStart.toFixed(1)} to ${eventEnd.toFixed(1)}) - no conflict-free band available (checked ${maxBands} bands)\n`;
                
                // Show ALL bands with conflicts
                for (const { band, conflicts } of collisionInfo) {
                    collisionReport += `  Band ${band}: conflicts with ${conflicts.length} event(s)\n`;
                    
                    // Show ALL conflicting events
                    for (const conflict of conflicts) {
                        collisionReport += `    - "${conflict.event.title}" (${conflict.startTime.toFixed(1)} to ${conflict.endTime.toFixed(1)})\n`;
                    }
                }
                
                console.info(collisionReport);
                continue;
            }
            
            // Position the event in the assigned band
            if (!isFinite(assignedBand)) {
                console.info(`SKIPPED EVENT: "${event.title}" (${eventStart} to ${eventEnd}) - invalid band assignment`);
                continue; // Skip this event
            }
            
            const y = centerY + (assignedBand - maxBands/2) * this.bandHeight + this.bandHeight/2;
            if (!isFinite(y)) {
                console.warn('Invalid Y position for event:', event, { assignedBand, maxBands, centerY, bandHeight: this.bandHeight });
                continue; // Skip this event
            }
            
            event.x = this.yearToX(event.startYear);
            event.y = y;
            event.band = assignedBand;
            
            // Record occupancy with event reference
            if (!bandOccupancy.has(assignedBand)) {
                bandOccupancy.set(assignedBand, []);
            }
            bandOccupancy.get(assignedBand).push({
                event: event,
                startTime: eventStart,
                endTime: eventEnd
            });
        }
        
        // Special positioning for low-precision events at deep zoom
        // These are distributed evenly on the axis as dots, ignoring collisions
        if (isDeepZoom && lowPrecisionEvents.length > 0) {
            // Group low-precision events by their year range
            const yearGroups = new Map(); // Map<yearRange, events[]>
            
            for (const event of lowPrecisionEvents) {
                const startYear = Math.floor(event.startYear);
                const endYear = Math.floor(event.endYear);
                const key = `${startYear}_${endYear}`; // Use underscore to avoid ambiguity with negative numbers
                
                if (!yearGroups.has(key)) {
                    yearGroups.set(key, []);
                }
                yearGroups.get(key).push(event);
            }
            
            // Position each group evenly within its year range
            for (const [key, events] of yearGroups) {
                const [startYear, endYear] = key.split('_').map(Number);
                const yearSpan = Math.abs(endYear - startYear);
                const count = events.length;
                
                // Calculate even spacing across the year range
                events.forEach((event, index) => {
                    // Distribute evenly: position = start + (index + 0.5) * (span / count)
                    const fraction = (index + 0.5) / count;
                    // For BC events (startYear > endYear), go backwards in time
                    const positionYear = startYear > endYear 
                        ? startYear - fraction * yearSpan
                        : startYear + fraction * yearSpan;
                    
                    event.x = this.yearToX(positionYear);
                    event.y = centerY; // On the axis
                    event.band = Math.floor(maxBands / 2); // Center band
                    
                    // Force dot rendering by setting visualBounds
                    event.visualBounds = {
                        left: event.x - 6,
                        right: event.x + 6,
                        width: 12,
                        type: 'dot'
                    };
                });
            }
        }

        this.bandLayers = Math.max(1, Math.max(...this.events.map(e => e.band || 0)) + 1);
    }

    visualElementsOverlap(bounds1, bounds2) {
        // Check if two visual elements overlap with minimum spacing
        const minSpacing = 4; // Minimum pixels between visual elements
        return !(bounds1.right + minSpacing < bounds2.left || bounds2.right + minSpacing < bounds1.left);
    }

    findLeastConflictedBand(bandOccupancy, eventStart, eventEnd, maxBands) {
        let bestBand = 1; // Default to first upper band
        let minConflicts = Infinity;
        
        const debugInfo = [];
        const centerBand = Math.floor(maxBands / 2);
        
        for (let band = 0; band < maxBands; band++) {
            // Skip center band (for axis) and band 0
            if (band === centerBand || band === 0) continue;
            
            const bandEvents = bandOccupancy.get(band) || [];
            let conflictCount = 0;
            
            for (const [otherStart, otherEnd] of bandEvents) {
                // Pure temporal overlap
                if (!(eventEnd <= otherStart || eventStart >= otherEnd)) {
                    conflictCount++;
                }
            }
            
            debugInfo.push({ band, events: bandEvents.length, conflicts: conflictCount });
            
            if (conflictCount < minConflicts) {
                minConflicts = conflictCount;
                bestBand = band;
            }
        }
        
        // Log if all bands have conflicts
        if (minConflicts > 0 && Math.random() < 0.1) {
            console.warn('All bands have conflicts! Choosing least bad option:', {
                bestBand,
                minConflicts,
                eventRange: [eventStart, eventEnd],
                bandStats: debugInfo.slice(0, 5) // Show first 5 bands
            });
        }
        
        return bestBand;
    }

    yearToX(year) {
        if (!isFinite(year)) return 0;
        const viewportLeft = this.viewportCenter - this.viewportSpan / 2;
        const relativeYear = year - viewportLeft;
        const pixelsPerYear = this.canvas.width / window.devicePixelRatio / this.viewportSpan;
        const x = relativeYear * pixelsPerYear;
        return isFinite(x) ? x : 0;
    }

    xToYear(x) {
        const viewportLeft = this.viewportCenter - this.viewportSpan / 2;
        const pixelsPerYear = this.canvas.width / window.devicePixelRatio / this.viewportSpan;
        return viewportLeft + (x / pixelsPerYear);
    }

    getCanvasCoordinates(event) {
        const rect = this.canvas.getBoundingClientRect();
        
        // Canvas logical coordinates match CSS coordinates, so no scaling needed
        return {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top
        };
    }

    updateHover(e) {
        const { x: mouseX, y: mouseY } = this.getCanvasCoordinates(e);

        this.hoveredEvent = null;

        const eventsToCheck = this.filteredEvents || this.events;

        for (const event of eventsToCheck) {
            if (event.visualBounds && event.y !== undefined) {
                // Use the actual visual bounds that were rendered
                const visualHeight = this.bandHeight * 0.7; // Matches drawEventAsBar
                const bandTop = event.y - visualHeight/2;
                const bandBottom = event.y + visualHeight/2;
                
                // Use visual bounds for horizontal detection
                if (mouseX >= event.visualBounds.left && mouseX <= event.visualBounds.right &&
                    mouseY >= bandTop && mouseY <= bandBottom) {
                    this.hoveredEvent = event;
                    break;
                }
            }
        }

        if (this.hoveredEvent) {
            this.tooltip.innerHTML = `
                <div class="event-title">${this.hoveredEvent.title}</div>
                <div class="event-date">${this.hoveredEvent.display_year || this.hoveredEvent.start_year}</div>
                <div class="event-description">${(this.hoveredEvent.description || '').substring(0, 150)}...</div>
                <div class="event-visibility" style="font-size: 10px; color: #4CAF50;">Fully visible</div>
            `;
            const centerX = window.innerWidth / 2;
            const centerY = window.innerHeight / 2;
            const margin = 10;
            this.tooltip.style.visibility = 'hidden';
            this.tooltip.classList.add('visible');
            const rect = this.tooltip.getBoundingClientRect();
            const tooltipW = rect.width || 200;
            const tooltipH = rect.height || 80;
            let left = (e.clientX > centerX) ? (e.clientX - margin - tooltipW) : (e.clientX + margin);
            let top = (e.clientY > centerY) ? (e.clientY - margin - tooltipH) : (e.clientY + margin);
            left = Math.max(4, Math.min(left, window.innerWidth - tooltipW - 4));
            top = Math.max(4, Math.min(top, window.innerHeight - tooltipH - 4));
            this.tooltip.style.left = left + 'px';
            this.tooltip.style.top = top + 'px';
            this.tooltip.style.visibility = 'visible';
        } else {
            this.tooltip.classList.remove('visible');
        }

        this.render();
    }

    applyZoomChange() {
        if (Math.abs(this.zoomAccumulator) < 0.001) {
            this.zoomTimeout = null;
            return;
        }

        const zoomFactor = 1 + this.zoomAccumulator;
        const newSpan = Math.max(this.minSpan, Math.min(this.maxSpan, this.viewportSpan * zoomFactor));

        if (newSpan !== this.viewportSpan) {
            const oldStrategy = this.currentLoadingStrategy;
            this.viewportSpan = newSpan;
            this.determineLoadingStrategy();

            if (oldStrategy !== this.currentLoadingStrategy) {
                this.eventCache.clear();
                this.updateCacheStatus();
            }

            this.loadEventsForViewport();
            this.scheduleRender();
        }

        this.zoomAccumulator = 0;
        this.zoomTimeout = null;
    }

    scheduleRender() {
        if (!this.renderScheduled) {
            this.renderScheduled = true;
            requestAnimationFrame(() => {
                this.render();
                this.renderScheduled = false;
            });
        }
    }

    calculateFractionalYear(year, isBc, month, day) {
        if (year === undefined || year === null || !isFinite(year)) {
            return 0; // Default to year 0 if invalid
        }
        let fractionalYear = year;
        if (month && isFinite(month)) fractionalYear += (month - 1) / 12;
        if (day && isFinite(day)) fractionalYear += day / 365.25;
        if (isBc) fractionalYear = -fractionalYear;
        return fractionalYear;
    }

    animate() {
        this.animationTime += 0.01;
        this.render();
        requestAnimationFrame(() => this.animate());
    }

    render() {
        const w = this.canvas.width / window.devicePixelRatio;
        const h = this.canvas.height / window.devicePixelRatio;

        // Animated gradient background
        const gradient = this.ctx.createLinearGradient(
            0, 0,
            w, h
        );
        const offset = Math.sin(this.animationTime) * 0.1;
        gradient.addColorStop(Math.max(0, Math.min(1, 0 + offset)), '#667eea');
        gradient.addColorStop(0.5, '#764ba2');
        gradient.addColorStop(Math.max(0, Math.min(1, 1 - offset)), '#f093fb');
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, w, h);

        // Draw band backgrounds
        this.drawBands(w, h);

        // Draw events
        this.drawEvents(w, h);

        // Draw axis
        this.drawAxis(w, h);

        this.updateInfoPanel();
    }

    drawBands(w, h) {
        const centerY = h / 2;
        const maxBands = Math.floor(h / this.bandHeight);

        for (let band = 0; band < maxBands; band++) {
            const y = centerY + (band - maxBands/2) * this.bandHeight;
            const bandTop = y - this.bandHeight/2;
            const bandBottom = y + this.bandHeight/2;

            // Band background with subtle gradient
            const bandGradient = this.ctx.createLinearGradient(0, bandTop, 0, bandBottom);
            const alpha = 0.1 + (band % 2) * 0.05; // Alternating opacity
            bandGradient.addColorStop(0, `rgba(255, 255, 255, ${alpha})`);
            bandGradient.addColorStop(1, `rgba(240, 147, 251, ${alpha})`);

            this.ctx.fillStyle = bandGradient;
            this.ctx.fillRect(0, bandTop, w, this.bandHeight);

            // Band separator lines
            this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
            this.ctx.lineWidth = 1;
            this.ctx.beginPath();
            this.ctx.moveTo(0, bandTop);
            this.ctx.lineTo(w, bandTop);
            this.ctx.moveTo(0, bandBottom);
            this.ctx.lineTo(w, bandBottom);
            this.ctx.stroke();
        }
    }

    drawAxis(w, h) {
        const centerY = h / 2;
        const axisY = centerY;
        const tickInterval = this.calculateTickInterval();
        const viewportLeft = this.viewportCenter - this.viewportSpan / 2;
        const viewportRight = this.viewportCenter + this.viewportSpan / 2;

        const firstTick = Math.floor(viewportLeft / tickInterval) * tickInterval;

        // Timeline axis
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
        this.ctx.lineWidth = 3;
        this.ctx.beginPath();
        this.ctx.moveTo(0, axisY);
        this.ctx.lineTo(w, axisY);
        this.ctx.stroke();

        // Ticks and labels
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = 'bold 12px Trebuchet MS';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'top';

        for (let year = firstTick; year <= viewportRight; year += tickInterval) {
            const x = this.yearToX(year);

            // Tick mark
            this.ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            this.ctx.beginPath();
            this.ctx.arc(x, axisY, 6, 0, Math.PI * 2);
            this.ctx.fill();

            // Inner circle
            this.ctx.fillStyle = '#f093fb';
            this.ctx.beginPath();
            this.ctx.arc(x, axisY, 3, 0, Math.PI * 2);
            this.ctx.fill();

            // Label
            const label = year < 0 ? `${Math.abs(year)} BC` : `${year} AD`;
            this.ctx.fillStyle = '#ffffff';
            this.ctx.shadowColor = 'rgba(102, 126, 234, 0.8)';
            this.ctx.shadowBlur = 4;
            this.ctx.fillText(label, x, axisY + 20);
            this.ctx.shadowBlur = 0;
        }
    }

    calculateTickInterval() {
        const intervals = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000];
        const targetTicks = 10;
        const idealInterval = this.viewportSpan / targetTicks;

        return intervals.reduce((prev, curr) =>
            Math.abs(curr - idealInterval) < Math.abs(prev - idealInterval) ? curr : prev
        );
    }

    drawEvents(w, h) {
        const eventsToDraw = this.filteredEvents || this.events;

        for (const event of eventsToDraw) {
            if (event.x === undefined || event.x === null || !isFinite(event.x)) continue;

            const isHovered = this.hoveredEvent === event;
            const renderStyle = this.getEventRenderStyle(event);
            
            switch (renderStyle) {
                case 'dot':
                    this.drawEventAsDot(event, isHovered);
                    break;
                case 'line':
                    this.drawEventAsLine(event, isHovered);
                    break;
                case 'bar':
                default:
                    this.drawEventAsBar(event, isHovered);
                    break;
            }
        }
    }

    getEventRenderStyle(event) {
        // CANDIDATE 5: Force low-precision events to always render as dots
        if (event.precision === 0) {
            return 'dot';
        }

        // Calculate actual visual width at current zoom level
        const startX = this.yearToX(event.startYear);
        const endX = this.yearToX(event.endYear);
        const visualWidth = Math.abs(endX - startX);
        
        // Use visual width to determine rendering style
        if (visualWidth < 8) {
            return 'dot'; // Too narrow to be a meaningful bar
        } else if (visualWidth < 20) {
            return 'line'; // Narrow enough for a line with arrow
        } else {
            return 'bar'; // Wide enough for a full bar
        }
    }

    drawEventAsDot(event, isHovered) {
        this.ctx.fillStyle = event.color;
        this.ctx.strokeStyle = isHovered ? '#ffffff' : event.color;
        this.ctx.lineWidth = isHovered ? 2 : 1;
        
        this.ctx.beginPath();
        this.ctx.arc(event.x, event.y, isHovered ? 6 : 4, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.stroke();
    }

    drawEventAsLine(event, isHovered) {
        // Calculate actual visual width at current zoom level (date-accurate)
        const startX = this.yearToX(event.startYear);
        const endX = this.yearToX(event.endYear);
        const visualWidth = Math.abs(endX - startX);
        
        // Use actual visual width, with minimum for visibility
        const lineLength = Math.max(visualWidth, 8); // Minimum 8px for arrow visibility
        
        this.ctx.strokeStyle = event.color;
        this.ctx.lineWidth = isHovered ? 4 : 2;
        this.ctx.lineCap = 'round';
        
        this.ctx.beginPath();
        this.ctx.moveTo(event.x, event.y);
        this.ctx.lineTo(event.x + lineLength, event.y);
        this.ctx.stroke();
        
        // Add arrowhead for direction (only if line is long enough)
        if (lineLength > 12) {
            this.ctx.beginPath();
            this.ctx.moveTo(event.x + lineLength - 8, event.y - 3);
            this.ctx.lineTo(event.x + lineLength, event.y);
            this.ctx.lineTo(event.x + lineLength - 8, event.y + 3);
            this.ctx.stroke();
        }
    }

    drawEventAsBar(event, isHovered) {
        // Calculate actual visual width at current zoom level
        const startX = this.yearToX(event.startYear);
        const endX = this.yearToX(event.endYear);
        const visualWidth = endX - startX;
        
        // Skip if too narrow to be visible (should be handled by getEventRenderStyle, but safety check)
        if (Math.abs(visualWidth) < 1) return;
        
        const barX = startX;
        const barWidth = visualWidth;

        const bandTop = event.y - this.bandHeight/2;
        const bandBottom = event.y + this.bandHeight/2;
        const eventHeight = this.bandHeight * 0.7;

        // Validate coordinates before creating gradient
        if (!isFinite(barX) || !isFinite(barWidth) || !isFinite(bandTop) || !isFinite(bandBottom)) {
            console.warn('Skipping event due to invalid coordinates:', { barX, barWidth, bandTop, bandBottom, event });
            return;
        }

        // Event rectangle with color - exact width of actual duration
        let eventGradient;
        try {
            eventGradient = this.ctx.createLinearGradient(
                barX, bandTop,
                barX + barWidth, bandBottom
            );
        } catch (e) {
            console.warn('Skipping event due to gradient creation error:', e);
            return;
        }

        if (isHovered) {
            eventGradient.addColorStop(0, this.lightenColor(event.color, 0.3));
            eventGradient.addColorStop(1, this.lightenColor(event.color, 0.1));
        } else {
            eventGradient.addColorStop(0, event.color);
            eventGradient.addColorStop(1, this.darkenColor(event.color, 0.2));
        }

        // Rounded rectangle - exact width of actual duration
        this.ctx.fillStyle = eventGradient;
        this.roundRect(barX, event.y - eventHeight/2, barWidth, eventHeight, 6);
        this.ctx.fill();

        // Border with glow - matches exact bar width
        if (isHovered) {
            this.ctx.shadowColor = event.color;
            this.ctx.shadowBlur = 15;
        }

        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
        this.ctx.lineWidth = isHovered ? 3 : 2;
        this.roundRect(barX, event.y - eventHeight/2, barWidth, eventHeight, 6);
        this.ctx.stroke();
        this.ctx.shadowBlur = 0;

        // Label - positioned within the actual bar width
        if (Math.abs(barWidth) > 40) {
            this.ctx.fillStyle = '#ffffff';
            this.ctx.font = 'bold 11px Trebuchet MS';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.shadowColor = 'rgba(0, 0, 0, 0.7)';
            this.ctx.shadowBlur = 3;

            const text = event.title.length > 12 ? event.title.substring(0, 9) + '...' : event.title;
            this.ctx.fillText(text, barX + barWidth/2, event.y);

            this.ctx.shadowBlur = 0;
        }

        // Duration indicator (small triangle at end) - positioned at actual end
        if (Math.abs(barWidth) > 30) {
            this.ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            this.ctx.beginPath();
            
            // Triangle direction depends on whether we're going forward or backward in time
            if (barWidth > 0) {
                // Forward in time (AD): triangle points right
                this.ctx.moveTo(barX + barWidth, event.y - eventHeight/4);
                this.ctx.lineTo(barX + barWidth + 8, event.y);
                this.ctx.lineTo(barX + barWidth, event.y + eventHeight/4);
            } else {
                // Backward in time (BC): triangle points left
                this.ctx.moveTo(barX + barWidth, event.y - eventHeight/4);
                this.ctx.lineTo(barX + barWidth - 8, event.y);
                this.ctx.lineTo(barX + barWidth, event.y + eventHeight/4);
            }
            this.ctx.closePath();
            this.ctx.fill();
        }

        // Band indicator
        if (event.band > 0) {
            this.ctx.fillStyle = event.color;
            this.ctx.beginPath();
            this.ctx.arc(barX - 6, event.y, 3, 0, Math.PI * 2);
            this.ctx.fill();
        }
    }

    isImportantEvent(event) {
        // For now, consider events important if they have certain keywords in title
        // This is a placeholder for future importance scoring
        const importantKeywords = ['assassination', 'battle', 'war', 'revolution', 'discovery', 'invention', 'treaty', 'coronation', 'death'];
        const title = (event.title || '').toLowerCase();
        return importantKeywords.some(keyword => title.includes(keyword));
    }

    roundRect(x, y, width, height, radius) {
        // Normalize negative widths (for BC events)
        if (width < 0) {
            x = x + width;
            width = -width;
        }
        
        this.ctx.beginPath();
        this.ctx.moveTo(x + radius, y);
        this.ctx.lineTo(x + width - radius, y);
        this.ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
        this.ctx.lineTo(x + width, y + height - radius);
        this.ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
        this.ctx.lineTo(x + radius, y + height);
        this.ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
        this.ctx.lineTo(x, y + radius);
        this.ctx.quadraticCurveTo(x, y, x + radius, y);
        this.ctx.closePath();
    }

    lightenColor(color, percent) {
        // Simple color lightening (assuming hex colors)
        const num = parseInt(color.replace("#", ""), 16);
        const amt = Math.round(2.55 * percent * 100);
        const R = (num >> 16) + amt;
        const G = (num >> 8 & 0x00FF) + amt;
        const B = (num & 0x0000FF) + amt;
        return "#" + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
            (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
            (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
    }

    darkenColor(color, percent) {
        return this.lightenColor(color, -percent);
    }

    updateInfoPanel() {
        document.getElementById('current-position').textContent =
            `${this.viewportCenter < 0 ? Math.abs(this.viewportCenter).toFixed(0) + ' BC' : this.viewportCenter.toFixed(0) + ' AD'}`;
        document.getElementById('zoom-level').textContent =
            `Viewing ${this.viewportSpan.toFixed(0)} years`;
        document.getElementById('band-layers').textContent = this.bandLayers;
    }

    showEventModal(event) {
        const modal = document.getElementById('event-modal');
        const modalTitle = document.getElementById('modal-title');
        const modalBody = document.getElementById('modal-body');

        modalTitle.textContent = event.title || 'Untitled Event';

        const startYear = this.calculateFractionalYear(event.start_year, event.is_bc_start, event.start_month, event.start_day);
        const endYear = this.calculateFractionalYear(event.end_year, event.is_bc_end, event.end_month, event.end_day);
        const duration = Math.abs(endYear - startYear);

        modalBody.innerHTML = `
            <div class="event-detail">
                <span class="event-detail-label">Title:</span>
                <span class="event-detail-value">${event.title || 'Untitled'}</span>
            </div>
            <div class="event-detail">
                <span class="event-detail-label">Date Range:</span>
                <span class="event-detail-value">${this.formatYear(startYear)} to ${this.formatYear(endYear)}</span>
            </div>
            <div class="event-detail">
                <span class="event-detail-label">Duration:</span>
                <span class="event-detail-value">${duration.toFixed(1)} years</span>
            </div>
            <div class="event-detail">
                <span class="event-detail-label">Description:</span>
                <span class="event-detail-value">${event.description || 'No description available'}</span>
            </div>
            <div class="event-detail">
                <span class="event-detail-label">Importance:</span>
                <span class="event-detail-value">${event.importance_score || 'Not specified'}</span>
            </div>
            <div class="event-detail">
                <span class="event-detail-label">Precision:</span>
                <span class="event-detail-value">${event.precision !== undefined ? event.precision.toFixed(3) : 'Not specified'}</span>
            </div>
            <div class="event-detail">
                <span class="event-detail-label">Match Type:</span>
                <span class="event-detail-value">${event.match_type || event.span_match_notes || 'Not available'}</span>
            </div>
            <div class="event-detail">
                <span class="event-detail-label">Extraction Method:</span>
                <span class="event-detail-value">${event.extraction_method || 'Not available'}</span>
            </div>
            <div class="event-detail">
                <span class="event-detail-label">Band:</span>
                <span class="event-detail-value">${event.band || 0}</span>
            </div>
            ${event.categories && event.categories.length > 0 ? `
            <div class="event-detail">
                <span class="event-detail-label">Categories:</span>
                <div class="event-detail-value">
                    ${event.categories.map(cat => `
                        <div class="category-item">
                            <span class="category-name">${cat.category}</span>
                            ${cat.llm_source ? `<span class="category-source ai-source">AI (${cat.llm_source})</span>` : '<span class="category-source wiki-source">Wikipedia</span>'}
                            ${cat.confidence ? `<span class="category-confidence">${(cat.confidence * 100).toFixed(0)}% confidence</span>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}

            <div class="debug-info">
                <h3>Debug Information</h3>
                <div class="debug-code">${JSON.stringify({
                    id: event.id,
                    start_year: event.start_year,
                    end_year: event.end_year,
                    is_bc_start: event.is_bc_start,
                    is_bc_end: event.is_bc_end,
                    start_month: event.start_month,
                    end_month: event.end_month,
                    start_day: event.start_day,
                    end_day: event.end_day,
                    precision: event.precision,
                    extraction_method: event.extraction_method,
                    extract_snippet: event.extract_snippet,
                    span_match_notes: event.span_match_notes,
                    title: event.title,
                    description: event.description,
                    importance_score: event.importance_score,
                    calculatedStartYear: startYear,
                    calculatedEndYear: endYear,
                    duration: duration,
                    x: event.x,
                    y: event.y,
                    width: event.width,
                    band: event.band,
                    color: event.color
                ,
                    match_type: event.match_type || event.span_match_notes
                }, null, 2)}</div>
            </div>
        `;

        modal.style.display = 'block';
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    hideEventModal() {
        const modal = document.getElementById('event-modal');
        modal.style.display = 'none';
        document.body.style.overflow = 'auto'; // Restore scrolling
    }

    formatYear(year) {
        if (year < 0) {
            return `${Math.abs(year).toFixed(0)} BC`;
        } else {
            return `${year.toFixed(0)} AD`;
        }
    }

    // FAB Control Methods
    showFilterPanel() {
        this.categorySearchInput.value = '';
        this.populateCategories();
        this.filterPanel.classList.add('active');
    }

    hideFilterPanel() {
        this.filterPanel.classList.remove('active');
    }

    showSearchPanel() {
        this.searchPanel.classList.add('active');
        this.searchInput.focus();
    }

    hideSearchPanel() {
        this.searchPanel.classList.remove('active');
        this.searchInput.value = '';
        this.searchResults.innerHTML = '';
    }

    populateCategories() {
        // Fetch all categories from the API
        fetch(`${API_URL}/categories`)
            .then(response => response.json())
            .then(data => {
                this.allCategories.clear();
                // Store categories with their metadata
                this.allCategoryData = data.categories || [];
                
                // Extract category names for the Set
                this.allCategoryData.forEach(catData => {
                    this.allCategories.add(catData.category);
                });
                
                this.renderCategoryList();
            })
            .catch(error => {
                console.error('Error fetching categories:', error);
                // Fallback to extracting from events if API fails
                this.allCategories.clear();
                this.events.forEach(event => {
                    if (event.categories) {
                        event.categories.forEach(cat => {
                            this.allCategories.add(cat.category);
                        });
                    }
                });
                this.allCategoryData = Array.from(this.allCategories).map(cat => ({ category: cat, count: 0, has_llm_enrichment: false }));
                this.renderCategoryList();
            });
    }

    renderCategoryList(filteredCategories = null) {
        const categoriesToShow = filteredCategories || this.allCategoryData;
        
        // Sort categories: active ones first, then by count descending
        const sortedCategories = categoriesToShow.sort((a, b) => {
            const aActive = this.activeCategories.has(a.category);
            const bActive = this.activeCategories.has(b.category);
            
            if (aActive && !bActive) return -1;
            if (!aActive && bActive) return 1;
            
            // If both active or both inactive, sort by count descending
            return b.count - a.count;
        });

        const filterContent = document.getElementById('filter-content');
        if (!filterContent) {
            console.error('Could not find filter-content element');
            return;
        }
        filterContent.innerHTML = '';

        if (sortedCategories.length === 0) {
            filterContent.innerHTML = '<p>No categories found</p>';
            return;
        }

        sortedCategories.forEach(catData => {
            const filterItem = document.createElement('div');
            filterItem.className = 'filter-item';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `filter-${catData.category}`;
            checkbox.checked = this.activeCategories.has(catData.category);

            const label = document.createElement('label');
            label.htmlFor = `filter-${catData.category}`;
            
            // Show category name with count and LLM indicator
            const countText = catData.count > 0 ? ` (${catData.count})` : '';
            const llmIndicator = catData.has_llm_enrichment ? ' 🤖' : '';
            label.textContent = catData.category + countText + llmIndicator;

            checkbox.addEventListener('change', () => {
                if (checkbox.checked) {
                    this.activeCategories.add(catData.category);
                } else {
                    this.activeCategories.delete(catData.category);
                }
                this.applyCategoryFilter();
                // Re-render to maintain sorting
                this.renderCategoryList(filteredCategories);
            });

            filterItem.appendChild(checkbox);
            filterItem.appendChild(label);
            filterContent.appendChild(filterItem);
        });
    }

    filterCategories(searchTerm) {
        if (!searchTerm.trim()) {
            // Show all categories when search is empty
            this.renderCategoryList();
            return;
        }

        const filtered = this.allCategoryData.filter(catData =>
            catData.category.toLowerCase().includes(searchTerm.toLowerCase())
        );
        
        this.renderCategoryList(filtered);
    }

    applyCategoryFilter() {
        if (this.activeCategories.size === 0) {
            // Show all events
            this.filteredEvents = this.events;
        } else {
            // Filter events that have at least one matching category
            this.filteredEvents = this.events.filter(event => {
                if (!event.categories) return false;
                return event.categories.some(cat => this.activeCategories.has(cat.category));
            });
        }
        this.scheduleRender();
    }

    performSearch(query) {
        if (!query.trim()) {
            this.searchResults.innerHTML = '';
            return;
        }

        const searchTerm = query.toLowerCase();
        const results = this.events.filter(event => {
            const title = (event.title || '').toLowerCase();
            const description = (event.description || '').toLowerCase();
            return title.includes(searchTerm) || description.includes(searchTerm);
        }).slice(0, 10); // Limit to 10 results

        this.searchResults.innerHTML = '';

        if (results.length === 0) {
            this.searchResults.innerHTML = '<p>No events found</p>';
            return;
        }

        results.forEach(event => {
            const resultItem = document.createElement('div');
            resultItem.className = 'search-result-item';

            const startYear = this.calculateFractionalYear(event.start_year, event.is_bc_start, event.start_month, event.start_day);

            resultItem.innerHTML = `
                <div class="search-result-title">${event.title || 'Untitled'}</div>
                <div class="search-result-date">${this.formatYear(startYear)}</div>
            `;

            resultItem.addEventListener('click', () => {
                // Center on the event
                this.viewportCenter = startYear;
                this.loadEventsForViewport();
                this.scheduleRender();
                this.hideSearchPanel();
            });

            this.searchResults.appendChild(resultItem);
        });
    }
}

new TimelineRenderer();