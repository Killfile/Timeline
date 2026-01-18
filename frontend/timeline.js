/**
 * Timeline Renderer Module
 * 
 * Responsibilities:
 * - D3.js visualization rendering
 * - Zoom and pan interaction handling
 * - Event click handling
 * - SVG drawing and updates
 * 
 * This module is purely focused on rendering. It pulls data from the orchestrator
 * and delegates all other concerns (packing, colors, stats, API) to other modules.
 */

console.log('[Timeline] ========== MODULE LOADED - VERSION 2024-01-05 17:00 ==========');

// Configuration constants
const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`;
const LANE_HEIGHT = 20;
const AXIS_HEIGHT = 50; // Height reserved for X-axis
const MIN_LANES = 10;   // Minimum number of lanes
const CHAR_WIDTH = 8;
const PADDING = 8;
const MAX_LABELS = 50; // Maximum number of labels to show at once
const MIN_LABEL_WIDTH = 20; // Minimum pixel width for a label

// DEBUG: Visual indicator for center viewport events (bins 5-9)
// Set to false to disable black outlines on center events
const DEBUG_SHOW_CENTER_BINS = true;

// D3 selection references
let svg, xScale, xAxis, zoom;
let currentTransform = d3.zoomIdentity;
let initialTransform = d3.zoomIdentity; // Store initial transform for reset zoom
let initialDomain = null; // Store initial domain for reset zoom
let tooltip = null;  // Tooltip for hover preview

// Track last zoom scale factor to detect pan vs zoom
let lastZoomK = 1;

// Track current operation type for label preservation
let currentOperationType = 'ZOOM'; // 'PAN' or 'ZOOM'

// Track label visibility state for center events during pan
let centerEventLabels = new Set(); // Event IDs that have visible labels in center

// Debounce timer for viewport event reloading
let reloadTimer = null;
const RELOAD_DEBOUNCE_MS = 300;

// Debounce timer for window resize
let resizeTimer = null;
const RESIZE_DEBOUNCE_MS = 200;

/**
 * Calculate the number of lanes that fit in the available window space
 * @returns {number} Number of lanes that can fit
 */
function calculateAvailableLanes() {
    const container = document.getElementById('timeline-container');
    if (!container) return MIN_LANES;
    
    // Get the bottom of the container element
    const containerRect = container.getBoundingClientRect();
    
    // Get window height
    const windowHeight = window.innerHeight;
    
    // Calculate available height for timeline (from container top to window bottom, minus some padding)
    const availableHeight = windowHeight - containerRect.top - 20; // 20px padding at bottom
    
    // Calculate how many lanes fit, reserving space for the axis
    const heightForLanes = Math.max(availableHeight - AXIS_HEIGHT, MIN_LANES * LANE_HEIGHT);
    const lanes = Math.max(Math.floor(heightForLanes / LANE_HEIGHT), MIN_LANES);
    
    console.log(`[Timeline] Calculated ${lanes} available lanes (available height: ${availableHeight}px)`);
    
    return lanes;
}

/**
 * Update timeline height and notify orchestrator of lane count change
 */
function updateTimelineHeight() {
    const availableLanes = calculateAvailableLanes();
    const height = availableLanes * LANE_HEIGHT + AXIS_HEIGHT;
    
    // Update container height
    const container = d3.select('#timeline-container');
    container.style('height', `${height}px`);
    
    // Update SVG height if it exists
    if (svg) {
        svg.attr('height', height);
        
        // Update axis position
        svg.select('.x-axis')
            .attr('transform', `translate(0, ${availableLanes * LANE_HEIGHT})`);
    }
    
    // Notify orchestrator of available lanes
    window.timelineOrchestrator.setAvailableLanes(availableLanes);
    
    console.log(`[Timeline] Updated timeline height to ${height}px for ${availableLanes} lanes`);
}

/**
 * Update timeline dimensions (both width and height)
 * Called when entering/exiting fullscreen or on window resize
 */
function updateTimelineDimensions() {
    const container = d3.select('#timeline');
    const width = container.node().clientWidth;
    const availableLanes = calculateAvailableLanes();
    const height = availableLanes * LANE_HEIGHT + AXIS_HEIGHT;
    
    // Update container height
    d3.select('#timeline-container').style('height', `${height}px`);
    
    // Update SVG dimensions if it exists
    if (svg) {
        svg.attr('width', width)
           .attr('height', height);
        
        // Update background rect to capture zoom/pan events
        svg.select('.zoom-capture')
            .attr('width', width)
            .attr('height', height);
        
        // Update axis position
        svg.select('.x-axis')
            .attr('transform', `translate(0, ${availableLanes * LANE_HEIGHT})`);
        
        // Update lane guides
        svg.selectAll('.lane-guides line')
            .attr('x2', width);
        
        // Update x-scale range
        if (xScale) {
            xScale.range([0, width]);
            
            // Re-render axis with updated scale
            const currentScale = currentTransform.rescaleX(xScale);
            xAxis.scale(currentScale);
            svg.select('.x-axis').call(xAxis);
            
            // Update orchestrator scale
            window.timelineOrchestrator.setScale(currentScale);
            
            // Reposition all events
            applyPositions(currentScale);
        }
    }
    
    // Notify orchestrator of available lanes
    window.timelineOrchestrator.setAvailableLanes(availableLanes);
    
    console.log(`[Timeline] Updated timeline dimensions to ${width}x${height}px for ${availableLanes} lanes`);
}

/**
 * Convert event year/BC flag to numeric scale value
 * @param {number} year - The year value from the API (always positive)
 * @param {boolean} isBC - Whether this is a BC date
 * @param {number} month - Optional month (1-12)
 * @param {number} day - Optional day (1-31)
 * @returns {number} Scale year (negative for BC, positive for AD)
 */
function toYearNumber(year, isBc, month = null, day = null) {
    if (year === null || year === undefined) return null;
    let fractionalYear = isBc ? -year : year;
    
    // Add fractional year based on month/day if available
    if (month !== null && month !== undefined) {
        const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        let dayOfYear = 0;
        
        // Add days from previous months
        for (let i = 0; i < month - 1; i++) {
            dayOfYear += daysInMonth[i];
        }
        
        // Add days in current month
        if (day !== null && day !== undefined) {
            dayOfYear += day;
        } else {
            // If no day specified, use middle of month
            dayOfYear += Math.floor(daysInMonth[month - 1] / 2);
        }
        
        const yearFraction = dayOfYear / 365.0;
        fractionalYear += yearFraction;
    }
    
    return fractionalYear;
}

/**
 * Calculate 15-bin boundaries for the timeline.
 * 
 * The 15-bin system divides the timeline into three 5-bin zones:
 * - Left buffer: bins 0-4 (earlier than viewport, for smooth panning left)
 * - Center viewport: bins 5-9 (currently visible)
 * - Right buffer: bins 10-14 (later than viewport, for smooth panning right)
 * 
 * Each bin has width = viewport_span / 5.
 * 
 * @param {number} startYear - Viewport start year (negative for BC)
 * @param {number} endYear - Viewport end year (negative for BC)
 * @returns {Object} Object with structure:
 *   {
 *     viewportCenter: number,
 *     viewportSpan: number,
 *     binWidth: number,
 *     left: { start: number, end: number, bins: [0,1,2,3,4] },
 *     center: { start: number, end: number, bins: [5,6,7,8,9] },
 *     right: { start: number, end: number, bins: [10,11,12,13,14] }
 *   }
 */
function calculate15Bins(startYear, endYear) {
    const viewportSpan = endYear - startYear;
    const viewportCenter = startYear + (viewportSpan / 2);
    const binWidth = viewportSpan / 5;
    
    // Left buffer: extends 1 viewport width before the viewport start
    const leftStart = viewportCenter - (viewportSpan * 1.5);
    const leftEnd = viewportCenter - (viewportSpan * 0.5);
    
    // Center viewport: the currently visible area
    const centerStart = viewportCenter - (viewportSpan * 0.5);
    const centerEnd = viewportCenter + (viewportSpan * 0.5);
    
    // Right buffer: extends 1 viewport width after the viewport end
    const rightStart = viewportCenter + (viewportSpan * 0.5);
    const rightEnd = viewportCenter + (viewportSpan * 1.5);
    
    return {
        viewportCenter,
        viewportSpan,
        binWidth,
        left: {
            start: leftStart,
            end: leftEnd,
            bins: [0, 1, 2, 3, 4]
        },
        center: {
            start: centerStart,
            end: centerEnd,
            bins: [5, 6, 7, 8, 9]
        },
        right: {
            start: rightStart,
            end: rightEnd,
            bins: [10, 11, 12, 13, 14]
        }
    };
}

/**
 * Recalculate bin assignments for all loaded events based on current viewport.
 * This allows immediate visual feedback during pan/zoom without waiting for API reload.
 * 
 * @param {number} startYear - Current viewport start year (negative for BC)
 * @param {number} endYear - Current viewport end year (negative for BC)
 */
function updateEventBinAssignments(startYear, endYear) {
    const events = window.timelineOrchestrator.getEvents();
    if (!events || events.length === 0) return;
    
    // Calculate current 15-bin boundaries
    const binConfig = calculate15Bins(startYear, endYear);
    const binWidth = binConfig.binWidth;
    
    // Update bin_num for each event based on its midpoint
    events.forEach(event => {
        // Calculate event's temporal midpoint
        const eventStart = toYearNumber(event.start_year, event.is_bc_start, event.start_month, event.start_day);
        const eventEnd = event.end_year !== null && event.end_year !== undefined
            ? toYearNumber(event.end_year, event.is_bc_end, event.end_month, event.end_day)
            : eventStart;
        
        if (eventStart === null || eventEnd === null) {
            event.bin_num = null;
            return;
        }
        
        const eventMidpoint = (eventStart + eventEnd) / 2;
        
        // Determine which bin (0-14) contains this midpoint
        // Bins are arranged: [left buffer 0-4][center viewport 5-9][right buffer 10-14]
        const leftStart = binConfig.left.start;
        const rightEnd = binConfig.right.end;
        
        // Check if event is outside the 15-bin range
        if (eventMidpoint < leftStart || eventMidpoint > rightEnd) {
            event.bin_num = null;
            return;
        }
        
        // Calculate which bin (0-14) the midpoint falls into
        const binIndex = Math.floor((eventMidpoint - leftStart) / binWidth);
        event.bin_num = Math.max(0, Math.min(14, binIndex));
    });
    
    // Update visual styling immediately without full re-render
    updateEventStrokes();
}

/**
 * Update stroke styling for all rendered events based on their bin_num.
 * Called after bin assignments change to provide immediate visual feedback.
 */
function updateEventStrokes() {
    if (!DEBUG_SHOW_CENTER_BINS) return;
    
    // Update circle strokes (moment events)
    svg.selectAll('.event-group circle.timeline-event')
        .attr('stroke', d => {
            if (d.bin_num >= 5 && d.bin_num <= 9) {
                return '#000';
            }
            return '#fff';
        })
        .attr('stroke-width', d => {
            if (d.bin_num >= 5 && d.bin_num <= 9) {
                return 3;
            }
            return 2;
        });
    
    // Update rect strokes (span events)
    svg.selectAll('.event-group rect.timeline-span')
        .attr('stroke', d => {
            if (d.bin_num >= 5 && d.bin_num <= 9) {
                return '#000';
            }
            return 'none';
        })
        .attr('stroke-width', d => {
            if (d.bin_num >= 5 && d.bin_num <= 9) {
                return 2;
            }
            return 0;
        });
}

/**
 * Load events for all three zones (left buffer, center viewport, right buffer) in parallel.
 * Uses the 15-bin system to load buffer zones around the viewport.
 * 
 * @param {number} startYear - Viewport start year (negative for BC)
 * @param {number} endYear - Viewport end year (negative for BC)
 * @param {boolean} skipCenter - If true, skip loading center zone (for pan operations)
 * @returns {Promise<Object>} Object with arrays: { left: [], center: [], right: [] }
 */
async function loadThreeZones(startYear, endYear, skipCenter = false) {
    try {
        // Calculate 15-bin boundaries
        const binConfig = calculate15Bins(startYear, endYear);
        
        // Get selected categories from orchestrator
        const selectedCategories = window.timelineOrchestrator.getSelectedCategories();
        const selectedElements = window.timelineOrchestrator.getSelectedElements();
        
        console.log(`[Timeline] ========================================`);
        console.log(`[Timeline] DEBUG: Loading zones`);
        console.log(`[Timeline] DEBUG: skipCenter=${skipCenter}, center=${binConfig.viewportCenter.toFixed(1)}, span=${binConfig.viewportSpan.toFixed(1)}`);
        console.log(`[Timeline] ========================================`);
        
        // Build promises array - conditionally include center
        const promises = [];
        const zoneNames = [];
        
        // Always load left buffer
        promises.push(window.timelineBackend.loadEventsByBins({
            viewportCenter: binConfig.viewportCenter,
            viewportSpan: binConfig.viewportSpan,
            zone: 'left',
            categories: selectedCategories.length > 0 ? selectedCategories : undefined,
            elements: selectedElements.length > 0 ? selectedElements : undefined,
            limit: 100
        }));
        zoneNames.push('left');
        
        // Conditionally load center
        if (!skipCenter) {
            promises.push(window.timelineBackend.loadEventsByBins({
                viewportCenter: binConfig.viewportCenter,
                viewportSpan: binConfig.viewportSpan,
                zone: 'center',
                categories: selectedCategories.length > 0 ? selectedCategories : undefined,
                elements: selectedElements.length > 0 ? selectedElements : undefined,
                limit: 100
            }));
            zoneNames.push('center');
        }
        
        // Always load right buffer
        promises.push(window.timelineBackend.loadEventsByBins({
            viewportCenter: binConfig.viewportCenter,
            viewportSpan: binConfig.viewportSpan,
            zone: 'right',
            categories: selectedCategories.length > 0 ? selectedCategories : undefined,
            elements: selectedElements.length > 0 ? selectedElements : undefined,
            limit: 100
        }));
        zoneNames.push('right');
        
        // Execute all API calls
        const results = await Promise.all(promises);
        
        // Map results back to zone names
        const leftEvents = results[0];
        const centerEvents = skipCenter ? [] : results[1];
        const rightEvents = skipCenter ? results[1] : results[2];
        
        console.log(`[Timeline] ========================================`);
        console.log(`[Timeline] DEBUG: Zone loading results`);
        console.log(`[Timeline] DEBUG: left=${leftEvents.length}, center=${centerEvents.length} (skipped=${skipCenter}), right=${rightEvents.length}`);
        console.log(`[Timeline] ========================================`);
        
        // Combine events
        let allEvents;
        if (skipCenter) {
            // During PAN: Simple 1:1 replacement strategy (like labels)
            // 1. Keep existing placed events
            // 2. Add new buffer events
            const existingEvents = window.timelineOrchestrator.getEvents();
            const existingIds = new Set(existingEvents.map(e => e.id));
            
            // Add new buffer events (from left/right loads) that aren't duplicates
            const newLeftEvents = leftEvents.filter(e => !existingIds.has(e.id));
            const newRightEvents = rightEvents.filter(e => !existingIds.has(e.id));
            
            allEvents = [...existingEvents, ...newLeftEvents, ...newRightEvents];
            
            console.log(`[Timeline] ========================================`);
            console.log(`[Timeline] DEBUG: PAN - Kept ${existingEvents.length} existing events`);
            console.log(`[Timeline] DEBUG: PAN - Added ${newLeftEvents.length} left + ${newRightEvents.length} right buffer events`);
            console.log(`[Timeline] DEBUG: Total events: ${allEvents.length}`);
            console.log(`[Timeline] ========================================`);
        } else {
            // ZOOM: Full reload from all zones
            allEvents = [...leftEvents, ...centerEvents, ...rightEvents];
            console.log(`[Timeline] DEBUG: ZOOM - Full reload: ${allEvents.length} events`);
        }
        
        window.timelineOrchestrator.setEvents(allEvents);
        
        // Update "events in scope" count for the visible viewport (NOT the full buffer)
        // Convert viewport center/span to start/end for the count API
        // Note: viewportCenter is negative for BC, positive for AD
        let viewportStartYear = binConfig.viewportCenter - (binConfig.viewportSpan / 2);
        let viewportEndYear = binConfig.viewportCenter + (binConfig.viewportSpan / 2);
        
        // Ensure start < end
        if (viewportStartYear > viewportEndYear) {
            [viewportStartYear, viewportEndYear] = [viewportEndYear, viewportStartYear];
        }
        
        const countParams = {
            viewportStart: Math.round(Math.abs(viewportStartYear)),
            viewportEnd: Math.round(Math.abs(viewportEndYear)),
            isStartBC: viewportStartYear < 0,
            isEndBC: viewportEndYear < 0,
            categories: selectedCategories.length > 0 ? selectedCategories : undefined,
            elements: selectedElements.length > 0 ? selectedElements : undefined
        };
        
        console.log(`[Timeline] DEBUG: Updating viewport count with params:`, countParams);
        await window.timelineBackend.updateViewportCount(countParams);
        
        return {
            left: leftEvents,
            center: centerEvents,
            right: rightEvents,
            binConfig
        };
        
    } catch (error) {
        console.error('[Timeline] Error loading three zones:', error);
        throw error;
    }
}

/**
 * Reload events for the current viewport with debouncing
 * Uses the 15-bin system to load events in three zones (left buffer, center viewport, right buffer).
 * 
 * @param {number} startYear - Viewport start year (negative for BC)
 * @param {number} endYear - Viewport end year (negative for BC)
 * @param {boolean} isPan - If true, skip center zone reload and repacking (pan operation)
 */
function reloadViewportEvents(startYear, endYear, isPan = false) {
    // Clear existing timer
    if (reloadTimer) {
        clearTimeout(reloadTimer);
    }
    
    // Debounce: wait for user to stop zooming/panning
    reloadTimer = setTimeout(async () => {
        try {
            console.log(`[Timeline] ========================================`);
            console.log(`[Timeline] DEBUG: Reloading viewport events`);
            console.log(`[Timeline] DEBUG: isPan=${isPan}, startYear=${startYear.toFixed(1)}, endYear=${endYear.toFixed(1)}`);
            console.log(`[Timeline] ========================================`);
            
            // Load zones - skip center on pan to preserve viewport events
            await loadThreeZones(startYear, endYear, isPan);
            
            console.log('[Timeline] Successfully loaded zones');
            
            // The packing module will automatically repack using the current transformed scale
            // because loadThreeZones() -> setEvents() triggers the 'events' notification
            // Note: On pan, center events are preserved so they won't be repacked
            
        } catch (error) {
            console.error('[Timeline] Error reloading viewport events:', error);
        }
    }, RELOAD_DEBOUNCE_MS);
}

/**
 * Create a smart tick formatter that adapts to zoom level
 * Returns a function that formats ticks as years, months, or days based on visible range
 * Ensures no duplicate labels by using different detail levels at different zoom levels
 */
function createSmartTickFormatter(scale) {
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    return function(d) {
        const domain = scale.domain();
        const rangeYears = Math.abs(domain[1] - domain[0]);
        
        // Determine detail level based on visible range
        if (rangeYears > 10) {
            // Year-only level (wide zoom)
            const year = Math.round(d);
            // Only show whole years to avoid duplicates
            if (Math.abs(d - year) > 0.05) return '';
            
            if (year < 0) return `${Math.abs(year)} BC`;
            if (year === 0) return '1 BC';
            return `${year} AD`;
            
        } else if (rangeYears > 1) {
            // Year + Month level (medium zoom)
            const year = Math.floor(d);
            const fraction = d - year;
            const monthFloat = fraction * 12;
            const month = Math.round(monthFloat);
            
            // Only show if close to month boundary (avoid duplicates within same month)
            if (Math.abs(monthFloat - month) > 0.15) return '';
            if (month < 0 || month > 11) return '';
            
            const absYear = Math.abs(year);
            const era = year < 0 ? 'BC' : 'AD';
            
            // For wider ranges, show year with month, for narrower just month
            if (rangeYears > 3) {
                return `${monthNames[month]} ${absYear} ${era}`;
            } else {
                // Just show month name to reduce clutter when focused on one year
                return `${monthNames[month]}`;
            }
            
        } else {
            // Day level (narrow zoom)
            const year = Math.floor(d);
            const fraction = d - year;
            const dayOfYear = Math.round(fraction * 365);
            
            // Convert day of year to month and day
            const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
            let month = 0;
            let day = dayOfYear;
            
            for (let i = 0; i < 12; i++) {
                if (day <= daysInMonth[i]) {
                    month = i;
                    break;
                }
                day -= daysInMonth[i];
            }
            
            // Clamp to valid range
            if (month < 0 || month > 11) return '';
            if (day < 1 || day > daysInMonth[month]) return '';
            
            const absYear = Math.abs(year);
            const era = year < 0 ? 'BC' : 'AD';
            
            // For very narrow ranges, just show date without year
            if (rangeYears < 0.3) {
                return `${monthNames[month]} ${day}`;
            } else {
                return `${monthNames[month]} ${day}, ${absYear} ${era}`;
            }
        }
    };
}

/**
 * Initialize the timeline renderer
 * Sets up the SVG container, scales, and event handlers
 */
function initializeTimeline() {
    const container = d3.select('#timeline');
    const width = container.node().clientWidth;
    
    // Calculate initial height based on available space
    const availableLanes = calculateAvailableLanes();
    const height = availableLanes * LANE_HEIGHT + AXIS_HEIGHT;
    
    // Set container height
    d3.select('#timeline-container').style('height', `${height}px`);

    // Create SVG
    svg = container.append('svg')
        .attr('width', width)
        .attr('height', height);

    // Create a background rect to capture zoom/pan events everywhere
    svg.append('rect')
        .attr('class', 'zoom-capture')
        .attr('width', width)
        .attr('height', height)
        .attr('fill', 'transparent')
        .style('pointer-events', 'all');

    // Create axis group (will be updated on zoom)
    const xAxisGroup = svg.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(0, ${availableLanes * LANE_HEIGHT})`);

    // Initialize x-scale as LINEAR (not time scale!)
    // Use numeric years (negative for BC, positive for AD)
    xScale = d3.scaleLinear()
        .domain([-3000, 2024])
        .range([0, width]);

    // Create and render initial axis with smart tick formatting
    xAxis = d3.axisBottom(xScale)
        .ticks(10)
        .tickFormat(createSmartTickFormatter(xScale));
    
    xAxisGroup.call(xAxis);

    // Store scale in orchestrator so packing module can use it
    window.timelineOrchestrator.setScale(xScale);

    // Store initial state for reset zoom functionality
    initialDomain = xScale.domain();
    initialTransform = d3.zoomIdentity;

    // Set initial time range in stats
    const stats = window.timelineOrchestrator.getStats();
    stats.timeRange = {
        start: initialDomain[0],
        end: initialDomain[1]
    };
    window.timelineOrchestrator.updateStats(stats);

    // Setup zoom behavior
    zoom = d3.zoom()
        .scaleExtent([0.5, 200000])
        .on('zoom', handleZoom);

    svg.call(zoom);

    // Draw lane guide lines (fixed, not part of zoom group)
    const laneGuides = svg.append('g')
        .attr('class', 'lane-guides');
    
    for (let i = 0; i <= availableLanes; i++) {
        laneGuides.append('line')
            .attr('x1', 0)
            .attr('x2', width)
            .attr('y1', i * LANE_HEIGHT)
            .attr('y2', i * LANE_HEIGHT)
            .attr('stroke', '#333')
            .attr('stroke-width', i === 0 || i === availableLanes ? 1 : 0.5)
            .attr('opacity', 0.2);
    }

    // Create tooltip for hover preview
    tooltip = d3.select('body')
        .append('div')
        .attr('class', 'timeline-tooltip')
        .style('position', 'absolute')
        .style('visibility', 'hidden')
        .style('background', '#fff')
        .style('color', '#000')
        .style('border', '1px solid #000')
        .style('padding', '8px 12px')
        .style('border-radius', '4px')
        .style('font-size', '12px')
        .style('font-family', 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif')
        .style('pointer-events', 'none')
        .style('z-index', '1001')
        .style('max-width', '300px')
        .style('box-shadow', '0 2px 4px rgba(0,0,0,0.2)');

    // Subscribe to orchestrator state changes
    window.timelineOrchestrator.subscribe('eventsUpdated', render);
    window.timelineOrchestrator.subscribe('laneAssignmentsUpdated', render);
    window.timelineOrchestrator.subscribe('categoryColorsUpdated', render);
    
    // Subscribe to category filter changes
    window.timelineOrchestrator.subscribe('categoriesFilterChanged', (selectedCategories) => {
        console.log('[Timeline] Category filter changed event received!');
        console.log('[Timeline] Selected categories:', selectedCategories);
        console.log('[Timeline] Reloading events for current viewport');
        const currentDomain = currentTransform.rescaleX(xScale).domain();
        reloadViewportEvents(currentDomain[0], currentDomain[1]);
    });
    
    // Subscribe to elements filter changes
    window.timelineOrchestrator.subscribe('elementsFilterChanged', (selectedElements) => {
        console.log('[Timeline] Elements filter changed event received!');
        console.log('[Timeline] Selected elements:', selectedElements);
        console.log('[Timeline] Reloading events for current viewport');
        const currentDomain = currentTransform.rescaleX(xScale).domain();
        reloadViewportEvents(currentDomain[0], currentDomain[1]);
    });

    // Notify orchestrator of initial available lanes
    window.timelineOrchestrator.setAvailableLanes(availableLanes);
    
    // Set up window resize handler with debouncing
    window.addEventListener('resize', () => {
        if (resizeTimer) {
            clearTimeout(resizeTimer);
        }
        resizeTimer = setTimeout(() => {
            updateTimelineDimensions();
            // Trigger repack after dimension change
            const currentEvents = window.timelineOrchestrator.getEvents();
            const currentScale = window.timelineOrchestrator.getScale();
            if (currentEvents.length > 0 && currentScale) {
                window.timelinePacking.repackWithScale(currentScale);
            }
        }, RESIZE_DEBOUNCE_MS);
    });

    // Initial render
    render();
}

