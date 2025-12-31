/**
 * Packing Module
 * 
 * Handles lane assignment algorithm for timeline events.
 * Ensures no horizontal collisions within lanes.
 */

class TimelinePacking {
    constructor(orchestrator) {
        this.orchestrator = orchestrator;
        this.globalLaneAssignments = new Map(); // eventId -> laneIndex (cache across viewport changes)
        this.globalTotalLanes = 1;
        
        // Subscribe to events and scale changes
        this.orchestrator.subscribe('events', (events) => this.packEvents(events));
        this.orchestrator.subscribe('scale', (scale) => this.repackWithScale(scale));
        this.orchestrator.subscribe('availableLanesChanged', (lanes) => {
            console.log('[Packing] Available lanes changed to', lanes, '- repacking');
            this.repackWithScale(this.orchestrator.getScale());
        });
    }
    
    /**
     * Pack events into lanes
     */
    packEvents(events, scale = null) {
        console.log('[Packing] packEvents called with', events?.length, 'events, scale:', scale ? 'provided' : 'will fetch');
        
        const currentScale = scale || this.orchestrator.getScale();
        if (!currentScale) {
            console.warn('[Packing] No scale available yet - cannot pack events');
            return;
        }
        
        console.log('[Packing] Using scale, domain:', currentScale.domain());
        
        const maxLanes = this.orchestrator.getAvailableLanes();
        console.log('[Packing] Available lanes:', maxLanes);
        
        const result = this.calculateLanes(events, currentScale, maxLanes);
        
        console.log('[Packing] Calculation complete:', result.sublaneById.size, 'placed,', result.skippedEvents.length, 'skipped');
        
        // Update orchestrator
        this.orchestrator.setLaneAssignments(
            result.sublaneById,
            result.totalLanes,
            result.skippedEvents
        );
        
        console.log('[Packing] Packed', result.sublaneById.size, 'events into', result.totalLanes, 'lanes');
        if (result.skippedEvents.length > 0) {
            console.log('[Packing] Skipped', result.skippedEvents.length, 'events');
        }
    }
    
    /**
     * Repack with new scale (zoom/pan)
     */
    repackWithScale(scale) {
        const events = this.orchestrator.getEvents();
        if (events.length > 0) {
            this.packEvents(events, scale);
        }
    }
    
    /**
     * Calculate lane assignments using bounding box collision detection
     */
    calculateLanes(renderData, scale, maxLanes = Infinity) {
        const sublaneById = new Map();
        const skippedEvents = [];
        
        // Sort events by start time for left-to-right processing
        const intervals = renderData
            .map(d => ({ d, span: this.getNumericSpan(d) }))
            .filter(x => x.span !== null)
            .sort((a, b) => {
                if (a.span.start !== b.span.start) return a.span.start - b.span.start;
                return a.span.end - b.span.end;
            });
        
        // Track what's in each lane: array of {eventId, bbox} objects
        const lanes = [];
        
        for (const { d, span } of intervals) {
            // Calculate bounding box
            const bbox = this.calculateBoundingBox(d, span, scale);
            
            // Convert to global X coordinates for collision detection
            let globalBbox;
            if (!this.hasSpan(d)) {
                // Point event: group is at (eventX, y), so offset the local bbox
                const eventX = scale(span.start);
                globalBbox = {
                    left: eventX + bbox.left,
                    right: eventX + bbox.right
                };
            } else {
                // Span event: bbox is already in global coordinates
                globalBbox = {
                    left: bbox.left,
                    right: bbox.right
                };
            }
            
            // Try to place in existing lanes (prefer cached lane if available)
            let placed = false;
            const cachedLane = this.globalLaneAssignments.get(d.id);
            const lanesToTry = [];
            
            // Build priority list: cached lane first, then 0 to maxLanes
            if (cachedLane !== undefined && cachedLane < maxLanes) {
                lanesToTry.push(cachedLane);
            }
            for (let i = 0; i < maxLanes; i++) {
                if (i !== cachedLane) {
                    lanesToTry.push(i);
                }
            }
            
            for (const laneIdx of lanesToTry) {
                // Ensure lane exists
                if (!lanes[laneIdx]) {
                    lanes[laneIdx] = [];
                }
                
                // Check for HORIZONTAL collisions only
                const hasCollision = lanes[laneIdx].some(existing => {
                    return this.boxesOverlapHorizontally(globalBbox, existing.bbox);
                });
                
                if (!hasCollision) {
                    // Place event in this lane
                    sublaneById.set(d.id, laneIdx);
                    lanes[laneIdx].push({ eventId: d.id, bbox: globalBbox });
                    this.globalLaneAssignments.set(d.id, laneIdx);
                    placed = true;
                    break;
                }
            }
            
            if (!placed) {
                skippedEvents.push(d.id);
            }
        }
        
        const totalLanes = lanes.length || 1;
        this.globalTotalLanes = Math.max(this.globalTotalLanes, totalLanes);
        
        return { sublaneById, totalLanes: this.globalTotalLanes, skippedEvents };
    }
    
