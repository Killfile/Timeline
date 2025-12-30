// API Configuration
const API_URL = window.location.protocol + '//' + window.location.hostname + ':8000';

// Viewport-based loading config
const MAX_VISIBLE_EVENTS = 100;  // Tunable: how many highest-weight events to show at once

// Extract the first sentence for compact UI labels.
// Remove date prefixes and limit to 30 characters.
function firstSentence(text) {
    if (!text) return '';
    let s = String(text).replace(/\s+/g, ' ').trim();
    if (!s) return '';

    // Remove date prefixes like "687 BC—", "c. 1000 BC—", "1500-1600—"
    // Pattern matches: optional circa, year/range, optional BC/AD/BCE/CE, optional separator
    s = s.replace(/^(c\.|ca\.|circa)?\s*\d+(\s*-\s*\d+)?(\s*(BC|AD|BCE|CE))?\s*[—–-]\s*/i, '');
    
    // Find the first real sentence terminator, ignoring '.' inside parentheses.
    // This handles common Wikipedia patterns like "(no. 4)".
    let depth = 0;
    for (let i = 0; i < s.length; i++) {
        const ch = s[i];
        if (ch === '(') depth++;
        else if (ch === ')' && depth > 0) depth--;

        if (depth > 0) continue;

        if (ch === '.' || ch === '!' || ch === '?' || ch === '…') {
            const next = s[i + 1];
            if (next === undefined || /\s/.test(next)) {
                s = s.slice(0, i + 1).trim();
                break;
            }
        }
    }

    // Limit to 30 characters with ellipsis
    if (s.length > 30) {
        return s.slice(0, 29) + '…';
    }

    return s;
}

// Timeline state
let allEvents = [];
let filteredEvents = [];
let selectedEvent = null;

// Viewport-based loading: track which events are currently rendered.
let renderedEventIds = new Set();
let viewportReloadTimeout = null;

// D3 timeline variables
let svg, xScale, yScale, xAxis, zoom;
const margin = { top: 40, right: 40, bottom: 60, left: 60 };

// Zoom state (used for zoom-dependent label opacity)
let currentZoomK = 1;
let currentTransform = d3.zoomIdentity;

// Most recent x-domain used for computing viewport-length-based opacity.
let currentViewportDomain = null;


// Color scale for categories
const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initializeTimeline();
    loadCategories();
    loadEvents();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('search-btn').addEventListener('click', handleSearch);
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
    document.getElementById('category-select').addEventListener('change', handleCategoryFilter);
    document.getElementById('reset-zoom-btn').addEventListener('click', resetZoom);
    document.getElementById('refresh-btn').addEventListener('click', loadEvents);
    document.getElementById('fullscreen-btn').addEventListener('click', toggleFullscreen);
    document.getElementById('close-details-btn').addEventListener('click', closeEventDetails);
    
    // Keyboard navigation
    document.addEventListener('keydown', handleKeyboardNavigation);
}

// Handle keyboard navigation
function handleKeyboardNavigation(e) {
    // Don't interfere if user is typing in an input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
    }
    
    // Escape key exits fullscreen mode
    if (e.key === 'Escape' && document.body.classList.contains('fullscreen')) {
        e.preventDefault();
        toggleFullscreen();
        return;
    }
    
    const step = 0.2; // 20% of current view
    const zoomFactor = 1.2;
    
    switch(e.key) {
        case 'ArrowUp':
            e.preventDefault();
            // Zoom in
            svg.transition()
                .duration(300)
                .call(zoom.scaleBy, zoomFactor);
            break;
            
        case 'ArrowDown':
            e.preventDefault();
            // Zoom out
            svg.transition()
                .duration(300)
                .call(zoom.scaleBy, 1 / zoomFactor);
            break;
            
        case 'ArrowLeft':
            e.preventDefault();
            // Pan left
            const [minX, maxX] = xScale.domain();
            const rangeX = maxX - minX;
            const shiftLeft = rangeX * step;
            svg.transition()
                .duration(300)
                .call(zoom.translateBy, 50, 0); // Positive x moves view right (shows earlier events)
            break;
            
        case 'ArrowRight':
            e.preventDefault();
            // Pan right
            svg.transition()
                .duration(300)
                .call(zoom.translateBy, -50, 0); // Negative x moves view left (shows later events)
            break;
    }
}