/**
 * Reset zoom to initial view
 */
function resetZoom() {
    if (!svg || !zoom || !initialTransform) {
        console.warn('[Timeline] Cannot reset zoom - components not initialized');
        return;
    }
    
    // Apply the initial transform (this triggers handleZoom)
    svg.transition()
        .duration(750)
        .call(zoom.transform, initialTransform);
}

/**
 * Toggle fullscreen mode
 */
function toggleFullscreen() {
    const container = document.getElementById('timeline-container');
    if (!container) {
        console.warn('[Timeline] Cannot toggle fullscreen - container not found');
        return;
    }
    
    if (!document.fullscreenElement) {
        // Enter fullscreen
        container.requestFullscreen().catch(err => {
            console.error('[Timeline] Error entering fullscreen:', err);
        });
    } else {
        // Exit fullscreen
        document.exitFullscreen();
    }
}

/**
 * Handle fullscreen changes - recalculate lanes when entering/exiting
 */
function handleFullscreenChange() {
    const container = document.getElementById('timeline-container');
    if (!container) return;
    
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    
    if (document.fullscreenElement) {
        // Entered fullscreen
        console.log('[Timeline] Entered fullscreen mode');
        if (fullscreenBtn) {
            fullscreenBtn.textContent = '⛶'; // Could change icon if desired
            fullscreenBtn.title = 'Exit Fullscreen';
        }
    } else {
        // Exited fullscreen
        console.log('[Timeline] Exited fullscreen mode');
        if (fullscreenBtn) {
            fullscreenBtn.textContent = '⛶';
            fullscreenBtn.title = 'Toggle Fullscreen';
        }
    }
    
    // Recalculate both width and height for fullscreen mode
    updateTimelineDimensions();
    
    // Trigger repack with current events
    const currentEvents = window.timelineOrchestrator.getEvents();
    const currentScale = window.timelineOrchestrator.getScale();
    if (currentEvents.length > 0 && currentScale) {
        console.log('[Timeline] Repacking events after fullscreen change');
        window.timelinePacking.repackWithScale(currentScale);
    }
}

