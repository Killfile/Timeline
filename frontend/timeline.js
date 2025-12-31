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
const VISIBLE_LANES = 10;  // Fixed number of lanes always visible
const CHAR_WIDTH = 8;
const PADDING = 8;

// D3 selection references
let svg, xScale, xAxis, zoom;
let currentTransform = d3.zoomIdentity;

// Debounce timer for viewport event reloading
let reloadTimer = null;
const RELOAD_DEBOUNCE_MS = 300;

/**
 * Convert event year/BC flag to numeric scale value
 * @param {number} year - The year value from the API (always positive)
 * @param {boolean} isBC - Whether this is a BC date
 * @returns {number} Scale year (negative for BC, positive for AD)
 */
function toYearNumber(year, isBc) {
    if (year === null || year === undefined) return null;
    return isBc ? -year : year;
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
            
            console.log(`[Timeline] Loading events for viewport: ${isStartBC ? Math.abs(Math.round(startYear)) + ' BC' : Math.round(startYear) + ' AD'} to ${isEndBC ? Math.abs(Math.round(endYear)) + ' BC' : Math.round(endYear) + ' AD'}`);
            
            // Load events for this viewport
            const events = await window.timelineBackend.loadViewportEvents({
                viewportStart: Math.abs(Math.round(startYear)),
                viewportEnd: Math.abs(Math.round(endYear)),
                isStartBC,
                isEndBC,
                limit: 1000
            });
            
            console.log(`[Timeline] Loaded ${events.length} events for viewport`);
            
            // Events are already set in orchestrator by backend
            // The packing module will automatically repack using the current transformed scale
            // because backend.setEvents() triggers the 'events' notification
            
        } catch (error) {
            console.error('[Timeline] Error reloading viewport events:', error);
        }
    }, RELOAD_DEBOUNCE_MS);
}

/**
 * Initialize the timeline renderer
 * Sets up the SVG container, scales, and event handlers
 */
function initializeTimeline() {
    const container = d3.select('#timeline');
    const width = container.node().clientWidth;
    const height = VISIBLE_LANES * LANE_HEIGHT + 50; // Fixed height based on lanes + axis space

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
        .attr('transform', `translate(0, ${VISIBLE_LANES * LANE_HEIGHT})`);

    // Initialize x-scale as LINEAR (not time scale!)
    // Use numeric years (negative for BC, positive for AD)
    xScale = d3.scaleLinear()
        .domain([-3000, 2024])
        .range([0, width]);

    // Create and render initial axis
    xAxis = d3.axisBottom(xScale)
        .ticks(10)
        .tickFormat(d => {
            const year = Math.round(d);
            if (year < 0) return `${Math.abs(year)} BC`;
            if (year === 0) return '1 BC';
            return `${year} AD`;
        });
    
    xAxisGroup.call(xAxis);

    // Store scale in orchestrator so packing module can use it
    window.timelineOrchestrator.setScale(xScale);

    // Set initial time range in stats
    const initialDomain = xScale.domain();
    const initialStats = window.timelineOrchestrator.getStats();
    initialStats.timeRange = {
        start: initialDomain[0],
        end: initialDomain[1]
    };
    window.timelineOrchestrator.updateStats(initialStats);

    // Setup zoom behavior
    zoom = d3.zoom()
        .scaleExtent([0.5, 200000])
        .on('zoom', handleZoom);

    svg.call(zoom);

    // Draw lane guide lines (fixed, not part of zoom group)
    const laneGuides = svg.append('g')
        .attr('class', 'lane-guides');
    
    for (let i = 0; i <= VISIBLE_LANES; i++) {
        laneGuides.append('line')
            .attr('x1', 0)
            .attr('x2', width)
            .attr('y1', i * LANE_HEIGHT)
            .attr('y2', i * LANE_HEIGHT)
            .attr('stroke', '#333')
            .attr('stroke-width', i === 0 || i === VISIBLE_LANES ? 1 : 0.5)
            .attr('opacity', 0.2);
    }

    // Subscribe to orchestrator state changes
    window.timelineOrchestrator.subscribe('eventsUpdated', render);
    window.timelineOrchestrator.subscribe('laneAssignmentsUpdated', render);
    window.timelineOrchestrator.subscribe('categoryColorsUpdated', render);

    // Initial render
    render();
}

/**
 * Handle zoom/pan interactions
 * Updates the viewport state and triggers lane recalculation
 */