// Load categories from API
async function loadCategories() {
    try {
        const response = await fetch(`${API_URL}/categories`);
        const data = await response.json();
        
        const select = document.getElementById('category-select');
        data.categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.category;
            option.textContent = `${cat.category} (${cat.count})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

// Load events from API
async function loadEvents(category = null) {
    try {
        // First, get the full time range from stats
        const statsResponse = await fetch(`${API_URL}/stats`);
        const stats = await statsResponse.json();
        
        // Load initial dataset
        let url = `${API_URL}/events?limit=500`;
        if (category) {
            url += `&category=${encodeURIComponent(category)}`;
        }
        
        const response = await fetch(url);
        allEvents = await response.json();
        filteredEvents = [...allEvents];
        
        updateStats();
        
        // Render timeline to set up scales/axes with FULL time range
        renderTimelineWithFullRange(stats);
        
        console.log('[loadEvents] Timeline initialized, clearing markers and preparing viewport load');
        
        // Clear all markers immediately and switch to viewport mode
        svg.selectAll('.event-group').remove();
        renderedEventIds.clear();
        
        // Load viewport-based events (give time for scales to be ready)
        setTimeout(() => {
            console.log('[loadEvents] Starting viewport load');
            loadEventsInViewport(category);
        }, 100);
    } catch (error) {
        console.error('Error loading events:', error);
        showError('Failed to load events. Please refresh the page.');
    }
}

// Load events for current viewport (weight-based, top X).
async function loadEventsInViewport(category = null) {
    console.log('[loadEventsInViewport] Called with category:', category, 'xScale exists:', !!xScale);
    
    try {
        if (!xScale) {
            console.warn('[loadEventsInViewport] xScale not initialized yet, aborting');
            return;
        }

        // Get the current zoomed/panned scale, not the base scale
        const currentScale = currentTransform ? currentTransform.rescaleX(xScale) : xScale;
        const [dMin, dMax] = currentScale.domain();
        const vMin = Math.min(dMin, dMax);
        const vMax = Math.max(dMin, dMax);

        // Determine BC flags for viewport bounds
        const isMinBc = vMin < 0;
        const isMaxBc = vMax < 0;
        const startYear = Math.abs(Math.floor(vMin));
        const endYear = Math.abs(Math.ceil(vMax));

        let url = `${API_URL}/events?viewport_start=${startYear}&viewport_end=${endYear}&viewport_is_bc_start=${isMinBc}&viewport_is_bc_end=${isMaxBc}&limit=${MAX_VISIBLE_EVENTS}`;
        if (category) {
            url += `&category=${encodeURIComponent(category)}`;
        }

        console.log('[Viewport] Loading:', { vMin, vMax, startYear, endYear, isMinBc, isMaxBc, url });

        const response = await fetch(url);
        const newEvents = await response.json();

        console.log('[Viewport] Loaded', newEvents.length, 'events', newEvents.slice(0, 3));

        // Diff and incrementally add/remove markers.
        updateTimelineMarkers(newEvents);
        
        // Explicitly render legend to ensure it updates
        renderLegend();
        console.log('[Viewport] Timeline markers and legend updated');
    } catch (error) {
        console.error('Error loading viewport events:', error);
    }
}

// Initialize scales and axes without rendering markers
function initializeScales() {
    if (filteredEvents.length === 0) {
        return;
    }
    
    // Extract years and convert BC years to negative
    const years = filteredEvents
        .filter(e => e.start_year !== null)
        .map(e => e.is_bc_start ? -e.start_year : e.start_year);
    
    if (years.length === 0) {
        return;
    }
    
    const minYear = Math.min(...years);
    const maxYear = Math.max(...years);
    const padding = (maxYear - minYear) * 0.1;
    
    xScale.domain([minYear - padding, maxYear + padding]);
    currentViewportDomain = getViewportDomain(xScale);
    
    // Update axis
    svg.select('.x-axis')
        .call(xAxis);
}

// Incrementally update timeline markers using D3 enter/exit/update pattern.
function updateTimelineMarkers(newEvents) {
    // Update filteredEvents with the new viewport data
    filteredEvents = newEvents;

    const newEventIds = new Set(newEvents.map(e => e.id));

    // Update rendered set
    renderedEventIds = newEventIds;

    const renderData = newEvents.filter(e => e.start_year !== null);

    // --- Global sublane layout (no category segregation) ---
    function toYearNumber(year, isBc, month = null, day = null) {
        if (year === null || year === undefined) return null;
        
        let fractionalYear = isBc ? -year : year;
        
        // Add month and day precision if available
        if (month !== null && month !== undefined) {
            // Days in each month (non-leap year approximation)
            const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
            
            // Calculate day of year
            let dayOfYear = 0;
            for (let i = 0; i < month - 1; i++) {
                dayOfYear += daysInMonth[i];
            }
            if (day !== null && day !== undefined) {
                dayOfYear += day;
            } else {
                // If only month is specified, use middle of month
                dayOfYear += Math.floor(daysInMonth[month - 1] / 2);
            }
            
            // Add fractional year (approximate 365 days per year)
            // For BC dates: -44 BC is represented as -44, January 1 should be closer to -43 (less negative)
            // For AD dates: 44 AD is represented as 44, January 1 should be closer to 44 (start of year)
            // In both cases, we ADD the fraction to move forward through the year
            const yearFraction = dayOfYear / 365.0;
            fractionalYear += yearFraction;
        }
        
        return fractionalYear;
    }

    function hasSpan(d) {
        return d.end_year !== null && d.end_year !== undefined;
    }

    function getNumericSpan(d) {
        const s = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
        const e = hasSpan(d) ? toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day) : s;
        if (s === null || e === null) return null;
        return {
            start: Math.min(s, e),
            end: Math.max(s, e),
        };
    }

    const sublaneById = new Map();
    
    // Sort all events globally by start time (spans before moments, then by start/end)
    const intervals = renderData
        .map(d => ({ d, span: getNumericSpan(d) }))
        .filter(x => x.span !== null)
        .sort((a, b) => {
            const aSpan = hasSpan(a.d) ? 0 : 1;
            const bSpan = hasSpan(b.d) ? 0 : 1;
            if (aSpan !== bSpan) return aSpan - bSpan;
            if (a.span.start !== b.span.start) return a.span.start - b.span.start;
            return a.span.end - b.span.end;
        });

    // Pack all events into lanes globally (no category boundaries)
    const laneEnds = [];
    for (const { d, span } of intervals) {
        let placed = false;
        for (let i = 0; i < laneEnds.length; i++) {
            if (span.start > laneEnds[i]) {
                sublaneById.set(d.id, i);
                laneEnds[i] = span.end;
                placed = true;
                break;
            }
        }
        if (!placed) {
            const i = laneEnds.length;
            sublaneById.set(d.id, i);
            laneEnds.push(span.end);
        }
    }

    const totalLanes = laneEnds.length || 1;

    // D3 data join
    const eventGroups = svg.selectAll('.event-group')
        .data(renderData, d => d.id);

    // Exit (fade out and remove)
    eventGroups.exit()
        .transition()
        .duration(250)
        .style('opacity', 0)
        .remove();

    // Enter (create new groups)
    const groupsEnter = eventGroups.enter()
        .append('g')
        .attr('class', 'event-group')
        .style('opacity', 0);

    // Span bar
    groupsEnter.append('rect')
        .attr('class', 'timeline-span')
        .attr('y', -4)
        .attr('height', 8)
        .attr('rx', 4)
        .attr('ry', 4)
        .style('opacity', 0.75)
        .style('pointer-events', 'none');

    // Moment dot
    groupsEnter.append('circle')
        .attr('class', 'timeline-event')
        .attr('r', 6)
        .attr('fill', d => colorScale(d.category || 'Unknown'))
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .style('opacity', 0.85)
        .style('pointer-events', 'none');

    // Hit area
    groupsEnter.append('rect')
        .attr('class', 'event-hit-area')
        .attr('x', -18)
        .attr('y', -12)
        .attr('width', 36)
        .attr('height', 24)
        .attr('rx', 10)
        .attr('ry', 10)
        .style('fill', 'transparent')
        .style('pointer-events', 'all')
        .on('click', (event, d) => showEventDetails(d))
        .on('mouseenter', function (event, d) {
            const g = d3.select(this.parentNode);
            g.classed('is-hover', true);
            
            // Dim all other event labels by setting inline opacity
            svg.selectAll('.event-group').each(function(eventData) {
                const group = d3.select(this);
                if (eventData.id !== d.id) {
                    group.select('.event-label').style('opacity', 0.1);
                }
            });
            
            // Make this event's label fully opaque
            const textElement = g.select('.event-label');
            textElement.style('opacity', 1);
            
            // Replace text with full untruncated title
            textElement.attr('data-original-text', textElement.text());
            textElement.text(d.title);
        })
        .on('mouseleave', function (event, d) {
            const g = d3.select(this.parentNode);
            g.classed('is-hover', false);
            
            // Restore original opacity for all labels
            const labelOp = getLabelOpacityForZoom(currentTransform.k);
            svg.selectAll('.event-group .event-label')
                .style('opacity', labelOp);
            
            // Restore truncated text
            const textElement = g.select('.event-label');
            const originalText = textElement.attr('data-original-text');
            if (originalText) {
                textElement.text(originalText);
                textElement.attr('data-original-text', null);
            }
        });

    // Tooltip
    groupsEnter.append('title')
        .text(d => firstSentence(d.title));

    // Labels
    groupsEnter.append('text')
        .attr('class', 'event-label')
        .attr('x', 0)
        .attr('y', 0)
        .attr('dy', -12)
        .attr('text-anchor', 'middle')
        .text(d => firstSentence(d.title));

    // Merge enter + update
    const groupsMerged = eventGroups.merge(groupsEnter);

    // Helper functions for positioning
    function getStartX(d, scale) {
        const n = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
        return n === null ? null : scale(n);
    }

    function getEndX(d, scale) {
        if (!hasSpan(d)) return null;
        
        // Check if this is a single-day event (same year, month, and day)
        const isSingleDay = d.start_year === d.end_year &&
                           d.start_month === d.end_month &&
                           d.start_day === d.end_day &&
                           d.start_day !== null && d.start_day !== undefined;
        
        if (isSingleDay) {
            // For single-day events, add 1 day to make them span the full day
            const startN = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
            if (startN === null) return null;
            return scale(startN + (1 / 365.0)); // Add 1 day
        }
        
        const n = toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day);
        return n === null ? null : scale(n);
    }

    function getYForEvent(d) {
        const container = document.getElementById('timeline-container');
        const height = container.clientHeight;
        const availableHeight = height - margin.top - margin.bottom;
        
        const sublaneIdx = sublaneById.get(d.id) || 0;
        
        // Limit visible lanes to prevent overcrowding
        const maxVisibleLanes = Math.min(20, totalLanes);
        const clampedIdx = Math.min(sublaneIdx, maxVisibleLanes - 1);
        
        // Distribute events across available vertical space
        const laneHeight = availableHeight / maxVisibleLanes;
        return margin.top + (clampedIdx + 0.5) * laneHeight;
    }

    function applyPositions(scale) {
        // Always select current groups (don't rely on closure)
        const groups = svg.selectAll('.event-group');
        
        groups
            .attr('transform', d => {
                const y = getYForEvent(d);
                if (hasSpan(d)) {
                    return `translate(0, ${y})`;
                }
                const x = getStartX(d, scale) ?? 0;
                return `translate(${x}, ${y})`;
            });

        groups.select('circle.timeline-event')
            .attr('display', d => hasSpan(d) ? 'none' : null);

        groups.select('rect.timeline-span')
            .attr('display', d => hasSpan(d) ? null : 'none')
            .attr('x', d => {
                const x0 = getStartX(d, scale);
                const x1 = getEndX(d, scale);
                if (x0 === null || x1 === null) return 0;
                const minWidth = 12; // Minimum width to match circle size
                const actualWidth = Math.abs(x1 - x0);
                const effectiveWidth = Math.max(minWidth, actualWidth);
                const leftmost = Math.min(x0, x1);
                // Center the bar if we're using minimum width
                if (actualWidth < minWidth) {
                    return leftmost - (minWidth - actualWidth) / 2;
                }
                return leftmost;
            })
            .attr('width', d => {
                const x0 = getStartX(d, scale);
                const x1 = getEndX(d, scale);
                if (x0 === null || x1 === null) return 0;
                const minWidth = 12; // Minimum width to match circle size
                return Math.max(minWidth, Math.abs(x1 - x0));
            })
            .attr('fill', d => colorScale(d.category || 'Unknown'));

        // Position hit areas for spans
        groups.select('rect.event-hit-area')
            .attr('x', d => {
                if (!hasSpan(d)) return -18;
                const sx = getStartX(d, scale);
                const ex = getEndX(d, scale);
                if (sx === null || ex === null) return -18;
                const minWidth = 12;
                const actualWidth = Math.abs(ex - sx);
                const effectiveWidth = Math.max(minWidth, actualWidth);
                const leftmost = Math.min(sx, ex);
                // Center the hit area if using minimum width
                if (actualWidth < minWidth) {
                    return leftmost - (minWidth - actualWidth) / 2 - 8;
                }
                return leftmost - 8;
            })
            .attr('width', d => {
                if (!hasSpan(d)) return 36;
                const sx = getStartX(d, scale);
                const ex = getEndX(d, scale);
                if (sx === null || ex === null) return 36;
                const minWidth = 12;
                const effectiveWidth = Math.max(minWidth, Math.abs(ex - sx));
                return Math.max(36, effectiveWidth + 16);
            });

        // Position labels for spans
        groups.select('text.event-label')
            .attr('x', d => {
                if (!hasSpan(d)) {
                    return 0;
                }
                const sx = getStartX(d, scale);
                const ex = getEndX(d, scale);
                if (sx === null || ex === null) {
                    return 0;
                }
                return (sx + ex) / 2;
            });

        const vd = getViewportDomain(scale);
        const viewSpanYears = vd.end - vd.start;

        groups.select('rect.timeline-span')
            .style('opacity', d => getOpacityForEventInViewport(d, viewSpanYears));
        
        groups.select('circle.timeline-event')
            .style('opacity', d => getOpacityForEventInViewport(d, viewSpanYears));

        const labelOp = getLabelOpacityForZoom(currentTransform.k);
        groups.select('text.event-label')
            .style('opacity', labelOp);
    }

    // Apply positions and fade in new elements
    // Use the current transform to get the correct scale (handles zoom state)
    const currentScale = currentTransform ? currentTransform.rescaleX(xScale) : xScale;
    applyPositions(currentScale);
    
    groupsEnter
        .transition()
        .duration(250)
        .style('opacity', 1);

    // Update stats
    updateStats();

    // Store helpers for zoom callback
    window._timelineHelpers = {
        applyPositions,
        toYearNumber,
        hasSpan,
        getStartX,
        getEndX,
        getYForEvent,
        sublaneById,
        totalLanes,
        getViewportDomain,
        getOpacityForEventInViewport,
        getLabelOpacityForZoom
    };
}

// Load statistics
async function updateStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        const stats = await response.json();
        
        document.getElementById('total-events').textContent = stats.total_events;
        
        // Show count of currently rendered events in viewport mode
        const loadedCount = renderedEventIds.size > 0 ? renderedEventIds.size : filteredEvents.length;
        console.log('[updateStats] renderedEventIds.size:', renderedEventIds.size, 'filteredEvents.length:', filteredEvents.length, 'showing:', loadedCount);
        document.getElementById('loaded-events').textContent = loadedCount;
        
        if (stats.earliest_year && stats.latest_year) {
            const earliest = formatYearDisplay(stats.earliest_year);
            const latest = formatYearDisplay(stats.latest_year);
            document.getElementById('time-range').textContent = `${earliest} to ${latest}`;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Format year for display
// Format year display for axis ticks, adapting to zoom level
// When zoomed in beyond 1 year, show months and days instead of decimals
function formatYearDisplay(year, viewportSpan) {
    const isBC = year < 0;
    const absYear = Math.abs(year);
    const suffix = isBC ? ' BC' : ' AD';
    
    // If viewport span is undefined, fall back to simple year display
    if (viewportSpan === undefined || viewportSpan === null) {
        return Math.round(absYear) + suffix;
    }
    
    // For spans > 2 years, just show the year
    if (viewportSpan > 2) {
        return Math.round(absYear) + suffix;
    }
    
    // For BC dates: -43.8 represents March 44 BC
    // We need to extract: year=44, fraction=0.2 (not 0.8)
    // For AD dates: 43.8 represents October 43 AD
    // We need to extract: year=43, fraction=0.8
    let wholeYear, fractionalYear;
    if (isBC) {
        // For BC: -43.8 means 44 BC, 20% into the year
        wholeYear = Math.ceil(absYear);  // 44
        fractionalYear = wholeYear - absYear;  // 44 - 43.8 = 0.2
    } else {
        // For AD: normal calculation
        wholeYear = Math.floor(absYear);  // 43
        fractionalYear = absYear - wholeYear;  // 43.8 - 43 = 0.8
    }
    
    // For spans 0.1 to 2 years, show year and month
    if (viewportSpan > 0.1) {
        const month = Math.floor(fractionalYear * 12) + 1; // 1-12
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${monthNames[month - 1]} ${wholeYear}${suffix}`;
    }
    
    // For spans < 0.1 years (~36 days), show month and day
    const dayOfYear = Math.floor(fractionalYear * 365) + 1; // 1-365
    
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
    
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${monthNames[month]} ${day}, ${wholeYear}${suffix}`;
}

// Initialize D3 timeline
function initializeTimeline() {
    const container = document.getElementById('timeline-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    svg = d3.select('#timeline')
        .attr('width', width)
        .attr('height', height);
    
    // Create scales
    xScale = d3.scaleLinear()
        .range([margin.left, width - margin.right]);
    
    // yScale is used as a category band scale (one lane per category)
    yScale = d3.scaleBand()
        .range([height - margin.bottom, margin.top])
        .paddingInner(0.6)
        .paddingOuter(0.4);
    
    // Create axes
    xAxis = d3.axisBottom(xScale)
        .tickFormat(d => {
            // Calculate viewport span from the current scale
            const domain = (currentTransform ? currentTransform.rescaleX(xScale) : xScale).domain();
            const span = Math.abs(domain[1] - domain[0]);
            return formatYearDisplay(d, span);
        });
    
    // Add zoom behavior
    zoom = d3.zoom()
        // Allow deep zoom so a single year can span most/all of the viewport.
        // (Exact scale needed depends on the current domain span.)
        // Increase max zoom substantially so we can eventually reach day-level views.
        // (With a linear scale in "years", a day is ~1/365 of a year, so we need
        // orders of magnitude beyond "single-year" zoom.)
        .scaleExtent([0.5, 200000])
        .translateExtent([[0, 0], [width, height]])
        .extent([[0, 0], [width, height]])
        .on('zoom', zoomed);
    
    svg.call(zoom);
    
    // Add axis group
    svg.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(0, ${height - margin.bottom})`);
    
    // Add title
    svg.append('text')
        .attr('class', 'timeline-title')
        .attr('x', width / 2)
        .attr('y', 25)
        .attr('text-anchor', 'middle')
        .style('font-size', '16px')
        .style('font-weight', 'bold')
        .text('Historical Timeline (Zoom and Pan)');

    // Legend is rendered into a separate HTML element (#timeline-legend)
    // so it does not scale/translate with zoom/pan.
    // Initialize with loading state
    const legendEl = document.getElementById('timeline-legend');
    if (legendEl) {
        legendEl.innerHTML = '<div class="legend-empty">Loading events...</div>';
        console.log('[initializeTimeline] Legend element initialized');
    } else {
        console.error('[initializeTimeline] Legend element #timeline-legend not found in DOM');
    }
}