/**
 * Handle zoom/pan interactions
``` * Updates the viewport state and triggers lane recalculation
 */
function handleZoom(event) {
    currentTransform = event.transform;
    
    // Detect if this is a pan (scale unchanged) or zoom (scale changed)
    const currentZoomK = event.transform.k;
    const isPan = Math.abs(currentZoomK - lastZoomK) < 0.0001;
    const operationType = isPan ? 'PAN' : 'ZOOM';
    
    console.log(`[Timeline] ========================================`);
    console.debug(`[Timeline] DEBUG: ${operationType} operation detected`);
    console.log(`[Timeline] DEBUG: ${operationType} operation detected`);
    console.log(`[Timeline] DEBUG: Current k=${currentZoomK.toFixed(4)}, Last k=${lastZoomK.toFixed(4)}, Diff=${Math.abs(currentZoomK - lastZoomK).toFixed(6)}`);
    console.log(`[Timeline] ========================================`);
    
    // Update last zoom level for next comparison
    lastZoomK = currentZoomK;
    
    // Set global operation type for label preservation
    currentOperationType = operationType;
    
    // Rescale the X axis with the new transform
    const newXScale = event.transform.rescaleX(xScale);
    
    // Update axis with smart formatting based on new zoom level
    xAxis.scale(newXScale).tickFormat(createSmartTickFormatter(newXScale));
    svg.select('.x-axis').call(xAxis);

    // Calculate new time range
    const newDomain = newXScale.domain();
    
    // Update time range in stats
    const stats = window.timelineOrchestrator.getStats();
    stats.timeRange = { 
        start: Math.round(newDomain[0]), 
        end: Math.round(newDomain[1]) 
    };
    window.timelineOrchestrator.updateStats(stats);
    
    // Update viewport state
    window.timelineOrchestrator.setState({
        viewport: {
            startDate: newDomain[0],
            endDate: newDomain[1],
            transform: currentTransform
        }
    });
    
    // Update the scale in orchestrator so packing uses the transformed scale
    window.timelineOrchestrator.setScale(newXScale);

    // Reapply positions to all event groups using the new scale
    applyPositions(newXScale);
    
    // Update bin assignments ONLY during ZOOM, not during PAN
    // During PAN: Events keep their spatial zones (left/center/right) from when they were loaded
    // During ZOOM: Recalculate bins for all events based on new viewport
    if (!isPan) {
        console.log('[Timeline] ZOOM - Updating bin assignments for all events');
        updateEventBinAssignments(newDomain[0], newDomain[1]);
    } else {
        console.log('[Timeline] PAN - Skipping bin assignment update (preserving spatial zones)');
    }

    // Reload events for the new viewport using 15-bin system (debounced)
    // On PAN: skip center zone reload and repacking
    // On ZOOM: reload all zones and repack everything
    reloadViewportEvents(newDomain[0], newDomain[1], isPan);
}