function handleZoom(event) {
    currentTransform = event.transform;
    
    // Rescale the X axis with the new transform
    const newXScale = event.transform.rescaleX(xScale);
    svg.select('.x-axis').call(xAxis.scale(newXScale));

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
 * Convert event year/BC flag to numeric scale value
 */
function toYearNumber(year, isBc) {
    if (year === null || year === undefined) return null;
    return isBc ? -year : year;
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
            const startYear = toYearNumber(d.start_year, d.is_bc_start);
            const x = startYear !== null ? scale(startYear) : 0;
            return `translate(${x}, ${y})`;
        }
    });

    // Update span bars (only for span events)
    groups.select('rect.timeline-span')
        .attr('x', d => {
            if (!hasSpan(d)) return 0;
            const startYear = toYearNumber(d.start_year, d.is_bc_start);
            const endYear = toYearNumber(d.end_year, d.is_bc_end);
            const sx = startYear !== null ? scale(startYear) : 0;
            const ex = endYear !== null ? scale(endYear) : sx;
            return Math.min(sx, ex);
        })
        .attr('width', d => {
            if (!hasSpan(d)) return 0;
            const startYear = toYearNumber(d.start_year, d.is_bc_start);
            const endYear = toYearNumber(d.end_year, d.is_bc_end);
            const sx = startYear !== null ? scale(startYear) : 0;
            const ex = endYear !== null ? scale(endYear) : sx;
            return Math.max(3, Math.abs(ex - sx));
        });

    // Update labels for span events
    groups.select('text.event-label')
        .attr('x', d => {
            if (!hasSpan(d)) return 0; // Moment events: label at group center
            const startYear = toYearNumber(d.start_year, d.is_bc_start);
            const endYear = toYearNumber(d.end_year, d.is_bc_end);
            const sx = startYear !== null ? scale(startYear) : 0;
            const ex = endYear !== null ? scale(endYear) : sx;
            return (sx + ex) / 2; // Span events: label at bar center
        })
        .attr('visibility', d => {
            // Show labels only for wide enough bars
            if (!hasSpan(d)) return 'visible'; // Always show for moments
            const startYear = toYearNumber(d.start_year, d.is_bc_start);
            const endYear = toYearNumber(d.end_year, d.is_bc_end);
            const sx = startYear !== null ? scale(startYear) : 0;
            const ex = endYear !== null ? scale(endYear) : sx;
            const width = Math.abs(ex - sx);
            return width > 20 ? 'visible' : 'hidden'; // Lower threshold from 30 to 20
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
            const startYear = toYearNumber(event.start_year, event.is_bc_start);
            const endYear = toYearNumber(event.end_year, event.is_bc_end);
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
        .on('click', handleEventClick);

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
    groupsMerged.select('circle.timeline-event')
        .attr('fill', d => categoryColors.get(d.category) || '#999')
        .style('opacity', d => hasSpan(d) ? 0 : 0.85); // Hide dots for span events

    groupsMerged.select('rect.timeline-span')
        .attr('fill', d => categoryColors.get(d.category) || '#999')
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

    // Update placed events count
    window.timelineOrchestrator.setState({
        stats: {
            ...state.stats,
            eventsPlaced: eventData.length
        }
    });
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
    const startYearNum = toYearNumber(d.start_year, d.is_bc_start);
    const endYearNum = toYearNumber(d.end_year, d.is_bc_end);
    const pixelX = currentScale ? currentScale(startYearNum) : 'N/A';
    const pixelWidth = (currentScale && endYearNum) 
        ? Math.abs(currentScale(endYearNum) - currentScale(startYearNum))
        : 'N/A';
    
    // Populate basic info
    title.textContent = d.title || d.name || 'Untitled Event';
    period.textContent = periodText;
    category.textContent = d.category || 'Unknown';
    
    // Create detailed description with full text and placement data
    description.innerHTML = `
        <div style="margin-bottom: 1em;">
            <strong>Full Text:</strong><br/>
            ${d.text || d.description || 'No description available'}
        </div>
        
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
                <dt style="font-weight: bold;">Source:</dt>
                <dd style="margin: 0;">${d.source || 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Article Title:</dt>
                <dd style="margin: 0; word-break: break-word;">${d.article_title || 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Weight (days):</dt>
                <dd style="margin: 0;">${d.chosen_weight_days !== null ? d.chosen_weight_days : 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Extraction Strategy:</dt>
                <dd style="margin: 0;">${d.extraction_strategy || 'N/A'}</dd>
                
                <dt style="font-weight: bold;">Match Type:</dt>
                <dd style="margin: 0;">${d.span_match_notes || 'N/A'}</dd>
            </dl>
        </details>
    `;
    
    // Set Wikipedia link
    if (d.source_url) {
        wikipediaLink.href = d.source_url;
        wikipediaLink.style.display = 'block';
    } else {
        wikipediaLink.style.display = 'none';
    }
    
    // Show the modal
    modal.classList.remove('hidden');
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
    // Wait a tick to ensure orchestrator is ready
    setTimeout(initializeTimeline, 0);
});