function clamp(val, lo, hi) {
    return Math.max(lo, Math.min(hi, val));
}

// Render timeline with full time range from stats (not just loaded events)
function renderTimelineWithFullRange(stats) {
    if (!stats.earliest_year || !stats.latest_year) {
        console.warn('No time range in stats, falling back to renderTimeline');
        return renderTimeline();
    }
    
    // Convert earliest and latest to numeric years (negative for BC)
    const minYear = stats.earliest_year;
    const maxYear = stats.latest_year;
    const padding = (maxYear - minYear) * 0.1;
    
    console.log('[renderTimelineWithFullRange] Setting domain:', minYear - padding, 'to', maxYear + padding);
    
    xScale.domain([minYear - padding, maxYear + padding]);
    currentViewportDomain = getViewportDomain(xScale);
    
    // Update axis
    svg.select('.x-axis')
        .call(xAxis);
}

function getViewportDomain(scale) {
    const d = scale.domain();
    const min = Math.min(d[0], d[1]);
    const max = Math.max(d[0], d[1]);
    return { start: min, end: max };
}

function getViewportSpanYears(scale) {
    const vd = getViewportDomain(scale);
    return Math.max(1e-9, vd.end - vd.start);
}

function getEventSpanYears(d) {
    // Calculate the span considering year, month, and day precision
    if (d.start_year === null || d.start_year === undefined) return 0;
    
    // Helper to convert year/month/day to fractional year number
    const toFractionalYear = (year, isBc, month, day) => {
        let fractionalYear = isBc ? -year : year;
        
        if (month !== null && month !== undefined) {
            const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
            let dayOfYear = 0;
            for (let i = 0; i < month - 1; i++) {
                dayOfYear += daysInMonth[i];
            }
            if (day !== null && day !== undefined) {
                dayOfYear += day;
            } else {
                dayOfYear += Math.floor(daysInMonth[month - 1] / 2);
            }
            const yearFraction = dayOfYear / 365.0;
            fractionalYear += yearFraction;
        }
        
        return fractionalYear;
    };
    
    const startFractional = toFractionalYear(
        d.start_year, 
        d.is_bc_start, 
        d.start_month, 
        d.start_day
    );
    
    const endFractional = (d.end_year === null || d.end_year === undefined)
        ? startFractional
        : toFractionalYear(d.end_year, d.is_bc_end, d.end_month, d.end_day);
    
    const spanYears = Math.max(0, Math.abs(endFractional - startFractional));
    
    // Special case: single-day events (same year, month, and day) should span 1 day
    if (spanYears === 0 && 
        d.start_day !== null && d.start_day !== undefined &&
        d.end_day !== null && d.end_day !== undefined &&
        d.start_year === d.end_year &&
        d.start_month === d.end_month &&
        d.start_day === d.end_day) {
        return 1 / 365.0;  // 1 day = 1/365 years
    }
    
    return spanYears;
}