    /**
     * Helper: Check if event has a span (vs point in time)
     */
    hasSpan(d) {
        return d.end_year !== null && d.end_year !== undefined;
    }
    
    /**
     * Helper: Convert date to numeric year
     */
    toYearNumber(year, isBc, month = null, day = null) {
        if (year === null || year === undefined) return null;
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
    }
    
    /**
     * Helper: Get numeric span for an event
     */
    getNumericSpan(d) {
        const s = this.toYearNumber(d.start_year, d.is_bc_start, d.start_month, d.start_day);
        const e = this.hasSpan(d) ? this.toYearNumber(d.end_year, d.is_bc_end, d.end_month, d.end_day) : s;
        if (s === null || e === null) return null;
        return { start: Math.min(s, e), end: Math.max(s, e) };
    }
    
    /**
     * Helper: Estimate text width
     */
    estimateTextWidth(text) {
        const avgCharWidth = 8;
        return (text || '').length * avgCharWidth;
    }
    
    /**
     * Helper: Extract first sentence from text
     */
    firstSentence(text) {
        if (!text) return '';
        let s = String(text).replace(/\s+/g, ' ').trim();
        if (!s) return '';
        const datePattern = /^(\d{1,4}(\s?BC|\s?AD)?[\s:–-]+)/i;
        s = s.replace(datePattern, '');
        const match = s.match(/^[^.!?]+[.!?]/);
        if (match) {
            s = match[0].trim();
        }
        return s.length > 30 ? s.substring(0, 30) + '...' : s;
    }
    
    /**
     * Helper: Calculate bounding box for collision detection
     */
    calculateBoundingBox(d, span, scale) {
        const sx = scale(span.start);
        const ex = this.hasSpan(d) ? scale(span.end) : sx;
        
        // Bar dimensions
        let barLeft, barRight;
        
        if (!this.hasSpan(d)) {
            // Point event: circle (r=6) in local coordinates
            barLeft = -6;
            barRight = 6;
        } else {
            // Span event: rectangle in global coordinates
            const minWidth = 12;
            const actualWidth = Math.abs(ex - sx);
            const leftmost = Math.min(sx, ex);
            
            let barX;
            if (actualWidth < minWidth) {
                barX = leftmost - (minWidth - actualWidth) / 2;
            } else {
                barX = leftmost;
            }
            
            const barWidth = Math.max(minWidth, actualWidth);
            barLeft = barX - 8;
            barRight = barX + barWidth + 8;
        }
        
        // Label dimensions
        const labelText = this.firstSentence(d.title);
        const labelWidth = this.estimateTextWidth(labelText);
        
        let labelCenterX;
        if (!this.hasSpan(d)) {
            labelCenterX = 0; // Local coordinates
        } else {
            labelCenterX = (sx + ex) / 2; // Global coordinates
        }
        
        const labelLeft = labelCenterX - labelWidth / 2;
        const labelRight = labelCenterX + labelWidth / 2;
        
        // Bounding box with padding
        const horizontalPadding = 8;
        
        return {
            left: Math.min(barLeft, labelLeft) - horizontalPadding,
            right: Math.max(barRight, labelRight) + horizontalPadding
        };
    }
    
    /**
     * Helper: Check if two bounding boxes overlap horizontally
     */
    boxesOverlapHorizontally(box1, box2) {
        return !(box1.right <= box2.left || box2.right <= box1.left);
    }
}

// Initialize packing module when orchestrator is ready
window.addEventListener('DOMContentLoaded', () => {
    window.timelinePacking = new TimelinePacking(window.timelineOrchestrator);
});