/**
 * Check if event has a span (not just a moment)
 */
function hasSpan(d) {
    return d.end_year !== null && d.end_year !== undefined;
}

/**
 * Apply positions to event groups based on scale
 * This is called on initial render and on every zoom/pan
 */
function applyPositions(scale) {
    const groups = svg.selectAll('.event-group');
    
    // First pass: collect all events with their widths, weights, and positions
    const eventWidths = [];
    groups.each(function(d) {
        const startYear = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
        let endYear = toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day);
        
        // For single-day events, add 1 day (1/365 year) to span the full day
        if (d.start_year === d.end_year && 
            d.start_month === d.end_month && 
            d.start_day === d.end_day && 
            d.start_day !== null) {
            endYear += 1/365.0;
        }
        
        const sx = startYear !== null ? scale(startYear) : 0;
        const ex = endYear !== null ? scale(endYear) : sx;
        const width = Math.abs(ex - sx);
        const centerX = (sx + ex) / 2; // Calculate center position for sorting
        
        // Check visibility: on-screen AND in near buffer zones (about to enter screen)
        // Use 50% of screen width buffer on each side so labels appear well before events are visible
        const bufferMargin = window.innerWidth * 0.5;
        const isVisibleOnScreen = centerX >= 0 && centerX <= window.innerWidth;
        const isNearScreen = centerX >= -bufferMargin && centerX <= window.innerWidth + bufferMargin;
        
        eventWidths.push({
            id: d.id,
            width: width,
            weight: d.weight || 0,
            hasSpan: hasSpan(d),
            centerX: centerX,
            bin: d.bin_num,
            isVisibleOnScreen: isVisibleOnScreen,
            isNearScreen: isNearScreen
        });
    });
    
    // Filter to events wide enough for labels and sort by position (left to right)
    const labelCandidates = eventWidths
        .filter(e => e.hasSpan && e.width > MIN_LABEL_WIDTH)
        .sort((a, b) => a.centerX - b.centerX); // Sort by position left to right
    
    const totalLabelable = labelCandidates.length;
    
    let shouldShowLabel;
    
    // During PAN: Replace labels that left the screen with labels entering from buffer
    if (currentOperationType === 'PAN') {
        // Step 1: Identify which cached labels are now off-screen (left the visible area)
        const visibleEventIds = new Set(labelCandidates.filter(e => e.isVisibleOnScreen).map(e => e.id));
        const labelsNowOffScreen = [];
        for (const eventId of centerEventLabels) {
            if (!visibleEventIds.has(eventId)) {
                labelsNowOffScreen.push(eventId);
            }
        }
        
        console.log(`[Timeline] DEBUG: PAN - ${labelsNowOffScreen.length} labels moved off-screen`);
        
        // Step 2: Keep only labels still on screen
        shouldShowLabel = new Set();
        for (const eventId of centerEventLabels) {
            if (visibleEventIds.has(eventId)) {
                shouldShowLabel.add(eventId);
            }
        }
        
        // Step 3: Find candidates in buffer zones (off-screen) that need labels
        const bufferCandidates = labelCandidates.filter(e => {
            // Events in buffer (off-screen) that don't have labels yet
            return !e.isVisibleOnScreen && !centerEventLabels.has(e.id);
        });
        
        // Sort by distance from screen edges (closest first)
        bufferCandidates.sort((a, b) => {
            const distA = a.centerX < 0 ? Math.abs(a.centerX) : Math.abs(a.centerX - window.innerWidth);
            const distB = b.centerX < 0 ? Math.abs(b.centerX) : Math.abs(b.centerX - window.innerWidth);
            return distA - distB;
        });
        
        console.log(`[Timeline] DEBUG: PAN - Found ${bufferCandidates.length} buffer candidates for labeling`);
        
        // Step 4: Add labels to buffer events to replace ones that left
        const labelsToAdd = Math.min(labelsNowOffScreen.length, bufferCandidates.length, MAX_LABELS - shouldShowLabel.size);
        console.log(`[Timeline] DEBUG: PAN - Adding ${labelsToAdd} labels to buffer events (replacing off-screen labels)`);
        
        for (let i = 0; i < labelsToAdd; i++) {
            const eventId = bufferCandidates[i].id;
            shouldShowLabel.add(eventId);
            centerEventLabels.add(eventId);
        }
        
        // Step 5: Remove off-screen labels from cache
        for (const eventId of labelsNowOffScreen) {
            centerEventLabels.delete(eventId);
        }
        
        console.log(`[Timeline] DEBUG: PAN - Using ${shouldShowLabel.size} total labels (${centerEventLabels.size} in cache)`);
    } else {
        // During ZOOM: Calculate labels fresh
        let selectedLabels = [];
        if (totalLabelable <= MAX_LABELS) {
            // If we have fewer candidates than max labels, show them all
            selectedLabels = labelCandidates.map(e => e.id);
        } else {
            // Select every Nth event to distribute evenly across the timeline
            const interval = totalLabelable / MAX_LABELS;
            for (let i = 0; i < MAX_LABELS; i++) {
                const index = Math.floor(i * interval);
                if (index < labelCandidates.length) {
                    selectedLabels.push(labelCandidates[index].id);
                }
            }
        }
        
        shouldShowLabel = new Set(selectedLabels);
        
        // Save on-screen labels for next pan
        centerEventLabels.clear();
        const selectedEventSet = new Set(selectedLabels);
        eventWidths.forEach(e => {
            if (e.isVisibleOnScreen && selectedEventSet.has(e.id)) {
                centerEventLabels.add(e.id);
            }
        });
        console.log(`[Timeline] DEBUG: ZOOM - Calculated labels and cached ${centerEventLabels.size} on-screen event labels`);
    }
    
    console.log(`[Timeline] Label selection: ${totalLabelable} candidates, showing ${shouldShowLabel.size} labels (interval: ${totalLabelable > MAX_LABELS ? (totalLabelable / MAX_LABELS).toFixed(2) : 'all'})`);
    
    // Position each group
    groups.attr('transform', d => {
        const lane = window.timelineOrchestrator.getLaneForEvent(d.id);
        if (lane === undefined) return 'translate(0, 0)';
        
        const y = lane * LANE_HEIGHT + LANE_HEIGHT / 2;
        
        if (hasSpan(d)) {
            // Span events: group at (0, y), bar positioned within
            return `translate(0, ${y})`;
        } else {
            // Moment events: group at (x, y), dot at (0, 0)
            const startYear = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
            const x = startYear !== null ? scale(startYear) : 0;
            return `translate(${x}, ${y})`;
        }
    });

    // Update span bars (only for span events)
    groups.select('rect.timeline-span')
        .attr('x', d => {
            if (!hasSpan(d)) return 0;
            const startYear = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
            const endYear = toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day);
            const sx = startYear !== null ? scale(startYear) : 0;
            const ex = endYear !== null ? scale(endYear) : sx;
            return Math.min(sx, ex);
        })
        .attr('width', d => {
            if (!hasSpan(d)) return 0;
            const startYear = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
            let endYear = toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day);
            
            // For single-day events, add 1 day (1/365 year) to span the full day
            if (d.start_year === d.end_year && 
                d.start_month === d.end_month && 
                d.start_day === d.end_day && 
                d.start_day !== null) {
                endYear += 1/365.0;
            }
            
            const sx = startYear !== null ? scale(startYear) : 0;
            const ex = endYear !== null ? scale(endYear) : sx;
            return Math.max(3, Math.abs(ex - sx));
        });

    // Update labels for span events
    groups.select('text.event-label')
        .attr('x', d => {
            if (!hasSpan(d)) return 0; // Moment events: label at group center
            const startYear = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
            const endYear = toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day);
            const sx = startYear !== null ? scale(startYear) : 0;
            const ex = endYear !== null ? scale(endYear) : sx;
            return (sx + ex) / 2; // Span events: label at bar center
        })
        .attr('visibility', d => {
            // Always show labels for moment events
            if (!hasSpan(d)) return 'visible';
            
            // For span events, check if wide enough AND in top MAX_LABELS by weight
            const startYear = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
            const endYear = toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day);
            const sx = startYear !== null ? scale(startYear) : 0;
            const ex = endYear !== null ? scale(endYear) : sx;
            const width = Math.abs(ex - sx);
            
            if (width <= MIN_LABEL_WIDTH) return 'hidden';
            
            // Check if this event made the cut for labels
            return shouldShowLabel.has(d.id) ? 'visible' : 'hidden';
        });
}