function getOpacityForEventInViewport(d, viewSpanYears) {
    // Opacity is a function of how much of the current viewport the event occupies.
    // - Longer spans -> more opaque, up to spanning the whole viewport.
    // - Once longer than the viewport, it becomes progressively more transparent.
    // - Never fully disappears.
    // Moments are treated as tiny fractions.

    const minOpacity = 0.12;
    const maxOpacity = 1.0;  // Allow full opacity for events that fill the viewport

    const eventSpan = getEventSpanYears(d);
    // Treat moments as a tiny non-zero fraction so they remain visible.
    const momentEps = Math.max(1e-6, viewSpanYears / 5000);
    const effectiveSpan = eventSpan > 0 ? eventSpan : momentEps;

    const frac = effectiveSpan / Math.max(1e-9, viewSpanYears);

    // Below 1.0: ramp opacity up with sqrt (fast early, gentle later)
    if (frac <= 1) {
        const t = Math.sqrt(clamp(frac, 0, 1));
        return minOpacity + (maxOpacity - minOpacity) * t;
    }

    // Above 1.0: decay faster than sqrt so the fade is perceptible.
    // Power-law keeps it smooth and never fully disappears.
    const exponent = 1.25;
    const decay = 1 / Math.pow(frac, exponent);
    return clamp(maxOpacity * decay, minOpacity, maxOpacity);
}

