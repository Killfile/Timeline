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

// Configuration constants
const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`;
const LANE_HEIGHT = 20;
const AXIS_HEIGHT = 50; // Height reserved for X-axis
const MIN_LANES = 10;   // Minimum number of lanes
const CHAR_WIDTH = 8;
const PADDING = 8;
const MAX_LABELS = 50; // Maximum number of labels to show at once
const MIN_LABEL_WIDTH = 20; // Minimum pixel width for a label

// D3 selection references
let svg, xScale, xAxis, zoom;
let currentTransform = d3.zoomIdentity;
let initialTransform = d3.zoomIdentity; // Store initial transform for reset zoom
let initialDomain = null; // Store initial domain for reset zoom
let tooltip = null;  // Tooltip for hover preview

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
 * Reload events for the current viewport with debouncing
 * @param {number} startYear - Viewport start year (negative for BC)
 * @param {number} endYear - Viewport end year (negative for BC)
 */
function reloadViewportEvents(startYear, endYear) {
    // Clear existing timer
    if (reloadTimer) {
        clearTimeout(reloadTimer);
    }
    
    // Debounce: wait for user to stop zooming/panning
    reloadTimer = setTimeout(async () => {
        try {
            const isStartBC = startYear < 0;
            const isEndBC = endYear < 0;
            
            // Get selected categories from orchestrator
            const selectedCategories = window.timelineOrchestrator.getSelectedCategories();
            
            console.log(`[Timeline] Loading events for viewport: ${isStartBC ? Math.abs(Math.round(startYear)) + ' BC' : Math.round(startYear) + ' AD'} to ${isEndBC ? Math.abs(Math.round(endYear)) + ' BC' : Math.round(endYear) + ' AD'}`);
            console.log(`[Timeline] Category filter: ${selectedCategories.length} categories selected`);
            
            // Load events for this viewport with category filter
            const events = await window.timelineBackend.loadViewportEvents({
                viewportStart: Math.abs(Math.round(startYear)),
                viewportEnd: Math.abs(Math.round(endYear)),
                isStartBC,
                isEndBC,
                limit: 1000,
                categories: selectedCategories.length > 0 ? selectedCategories : undefined
            });
            
            console.log(`[Timeline] Loaded ${events.length} events for viewport`);
            
            // Events are already set in orchestrator by backend
            // The packing module will automatically repack using the current transformed scale
            // because backend.setEvents() triggers the 'events' notification
            // Note: eventsInScope will be updated by render() after filtering to visible events
            
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

    // Reload events for the new viewport (debounced)
    reloadViewportEvents(newDomain[0], newDomain[1]);
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
    
    // First pass: collect all events with their widths and weights
    const eventWidths = [];
    groups.each(function(d) {
        const startYear = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
        const endYear = toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day);
        const sx = startYear !== null ? scale(startYear) : 0;
        const ex = endYear !== null ? scale(endYear) : sx;
        const width = Math.abs(ex - sx);
        
        eventWidths.push({
            id: d.id,
            width: width,
            weight: d.weight || 0,
            hasSpan: hasSpan(d)
        });
    });
    
    // Filter to events wide enough for labels and sort by weight
    const labelCandidates = eventWidths
        .filter(e => e.hasSpan && e.width > MIN_LABEL_WIDTH)
        .sort((a, b) => b.weight - a.weight) // Sort by weight descending
        .slice(0, MAX_LABELS) // Take top N
        .map(e => e.id);
    
    const shouldShowLabel = new Set(labelCandidates);
    
    console.log(`[Timeline] Label selection: ${eventWidths.filter(e => e.hasSpan && e.width > MIN_LABEL_WIDTH).length} candidates, showing ${labelCandidates.length} labels`);
    
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
            const endYear = toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day);
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

    // Prepare event data with positions, filtering to only visible events
    const eventData = events
        .filter(event => {
            // Check if event overlaps with viewport
            const startYear = toYearNumber(event.start_year, event.is_bc_start, event.start_month, event.start_day);
            const endYear = toYearNumber(event.end_year, event.is_bc_end, event.end_month, event.end_day);
            if (startYear === null) return false;
            const eventEndYear = endYear !== null ? endYear : startYear;
            return eventEndYear >= viewportStart && startYear <= viewportEnd;
        })
        .filter(event => laneAssignments.has(event.id)); // Only render placed events

    console.log(`[Timeline] After filtering: ${eventData.length} events to render (viewport: ${Math.round(viewportStart)} to ${Math.round(viewportEnd)})`);

    // Bind data to event groups
    const eventGroups = svg.selectAll('.event-group')
        .data(eventData, d => d.id);

    // Exit (remove old events)
    eventGroups.exit().remove();

    // Enter (create new events)
    const groupsEnter = eventGroups.enter()
        .append('g')
        .attr('class', 'event-group')
        .style('cursor', 'pointer')
        .on('click', handleEventClick)
        .on('mouseover', handleEventMouseOver)
        .on('mousemove', handleEventMouseMove)
        .on('mouseout', handleEventMouseOut);

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
        .style('opacity', d => hasSpan(d) ? 0 : 0.85); // Hide dots for span events

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
        .style('opacity', d => hasSpan(d) ? 0.75 : 0); // Hide bars for moment events

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