/**
 * Main render function
 * Draws events on the timeline using current state from orchestrator
 */
function render() {
    const state = window.timelineOrchestrator.getState();
    const { events, laneAssignments, categoryColors } = state;

    console.log(`[Timeline] render() called - events: ${events?.length}, laneAssignments: ${laneAssignments?.size}, colors: ${categoryColors?.size}`);

    if (!events || !laneAssignments || !categoryColors) {
        console.warn('[Timeline] Render skipped - missing data');
        return; // Not ready to render yet
    }

    // Use the current transformed scale for filtering
    const currentScale = currentTransform.rescaleX(xScale);
    const [viewportStart, viewportEnd] = currentScale.domain();

    // During PAN: Keep ALL currently rendered events to avoid DOM churn
    // During ZOOM: Filter to only visible events (normal behavior)
    let eventData;
    if (currentOperationType === 'PAN') {
        // Keep all events that have lane assignments - no viewport filtering
        eventData = events.filter(event => laneAssignments.has(event.id));
        console.log(`[Timeline] DEBUG: PAN - Keeping all ${eventData.length} placed events (no viewport filter)`);
    } else {
        // Normal zoom behavior: filter to viewport
        eventData = events
            .filter(event => {
                // Check if event overlaps with viewport
                const startYear = toYearNumber(event.start_year, event.is_bc_start, event.start_month, event.start_day);
                const endYear = toYearNumber(event.end_year, event.is_bc_end, event.end_month, event.end_day);
                if (startYear === null) return false;
                const eventEndYear = endYear !== null ? endYear : startYear;
                return eventEndYear >= viewportStart && startYear <= viewportEnd;
            })
            .filter(event => laneAssignments.has(event.id)); // Only render placed events
        console.log(`[Timeline] DEBUG: ZOOM - Filtered to ${eventData.length} events in viewport (${Math.round(viewportStart)} to ${Math.round(viewportEnd)})`);
    }

    console.log(`[Timeline] After filtering: ${eventData.length} events to render (viewport: ${Math.round(viewportStart)} to ${Math.round(viewportEnd)})`);

    // Bind data to event groups
    const eventGroups = svg.selectAll('.event-group')
        .data(eventData, d => d.id);

    // Exit (remove old events)
    const exitingEvents = eventGroups.exit();
    if (exitingEvents.size() > 0) {
        const exitingIds = [];
        exitingEvents.each(d => exitingIds.push(d.id));
        console.log(`[Timeline] DEBUG: Removing ${exitingEvents.size()} events:`, exitingIds.slice(0, 5));
        exitingEvents.remove();
    }

    // Enter (create new events)
    const groupsEnter = eventGroups.enter()
        .append('g')
        .attr('class', 'event-group')
        .style('cursor', 'pointer')
        .on('click', handleEventClick)
        .on('mouseover', handleEventMouseOver)
        .on('mousemove', handleEventMouseMove)
        .on('mouseout', handleEventMouseOut);
    
    if (groupsEnter.size() > 0) {
        console.log(`[Timeline] DEBUG: Adding ${groupsEnter.size()} new events`);
    }

    // Span bar (for events with duration)
    groupsEnter.append('rect')
        .attr('class', 'timeline-span')
        .attr('y', -4)
        .attr('height', 8)
        .attr('rx', 4)
        .attr('ry', 4);

    // Moment dot (for point-in-time events)
    groupsEnter.append('circle')
        .attr('class', 'timeline-event')
        .attr('r', 6)
        .attr('stroke', '#fff')
        .attr('stroke-width', 2);

    // Labels
    groupsEnter.append('text')
        .attr('class', 'event-label')
        .attr('text-anchor', 'middle')
        .attr('dy', -12)
        .style('font-size', '12px')
        .style('font-weight', 'bold')
        .style('font-family', 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif')
        .style('fill', '#000');

    // Merge enter + update
    const groupsMerged = eventGroups.merge(groupsEnter);

    // Update colors and visibility
    // Use LLM category first (AI-enriched), fallback to Wikipedia category, then legacy category field
    groupsMerged.select('circle.timeline-event')
        .attr('fill', d => {
            // Try LLM category first (prioritize AI enrichment)
            const llmCat = d.categories?.find(c => c.llm_source);
            if (llmCat) return categoryColors.get(llmCat.category) || '#999';
            
            // Fallback to Wikipedia category
            const wikiCat = d.categories?.find(c => !c.llm_source);
            if (wikiCat) return categoryColors.get(wikiCat.category) || '#999';
            
            // Final fallback to legacy category field
            return categoryColors.get(d.category) || '#999';
        })
        .style('opacity', d => hasSpan(d) ? 0 : 0.85) // Hide dots for span events
        .attr('stroke', d => {
            // DEBUG: Black outline for center viewport events (bins 5-9)
            if (DEBUG_SHOW_CENTER_BINS && d.bin_num >= 5 && d.bin_num <= 9) {
                return '#000';
            }
            return '#fff';
        })
        .attr('stroke-width', d => {
            // DEBUG: Thicker stroke for center viewport events
            if (DEBUG_SHOW_CENTER_BINS && d.bin_num >= 5 && d.bin_num <= 9) {
                return 3;
            }
            return 2;
        });

    groupsMerged.select('rect.timeline-span')
        .attr('fill', d => {
            // Try LLM category first (prioritize AI enrichment)
            const llmCat = d.categories?.find(c => c.llm_source);
            if (llmCat) return categoryColors.get(llmCat.category) || '#999';
            
            // Fallback to Wikipedia category
            const wikiCat = d.categories?.find(c => !c.llm_source);
            if (wikiCat) return categoryColors.get(wikiCat.category) || '#999';
            
            // Final fallback to legacy category field
            return categoryColors.get(d.category) || '#999';
        })
        .style('opacity', d => hasSpan(d) ? 0.75 : 0) // Hide bars for moment events
        .attr('stroke', d => {
            // DEBUG: Black outline for center viewport events (bins 5-9)
            if (DEBUG_SHOW_CENTER_BINS && d.bin_num >= 5 && d.bin_num <= 9) {
                return '#000';
            }
            return 'none';
        })
        .attr('stroke-width', d => {
            // DEBUG: Stroke width for center viewport events
            if (DEBUG_SHOW_CENTER_BINS && d.bin_num >= 5 && d.bin_num <= 9) {
                return 2;
            }
            return 0;
        });

    // Update text content
    groupsMerged.select('text.event-label')
        .text(d => {
            const title = d.title || d.name || '';
            const maxLength = 50;
            if (title.length > maxLength) {
                return title.substring(0, maxLength) + '...';
            }
            return title;
        });

    // Apply positions using current transform
    applyPositions(currentScale);

    // Update eventsPlaced stat (events actually rendered)
    // Note: eventsInScope is updated by backend when loading viewport events
    const currentStats = window.timelineOrchestrator.getStats();
    window.timelineOrchestrator.updateStats({
        ...currentStats,
        loadedEvents: events.length,      // Total events loaded from API
        eventsPlaced: eventData.length    // Events actually rendered (after filtering)
    });
}

/**
 * Handle mouse over event - show tooltip
 */
function handleEventMouseOver(event, d) {
    if (!tooltip) return;
    
    const title = d.title || d.name || 'Untitled Event';
    const maxLength = 100;
    const displayTitle = title.length > maxLength 
        ? title.substring(0, maxLength) + '...' 
        : title;
    
    // Format time period
    const startYear = d.is_bc_start 
        ? `${d.start_year} BC` 
        : `${d.start_year} AD`;
    const endYear = d.end_year 
        ? (d.is_bc_end ? `${d.end_year} BC` : `${d.end_year} AD`)
        : null;
    const periodText = endYear ? `${startYear} - ${endYear}` : startYear;
    
    tooltip
        .html(`<strong>${displayTitle}</strong><br/><span style="font-size: 11px; color: #666;">${periodText}</span>`)
        .style('visibility', 'visible');
}

/**
 * Handle mouse move - update tooltip position
 */
function handleEventMouseMove(event) {
    if (!tooltip) return;
    
    tooltip
        .style('top', (event.pageY + 15) + 'px')
        .style('left', (event.pageX + 15) + 'px');
}

/**
 * Handle mouse out - hide tooltip
 */
function handleEventMouseOut() {
    if (!tooltip) return;
    
    tooltip.style('visibility', 'hidden');
}

/**
 * Handle event click
 * Shows event details in the modal with full debugging info
 */
function handleEventClick(event, d) {
    console.log('[Timeline] Event clicked:', d);
    
    // Get the modal elements
    const modal = document.getElementById('event-details');
    const title = document.getElementById('event-title');
    const period = document.getElementById('event-period');
    const category = document.getElementById('event-category');
    const strategy = document.getElementById('event-strategy');
    const description = document.getElementById('event-description');
    const wikipediaLink = document.getElementById('event-wikipedia-link');
    
    // Format the time period
    const startYear = d.is_bc_start 
        ? `${d.start_year} BC` 
        : `${d.start_year} AD`;
    const endYear = d.end_year 
        ? (d.is_bc_end ? `${d.end_year} BC` : `${d.end_year} AD`)
        : null;
    const periodText = endYear ? `${startYear} to ${endYear}` : startYear;
    
    // Get placement data
    const lane = window.timelineOrchestrator.getLaneForEvent(d.id);
    const currentScale = window.timelineOrchestrator.getScale();
    const startYearNum = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
    const endYearNum = toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day);
    const pixelX = currentScale ? currentScale(startYearNum) : 'N/A';
    const pixelWidth = (currentScale && endYearNum) 
        ? Math.abs(currentScale(endYearNum) - currentScale(startYearNum))
        : 'N/A';
    
    // Populate basic info
    title.textContent = d.title || d.name || 'Untitled Event';
    period.textContent = periodText;
    
    // Format categories display
    const wikipediaCategories = d.categories?.filter(c => !c.llm_source) || [];
    const llmCategories = d.categories?.filter(c => c.llm_source) || [];
    
    let categoryDisplay = '';
    if (wikipediaCategories.length > 0) {
        categoryDisplay = wikipediaCategories.map(c => c.category).join(', ');
    } else if (llmCategories.length > 0) {
        // Use LLM category if no Wikipedia category
        categoryDisplay = llmCategories[0].category + ' (AI)';
    } else if (d.category) {
        // Fallback to legacy category field
        categoryDisplay = d.category;
    } else {
        categoryDisplay = 'Uncategorized';
    }
    
    category.textContent = categoryDisplay;
    
    // Set strategy
    strategy.textContent = d.strategy || 'Unknown';
    
    // Create detailed description with full text and placement data
    description.innerHTML = `
        <div style="margin-bottom: 1em;">
            <strong>Full Text:</strong><br/>
            ${d.text || d.description || 'No description available'}
        </div>
        
        <details open style="margin-bottom: 1em; padding: 0.5em; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px;">
            <summary style="cursor: pointer; font-weight: bold; margin-bottom: 0.5em; color: #333;">Categories & Enrichment</summary>
            ${wikipediaCategories.length > 0 ? `
                <div style="margin-bottom: 1em;">
                    <strong style="color: #1a73e8;">📚 Wikipedia Categories:</strong><br/>
                    <div style="margin-top: 0.5em;">
                        ${wikipediaCategories.map(cat => 
                            `<span style="display: inline-block; background: #e8f0fe; color: #1a73e8; padding: 4px 8px; margin: 2px; border-radius: 4px; font-size: 12px;">${cat.category}</span>`
                        ).join('')}
                    </div>
                </div>
            ` : ''}
            ${llmCategories.length > 0 ? `
                <div style="margin-bottom: 0.5em;">
                    <strong style="color: #ea4335;">🤖 AI-Assigned Categories:</strong><br/>
                    <div style="margin-top: 0.5em;">
                        ${llmCategories.map(cat => 
                            `<div style="display: inline-block; background: #fce8e6; border: 1px solid #ea4335; padding: 6px 10px; margin: 2px; border-radius: 4px; font-size: 12px;">
                                <strong>${cat.category}</strong><br/>
                                <span style="font-size: 10px; color: #666;">
                                    Model: ${cat.llm_source || 'Unknown'} | 
                                    Confidence: ${cat.confidence ? (cat.confidence * 100).toFixed(1) + '%' : 'N/A'}
                                </span>
                            </div>`
                        ).join('')}
                    </div>
                </div>
            ` : ''}
            ${wikipediaCategories.length === 0 && llmCategories.length === 0 ? `
                <em style="color: #666;">No categories assigned</em>
            ` : ''}
        </details>
        
        <details open style="margin-bottom: 1em; padding: 0.5em; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px;">
            <summary style="cursor: pointer; font-weight: bold; margin-bottom: 0.5em; color: #333;">Placement Data</summary>
            <dl style="margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 0.25em 1em;">
                <dt style="font-weight: bold;">Event ID:</dt>
                <dd style="margin: 0;">${d.id}</dd>
                
                <dt style="font-weight: bold;">Lane:</dt>
                <dd style="margin: 0;">${lane !== undefined ? lane : 'Not placed'}</dd>
                
                <dt style="font-weight: bold;">Pixel X:</dt>
                <dd style="margin: 0;">${typeof pixelX === 'number' ? Math.round(pixelX) : pixelX}</dd>
                
                <dt style="font-weight: bold;">Pixel Width:</dt>
                <dd style="margin: 0;">${typeof pixelWidth === 'number' ? Math.round(pixelWidth) : pixelWidth}</dd>
                
                <dt style="font-weight: bold;">Has Span:</dt>
                <dd style="margin: 0;">${hasSpan(d) ? 'Yes' : 'No (moment event)'}</dd>
            </dl>
        </details>
        
        <details style="margin-bottom: 1em; padding: 0.5em; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px;">
            <summary style="cursor: pointer; font-weight: bold; margin-bottom: 0.5em; color: #333;">Date Details</summary>
            <dl style="margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 0.25em 1em;">
                <dt style="font-weight: bold;">Start Year:</dt>
                <dd style="margin: 0;">${d.start_year} ${d.is_bc_start ? 'BC' : 'AD'}</dd>
                
                <dt style="font-weight: bold;">Start Month:</dt>
                <dd style="margin: 0;">${d.start_month || 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Start Day:</dt>
                <dd style="margin: 0;">${d.start_day || 'N/A'}</dd>
                
                <dt style="font-weight: bold;">End Year:</dt>
                <dd style="margin: 0;">${d.end_year ? `${d.end_year} ${d.is_bc_end ? 'BC' : 'AD'}` : 'N/A'}</dd>
                
                <dt style="font-weight: bold;">End Month:</dt>
                <dd style="margin: 0;">${d.end_month || 'N/A'}</dd>
                
                <dt style="font-weight: bold;">End Day:</dt>
                <dd style="margin: 0;">${d.end_day || 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Numeric Start:</dt>
                <dd style="margin: 0;">${startYearNum !== null ? startYearNum.toFixed(3) : 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Numeric End:</dt>
                <dd style="margin: 0;">${endYearNum !== null ? endYearNum.toFixed(3) : 'N/A'}</dd>
            </dl>
        </details>
        
        <details style="margin-bottom: 1em; padding: 0.5em; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px;">
            <summary style="cursor: pointer; font-weight: bold; margin-bottom: 0.5em; color: #333;">Source Data</summary>
            <dl style="margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 0.25em 1em;">
                <dt style="font-weight: bold;">Strategy:</dt>
                <dd style="margin: 0;">${d.strategy || 'Unknown'}</dd>
                
                <dt style="font-weight: bold;">Wikipedia URL:</dt>
                <dd style="margin: 0; word-break: break-all;"><a href="${d.wikipedia_url || '#'}" target="_blank" style="color: #667eea;">${d.wikipedia_url || 'N/A'}</a></dd>
                
                <dt style="font-weight: bold;">Weight (days):</dt>
                <dd style="margin: 0;">${d.weight !== null && d.weight !== undefined ? d.weight : 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Precision:</dt>
                <dd style="margin: 0;">${d.precision !== null && d.precision !== undefined ? d.precision : 'N/A'}</dd>
            </dl>
        </details>
        
        <details id="extraction-debug-section" style="margin-bottom: 1em; padding: 0.5em; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px;">
            <summary style="cursor: pointer; font-weight: bold; margin-bottom: 0.5em; color: #333;">Extraction Debug Info</summary>
            <div id="extraction-debug-content" style="margin-top: 0.5em;">
                <em style="color: #666;">Loading...</em>
            </div>
        </details>
    `;
    
    // Set Wikipedia link
    if (d.wikipedia_url) {
        wikipediaLink.href = d.wikipedia_url;
        wikipediaLink.style.display = 'block';
    } else {
        wikipediaLink.style.display = 'none';
    }
    
    // Show the modal
    modal.classList.remove('hidden');
    
    // Fetch extraction debug information asynchronously
    fetchExtractionDebug(d.id);
}