function getLabelOpacityForZoom(k) {
    // Very low when zoomed out; increases with zoom.
    // Cap at 0.5 (50%) per requirement.
    const min = 0.04;
    const max = 0.5;

    // Normalize k from [1..10] -> [0..1]
    const t = Math.max(0, Math.min(1, (k - 1) / 9));
    return min + (max - min) * t;
}

// Render timeline with events
function renderTimeline() {
    if (filteredEvents.length === 0) {
        return;
    }
    
    // Extract years and convert BC years to negative
    const years = filteredEvents
        .filter(e => e.start_year !== null)
        .map(e => e.is_bc_start ? -e.start_year : e.start_year);
    
    if (years.length === 0) {
        return;
    }
    
    const minYear = Math.min(...years);
    const maxYear = Math.max(...years);
    const padding = (maxYear - minYear) * 0.1;
    
    xScale.domain([minYear - padding, maxYear + padding]);
    currentViewportDomain = getViewportDomain(xScale);
    
    // Update axis
    svg.select('.x-axis')
        .call(xAxis);
    
    const renderData = filteredEvents.filter(e => e.start_year !== null);

    // --- Global sublane layout (no category segregation) ---
    function toYearNumber(year, isBc, month = null, day = null) {
        if (year === null || year === undefined) return null;
        
        let fractionalYear = isBc ? -year : year;
        
        // Add month and day precision if available
        if (month !== null && month !== undefined) {
            // Days in each month (non-leap year approximation)
            const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
            
            // Calculate day of year
            let dayOfYear = 0;
            for (let i = 0; i < month - 1; i++) {
                dayOfYear += daysInMonth[i];
            }
            if (day !== null && day !== undefined) {
                dayOfYear += day;
            } else {
                // If only month is specified, use middle of month
                dayOfYear += Math.floor(daysInMonth[month - 1] / 2);
            }
            
            // Add fractional year (approximate 365 days per year)
            // For BC dates: -44 BC is represented as -44, January 1 should be closer to -43 (less negative)
            // For AD dates: 44 AD is represented as 44, January 1 should be closer to 44 (start of year)
            // In both cases, we ADD the fraction to move forward through the year
            const yearFraction = dayOfYear / 365.0;
            fractionalYear += yearFraction;
        }
        
        return fractionalYear;
    }

    function hasSpan(d) {
        // Only day-level precision should be momentary.
        // Until we ingest day precision, treat (start_year == end_year) as a span.
        return d.end_year !== null && d.end_year !== undefined;
    }

    function getNumericSpan(d) {
        const s = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
        const e = hasSpan(d) ? toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day) : s;
        if (s === null || e === null) return null;
        return {
            start: Math.min(s, e),
            end: Math.max(s, e),
        };
    }

    const sublaneById = new Map();
    
    // Sort all events globally by start time (spans before moments, then by start/end)
    const intervals = renderData
        .map(d => ({ d, span: getNumericSpan(d) }))
        .filter(x => x.span !== null)
        .sort((a, b) => {
            const aSpan = hasSpan(a.d) ? 0 : 1;
            const bSpan = hasSpan(b.d) ? 0 : 1;
            if (aSpan !== bSpan) return aSpan - bSpan;
            if (a.span.start !== b.span.start) return a.span.start - b.span.start;
            return a.span.end - b.span.end;
        });

    // Pack all events into lanes globally (no category boundaries)
    const laneEnds = [];
    for (const { d, span } of intervals) {
        let placed = false;
        for (let i = 0; i < laneEnds.length; i++) {
            if (span.start > laneEnds[i]) {
                sublaneById.set(d.id, i);
                laneEnds[i] = span.end;
                placed = true;
                break;
            }
        }
        if (!placed) {
            const i = laneEnds.length;
            sublaneById.set(d.id, i);
            laneEnds.push(span.end);
        }
    }

    const totalLanes = laneEnds.length || 1;

    // Bind data to a group so hover effects don't move the actual hit target
    const eventGroups = svg.selectAll('.event-group')
        .data(renderData, d => d.id);
    
    // Exit
    eventGroups.exit().remove();
    
    // Enter + Update
    const groupsEnter = eventGroups.enter()
        .append('g')
        .attr('class', 'event-group');

    // A span bar for events that have a range.
    // Note: we draw in local group coords; `x`/`width` get set on merge (also updated on zoom).
    groupsEnter.append('rect')
        .attr('class', 'timeline-span')
        .attr('y', -4)
        .attr('height', 8)
        .attr('rx', 4)
        .attr('ry', 4)
        .style('opacity', 0.75)
        .style('pointer-events', 'none');

    // Visible dot for moment-in-time events.
    groupsEnter.append('circle')
        .attr('class', 'timeline-event')
        .attr('r', 6)
        .attr('fill', d => colorScale(d.category || 'Unknown'))
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .style('opacity', 0.85)
        .style('pointer-events', 'none');

    // Invisible hit target (works for both dots and bars)
    groupsEnter.append('rect')
        .attr('class', 'event-hit-area')
        .attr('x', -18)
        .attr('y', -12)
        .attr('width', 36)
        .attr('height', 24)
        .attr('rx', 10)
        .attr('ry', 10)
        .style('fill', 'transparent')
        .style('pointer-events', 'all')
        .on('click', (event, d) => showEventDetails(d))
        .on('mouseenter', function (event, d) {
            const g = d3.select(this.parentNode);
            g.classed('is-hover', true);
            
            // Dim all other event labels by setting inline opacity
            svg.selectAll('.event-group').each(function(eventData) {
                const group = d3.select(this);
                if (eventData.id !== d.id) {
                    group.select('.event-label').style('opacity', 0.1);
                }
            });
            
            // Make this event's label fully opaque
            const textElement = g.select('.event-label');
            textElement.style('opacity', 1);
            
            // Replace text with full untruncated title
            textElement.attr('data-original-text', textElement.text());
            textElement.text(d.title);
        })
        .on('mouseleave', function (event, d) {
            const g = d3.select(this.parentNode);
            g.classed('is-hover', false);
            
            // Restore original opacity for all labels
            const labelOp = getLabelOpacityForZoom(currentTransform.k);
            svg.selectAll('.event-group .event-label')
                .style('opacity', labelOp);
            
            // Restore truncated text
            const textElement = g.select('.event-label');
            const originalText = textElement.attr('data-original-text');
            if (originalText) {
                textElement.text(originalText);
                textElement.attr('data-original-text', null);
            }
        });

    // Tooltip
    groupsEnter.append('title')
        .text(d => firstSentence(d.title));

    // Labels (always-on). Styling is mostly handled via CSS.
    groupsEnter.append('text')
        .attr('class', 'event-label')
        .attr('y', 0)
        .attr('dy', -12)
        .attr('text-anchor', 'middle')
        .text(d => firstSentence(d.title));

    const groupsMerged = eventGroups.merge(groupsEnter);

    function getStartX(d, scale) {
        const n = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
        return n === null ? null : scale(n);
    }

    function getEndX(d, scale) {
        if (!hasSpan(d)) return null;
        
        // Check if this is a single-day event (same year, month, and day)
        const isSingleDay = d.start_year === d.end_year &&
                           d.start_month === d.end_month &&
                           d.start_day === d.end_day &&
                           d.start_day !== null && d.start_day !== undefined;
        
        if (isSingleDay) {
            // For single-day events, add 1 day to make them span the full day
            const startN = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
            if (startN === null) return null;
            return scale(startN + (1 / 365.0)); // Add 1 day
        }
        
        const n = toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day);
        return n === null ? null : scale(n);
    }

    function getYForEvent(d) {
        const container = document.getElementById('timeline-container');
        const height = container.clientHeight;
        const availableHeight = height - margin.top - margin.bottom;
        
        const sublaneIdx = sublaneById.get(d.id) || 0;
        
        // Limit visible lanes to prevent overcrowding
        const maxVisibleLanes = Math.min(20, totalLanes);
        const clampedIdx = Math.min(sublaneIdx, maxVisibleLanes - 1);
        
        // Distribute events across available vertical space
        const laneHeight = availableHeight / maxVisibleLanes;
        return margin.top + (clampedIdx + 0.5) * laneHeight;
    }

    function applyPositions(scale) {
        groupsMerged
            .attr('transform', d => {
                // For dots we keep group anchored on the dot.
                // For spans we anchor group at y only and place the rect via x/width.
                const y = getYForEvent(d);

                if (hasSpan(d)) {
                    return `translate(0, ${y})`;
                }

                const x = getStartX(d, scale) ?? 0;
                return `translate(${x}, ${y})`;
            });

        // Dots only for non-span events
        groupsMerged.select('circle.timeline-event')
            .attr('display', d => hasSpan(d) ? 'none' : null);

        // Spans only for span events
        groupsMerged.select('rect.timeline-span')
            .attr('display', d => hasSpan(d) ? null : 'none')
            .attr('fill', d => colorScale(d.category || 'Unknown'))
            .attr('stroke', '#fff')
            .attr('stroke-width', 1)
            .attr('x', d => {
                const sx = getStartX(d, scale);
                const ex = getEndX(d, scale);
                if (sx === null || ex === null) return 0;
                return Math.min(sx, ex);
            })
            .attr('width', d => {
                const sx = getStartX(d, scale);
                const ex = getEndX(d, scale);
                if (sx === null || ex === null) return 0;
                const w = Math.abs(ex - sx);
                return Math.max(3, w); // keep tiny spans visible
            });

        // Hit area should cover the bar if it's a span; otherwise keep it around the dot.
        groupsMerged.select('rect.event-hit-area')
            .attr('x', d => {
                if (!hasSpan(d)) return -18;
                const sx = getStartX(d, scale);
                const ex = getEndX(d, scale);
                if (sx === null || ex === null) return -18;
                return Math.min(sx, ex) - 8;
            })
            .attr('width', d => {
                if (!hasSpan(d)) return 36;
                const sx = getStartX(d, scale);
                const ex = getEndX(d, scale);
                if (sx === null || ex === null) return 36;
                return Math.max(36, Math.abs(ex - sx) + 16);
            });

        // Labels: for span, center label on midpoint; dot stays centered via group translate.
        groupsMerged.select('text.event-label')
            .attr('x', d => {
                if (!hasSpan(d)) return 0;
                const sx = getStartX(d, scale);
                const ex = getEndX(d, scale);
                if (sx === null || ex === null) return 0;
                return (sx + ex) / 2;
            });
    }

    applyPositions(xScale);

    // Update dot colors if categories change
    groupsMerged.select('circle.timeline-event')
        .attr('fill', d => colorScale(d.category || 'Unknown'));

    // Apply zoom-dependent label opacity on render
    const labelOpacity = getLabelOpacityForZoom(currentZoomK);
    groupsMerged.select('text.event-label')
        .style('opacity', labelOpacity);

    // Apply viewport-fraction-based opacity on render
    const viewSpanYears = getViewportSpanYears(xScale);
    groupsMerged.select('rect.timeline-span')
        .style('opacity', d => getOpacityForEventInViewport(d, viewSpanYears));
    groupsMerged.select('circle.timeline-event')
        .style('opacity', d => getOpacityForEventInViewport(d, viewSpanYears));

    renderLegend();
}

function renderLegend() {
    console.log('[renderLegend] Starting legend render');
    const legendEl = document.getElementById('timeline-legend');
    if (!legendEl) {
        console.error('[renderLegend] Legend element #timeline-legend not found in DOM');
        return;
    }

    console.log('[renderLegend] filteredEvents.length:', filteredEvents.length);

    // Get categories from currently rendered events (viewport-based)
    const categoryCounts = new Map();
    for (const e of filteredEvents) {
        const cat = e.category || 'Unknown';
        categoryCounts.set(cat, (categoryCounts.get(cat) || 0) + 1);
    }

    console.log('[renderLegend] Category counts:', Object.fromEntries(categoryCounts));
    console.log('[renderLegend] Total unique categories:', categoryCounts.size);

    // Sort by count (descending) and take top 12
    const items = Array.from(categoryCounts.entries())
        .sort((a, b) => b[1] - a[1])  // Sort by count descending
        .slice(0, 12)
        .map(([cat, count]) => cat);  // Extract just the category names

    console.log('[renderLegend] Top 12 categories:', items);

    if (items.length === 0) {
        console.warn('[renderLegend] No categories to display');
        legendEl.innerHTML = '<div class="legend-empty">No events in view</div>';
        legendEl.style.display = 'block';  // Ensure it's visible even when empty
        return;
    }

    // Simple, DOM-based legend rendering (kept out of the zoomable SVG).
    const shapeKeyHtml = `
        <div class="legend-shape-key">
            <span class="legend-shape"><span class="legend-dot"></span><span>Moment</span></span>
            <span class="legend-shape"><span class="legend-span"></span><span>Span</span></span>
        </div>
    `;

    const rowsHtml = items
        .map(cat => {
            const c = colorScale(cat);
            const safeCat = String(cat)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
            return `
                <div class="legend-swatch" style="background:${c}"></div>
                <div class="legend-label" title="${safeCat}">${safeCat}</div>
            `;
        })
        .join('');

    legendEl.innerHTML = `${shapeKeyHtml}<div class="legend-grid">${rowsHtml}</div>`;
    legendEl.style.display = 'block';  // Ensure it's visible
    console.log('[renderLegend] Legend HTML updated successfully with', items.length, 'categories');
}