/**
 * Fetch extraction debug information for an event
 */
async function fetchExtractionDebug(eventId) {
    const debugContent = document.getElementById('extraction-debug-content');
    if (!debugContent) return;
    
    try {
        const debug = await window.timelineBackend.getExtractionDebug(eventId);
        
        // Display debug information
        debugContent.innerHTML = `
            <dl style="margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 0.25em 1em; font-size: 11px;">
                <dt style="font-weight: bold;">Extraction Method:</dt>
                <dd style="margin: 0;">${debug.extraction_method || 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Span Match Notes:</dt>
                <dd style="margin: 0;">${debug.span_match_notes || 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Chosen Weight (days):</dt>
                <dd style="margin: 0;">${debug.chosen_weight_days !== null ? debug.chosen_weight_days : 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Chosen Precision:</dt>
                <dd style="margin: 0;">${debug.chosen_precision !== null ? debug.chosen_precision : 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Article Title:</dt>
                <dd style="margin: 0; word-break: break-word;">${debug.title || 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Page ID:</dt>
                <dd style="margin: 0;">${debug.pageid || 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Extract Snippet:</dt>
                <dd style="margin: 0; font-family: monospace; white-space: pre-wrap; word-break: break-word;">${debug.extract_snippet || 'N/A'}</dd>
            </dl>
        `;
    } catch (error) {
        console.error('[Timeline] Error fetching extraction debug:', error);
        debugContent.innerHTML = `<em style="color: #b00020;">Failed to load debug information: ${error.message}</em>`;
    }
}

// Add close button handler
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('event-details');
    const closeBtn = document.getElementById('close-details-btn');
    
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.classList.add('hidden');
        });
    }
    
    // Close on overlay click (not the container)
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
        }
    });
    
    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
            modal.classList.add('hidden');
        }
    });
});

/**
 * Initialize when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
    // Set up reset zoom button
    const resetZoomBtn = document.getElementById('reset-zoom-btn');
    if (resetZoomBtn) {
        resetZoomBtn.addEventListener('click', resetZoom);
    }
    
    // Set up fullscreen button
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', toggleFullscreen);
    }
    
    // Listen for fullscreen changes (triggered by button, escape key, or browser UI)
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    
    // Wait a tick to ensure orchestrator is ready
    setTimeout(initializeTimeline, 0);
});