// Zoom handler
function zoomed(event) {
    currentZoomK = event.transform.k;
    currentTransform = event.transform;
    const newXScale = event.transform.rescaleX(xScale);
    currentViewportDomain = getViewportDomain(newXScale);
    
    svg.select('.x-axis').call(xAxis.scale(newXScale));
    
    // Use helpers from updateTimelineMarkers if available (after viewport mode enabled)
    const helpers = window._timelineHelpers;
    if (helpers) {
        // Viewport mode: reapply positions with new scale, then debounce reload
        helpers.applyPositions(newXScale);
        
        // Debounce viewport reload
        if (viewportReloadTimeout) {
            clearTimeout(viewportReloadTimeout);
        }
        viewportReloadTimeout = setTimeout(() => {
            const currentCategory = document.getElementById('category-select').value || null;
            loadEventsInViewport(currentCategory);
        }, 300);
        
        return;
    }
    
    // Legacy mode (full dataset): update positions directly
    const groups = svg.selectAll('.event-group');

    function hasSpan(d) {
        return d.end_year !== null && d.end_year !== undefined;
    }

    function toYearNumber(year, isBc, month = null, day = null) {
        if (year === null || year === undefined) return null;
        
        let fractionalYear = isBc ? -year : year;
        
        // Add month and day precision if available
        if (month !== null && month !== undefined) {
            // Days in each month (non-leap year approximation)
            const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
            
            // Calculate day of year
            let dayOfYear = 0;
            for (let i = 0; i < month - 1; i++) {
                dayOfYear += daysInMonth[i];
            }
            if (day !== null && day !== undefined) {
                dayOfYear += day;
            } else {
                // If only month is specified, use middle of month
                dayOfYear += Math.floor(daysInMonth[month - 1] / 2);
            }
            
            // Add fractional year (approximate 365 days per year)
            // For BC dates: -44 BC is represented as -44, January 1 should be closer to -43 (less negative)
            // For AD dates: 44 AD is represented as 44, January 1 should be closer to 44 (start of year)
            // In both cases, we ADD the fraction to move forward through the year
            const yearFraction = dayOfYear / 365.0;
            fractionalYear += yearFraction;
        }
        
        return fractionalYear;
    }

    function getStartX(d, scale) {
        const n = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
        return n === null ? null : scale(n);
    }

    function getEndX(d, scale) {
        if (!hasSpan(d)) return null;
        
        // Check if this is a single-day event (same year, month, and day)
        const isSingleDay = d.start_year === d.end_year &&
                           d.start_month === d.end_month &&
                           d.start_day === d.end_day &&
                           d.start_day !== null && d.start_day !== undefined;
        
        if (isSingleDay) {
            // For single-day events, add 1 day to make them span the full day
            const startN = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
            if (startN === null) return null;
            return scale(startN + (1 / 365.0)); // Add 1 day
        }
        
        const n = toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day);
        return n === null ? null : scale(n);
    }

    // Recompute sublane assignment on zoom to keep it stable with the current filtered set.
    const data = groups.data();
    const sublaneById = new Map();

    function getNumericSpan(d) {
        const s = toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
        const e = hasSpan(d) ? toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day) : s;
        if (s === null || e === null) return null;
        return { start: Math.min(s, e), end: Math.max(s, e) };
    }

    // Sort all events globally by start time
    const intervals = data
        .map(d => ({ d, span: getNumericSpan(d) }))
        .filter(x => x.span !== null)
        .sort((a, b) => {
            const aSpan = hasSpan(a.d) ? 0 : 1;
            const bSpan = hasSpan(b.d) ? 0 : 1;
            if (aSpan !== bSpan) return aSpan - bSpan;
            if (a.span.start !== b.span.start) return a.span.start - b.span.start;
            return a.span.end - b.span.end;
        });

    // Pack all events into lanes globally
    const laneEnds = [];
    for (const { d, span } of intervals) {
        let placed = false;
        for (let i = 0; i < laneEnds.length; i++) {
            if (span.start > laneEnds[i]) {
                sublaneById.set(d.id, i);
                laneEnds[i] = span.end;
                placed = true;
                break;
            }
        }
        if (!placed) {
            const i = laneEnds.length;
            sublaneById.set(d.id, i);
            laneEnds.push(span.end);
        }
    }

    const totalLanes = laneEnds.length || 1;

    function getYForEvent(d) {
        const container = document.getElementById('timeline-container');
        const height = container.clientHeight;
        const availableHeight = height - margin.top - margin.bottom;
        
        const sublaneIdx = sublaneById.get(d.id) || 0;
        
        // Limit visible lanes to prevent overcrowding
        const maxVisibleLanes = Math.min(20, totalLanes);
        const clampedIdx = Math.min(sublaneIdx, maxVisibleLanes - 1);
        
        // Distribute events across available vertical space
        const laneHeight = availableHeight / maxVisibleLanes;
        return margin.top + (clampedIdx + 0.5) * laneHeight;
    }

    groups.attr('transform', d => {
        const y = getYForEvent(d);
        if (hasSpan(d)) return `translate(0, ${y})`;
        const x = getStartX(d, newXScale) ?? 0;
        return `translate(${x}, ${y})`;
    });

    groups.select('rect.timeline-span')
        .attr('x', d => {
            const sx = getStartX(d, newXScale);
            const ex = getEndX(d, newXScale);
            if (sx === null || ex === null) return 0;
            return Math.min(sx, ex);
        })
        .attr('width', d => {
            const sx = getStartX(d, newXScale);
            const ex = getEndX(d, newXScale);
            if (sx === null || ex === null) return 0;
            return Math.max(3, Math.abs(ex - sx));
        });

    groups.select('rect.event-hit-area')
        .attr('x', d => {
            if (!hasSpan(d)) return -18;
            const sx = getStartX(d, newXScale);
            const ex = getEndX(d, newXScale);
            if (sx === null || ex === null) return -18;
            return Math.min(sx, ex) - 8;
        })
        .attr('width', d => {
            if (!hasSpan(d)) return 36;
            const sx = getStartX(d, newXScale);
            const ex = getEndX(d, newXScale);
            if (sx === null || ex === null) return 36;
            return Math.max(36, Math.abs(ex - sx) + 16);
        });

    groups.select('text.event-label')
        .attr('x', d => {
            if (!hasSpan(d)) return 0;
            const sx = getStartX(d, newXScale);
            const ex = getEndX(d, newXScale);
            if (sx === null || ex === null) return 0;
            return (sx + ex) / 2;
        });

    // Update label opacity based on zoom
    const labelOpacity = getLabelOpacityForZoom(currentZoomK);
    svg.selectAll('.event-group text.event-label')
        .style('opacity', labelOpacity);

    // Update spans/dots opacity based on how much of the visible window they occupy.
    const viewSpanYears = getViewportSpanYears(newXScale);
    svg.selectAll('.event-group rect.timeline-span')
        .style('opacity', d => getOpacityForEventInViewport(d, viewSpanYears));
    svg.selectAll('.event-group circle.timeline-event')
        .style('opacity', d => getOpacityForEventInViewport(d, viewSpanYears));
}

// Reset zoom
function resetZoom() {
    svg.transition()
        .duration(750)
        .call(zoom.transform, d3.zoomIdentity);
}

// Toggle fullscreen mode
function toggleFullscreen() {
    const body = document.body;
    const button = document.getElementById('fullscreen-btn');
    
    body.classList.toggle('fullscreen');
    
    if (body.classList.contains('fullscreen')) {
        button.textContent = 'Exit Fullscreen';
    } else {
        button.textContent = 'Fullscreen';
    }
    
    // Reinitialize timeline with new dimensions
    // Clear the existing SVG and rebuild
    d3.select('#timeline').selectAll('*').remove();
    initializeTimeline();
    renderTimeline();
}

// Handle search
async function handleSearch() {
    const query = document.getElementById('search-input').value.trim();
    
    if (query.length < 3) {
        showError('Please enter at least 3 characters to search');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}&limit=100`);
        filteredEvents = await response.json();
        
        updateStats();
        renderTimeline();
    } catch (error) {
        console.error('Error searching events:', error);
        showError('Search failed. Please try again.');
    }
}

// Handle category filter
function handleCategoryFilter(event) {
    const category = event.target.value;
    
    if (category) {
        loadEvents(category);
    } else {
        loadEvents();
    }
}

// Show event details
function showEventDetails(event) {
    selectedEvent = event;
    
    document.getElementById('event-title').textContent = event.title;
    document.getElementById('event-period').textContent = event.display_year || 'Unknown';
    document.getElementById('event-category').textContent = event.category || 'Uncategorized';
    document.getElementById('event-description').textContent = event.description || 'No description available.';
    
    const wikipediaLink = document.getElementById('event-wikipedia-link');
    if (event.wikipedia_url) {
        wikipediaLink.href = event.wikipedia_url;
        wikipediaLink.style.display = 'inline-block';
    } else {
        wikipediaLink.style.display = 'none';
    }
    
    document.getElementById('event-details').classList.remove('hidden');

    // Debug panel (expandable): fetch extraction-debug lazily.
    resetEventDebugUI();
    loadEventExtractionDebug(event.id);
    
    // Highlight selected event
    svg.selectAll('.event-group')
        .classed('is-selected', d => d.id === event.id);
}

// Close event details
function closeEventDetails() {
    document.getElementById('event-details').classList.add('hidden');
    selectedEvent = null;

    resetEventDebugUI();
    
    // Remove highlight
    svg.selectAll('.event-group')
        .classed('is-selected', false);
}

function resetEventDebugUI() {
    const details = document.getElementById('event-debug-details');
    if (!details) return;

    // Keep expanded/collapsed state sticky across events? For now, collapse on close.
    details.open = false;

    const loading = document.getElementById('event-debug-loading');
    const error = document.getElementById('event-debug-error');
    const dl = document.getElementById('event-debug-dl');
    const strat = document.getElementById('event-debug-strategy');
    const start = document.getElementById('event-debug-start');
    const startDetails = document.getElementById('event-debug-start-details');
    const end = document.getElementById('event-debug-end');
    const endDetails = document.getElementById('event-debug-end-details');
    const weight = document.getElementById('event-debug-weight');

    if (loading) loading.classList.add('hidden');
    if (error) {
        error.classList.add('hidden');
        error.textContent = '';
    }
    if (dl) dl.classList.add('hidden');
    if (strat) strat.textContent = '-';
    if (start) start.textContent = '-';
    if (startDetails) startDetails.textContent = '-';
    if (end) end.textContent = '-';
    if (endDetails) endDetails.textContent = '-';
    if (weight) weight.textContent = '-';
}

function formatDebugYear(year, isBc) {
    if (year === null || year === undefined) return null;
    const y = Number(year);
    if (!Number.isFinite(y)) return null;
    return isBc ? `${y} BC` : `${y} AD`;
}

async function loadEventExtractionDebug(eventId) {
    const loading = document.getElementById('event-debug-loading');
    const error = document.getElementById('event-debug-error');
    const dl = document.getElementById('event-debug-dl');
    if (!loading || !error || !dl) return;

    loading.classList.remove('hidden');

    try {
        const resp = await fetch(`${API_URL}/events/${eventId}/extraction-debug`);
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`);
        }
        const dbg = await resp.json();

        // If user clicked a different event while request was in-flight, ignore.
        if (!selectedEvent || selectedEvent.id !== eventId) return;

        const strat = document.getElementById('event-debug-strategy');
        const matchType = document.getElementById('event-debug-match-type');
        const start = document.getElementById('event-debug-start');
        const startDetails = document.getElementById('event-debug-start-details');
        const end = document.getElementById('event-debug-end');
        const endDetails = document.getElementById('event-debug-end-details');
        const weight = document.getElementById('event-debug-weight');

        if (strat) strat.textContent = dbg.extraction_method || '-';
        if (matchType) matchType.textContent = dbg.span_match_notes || '-';

        const startFmt = formatDebugYear(dbg.chosen_start_year, dbg.chosen_is_bc_start);
        const endFmt = formatDebugYear(dbg.chosen_end_year, dbg.chosen_is_bc_end);
        if (start) start.textContent = startFmt || '-';
        if (end) end.textContent = endFmt || '-';

        // Show month/day details from debug table
        if (startDetails) {
            const month = dbg.chosen_start_month;
            const day = dbg.chosen_start_day;
            if (month && day) {
                const monthName = new Date(2000, month - 1, 1).toLocaleString('en-US', { month: 'long' });
                startDetails.textContent = `${monthName} ${day}`;
            } else if (month) {
                const monthName = new Date(2000, month - 1, 1).toLocaleString('en-US', { month: 'long' });
                startDetails.textContent = monthName;
            } else {
                startDetails.textContent = '-';
            }
        }

        if (endDetails) {
            const month = dbg.chosen_end_month;
            const day = dbg.chosen_end_day;
            if (month && day) {
                const monthName = new Date(2000, month - 1, 1).toLocaleString('en-US', { month: 'long' });
                endDetails.textContent = `${monthName} ${day}`;
            } else if (month) {
                const monthName = new Date(2000, month - 1, 1).toLocaleString('en-US', { month: 'long' });
                endDetails.textContent = monthName;
            } else {
                endDetails.textContent = '-';
            }
        }

        // Prefer debug table field; fall back to the event row's weight.
        const w = (dbg.chosen_weight_days !== null && dbg.chosen_weight_days !== undefined)
            ? dbg.chosen_weight_days
            : dbg.event_weight;
        if (weight) weight.textContent = (w === null || w === undefined) ? '-' : String(w);

        loading.classList.add('hidden');
        dl.classList.remove('hidden');
    } catch (e) {
        if (!selectedEvent || selectedEvent.id !== eventId) return;
        loading.classList.add('hidden');
        error.textContent = `No extraction debug available (${String(e)})`;
        error.classList.remove('hidden');
        dl.classList.add('hidden');
    }
}

// Show error message
function showError(message) {
    const container = document.getElementById('timeline-container');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    container.insertBefore(errorDiv, container.firstChild);
    
    setTimeout(() => errorDiv.remove(), 5000);
}

// Handle window resize
window.addEventListener('resize', () => {
    console.log('[resize] Window resized, reinitializing timeline');
    
    // Save the current domain before reinitializing
    const currentDomain = xScale ? xScale.domain() : null;
    const currentTransformState = currentTransform;
    
    initializeTimeline();
    
    // Restore the domain if we had one
    if (currentDomain) {
        xScale.domain(currentDomain);
        svg.select('.x-axis').call(xAxis);
    }
    
    // Restore the transform state
    if (currentTransformState) {
        currentTransform = currentTransformState;
    }
    
    // Reload viewport with current state
    if (renderedEventIds.size > 0) {
        // We're in viewport mode, reload the viewport
        loadEventsInViewport();
    } else {
        // Fallback to full render if viewport mode isn't active yet
        renderTimeline();
    }
});
