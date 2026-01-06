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
        this.lastTransformK = 1; // Track zoom level to detect zoom vs pan
        this.currentViewportDomain = null; // Track current viewport [start, end]
        this.frozenEventIds = new Set(); // Track events that have been in center bins during current pan session
        
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
        
        // Detect if this is a pan (domain changed but scale factor didn't)
        const viewport = this.orchestrator.getState()?.viewport;
        const newDomain = currentScale.domain();
        const isPan = viewport && viewport.transform && 
                      Math.abs(viewport.transform.k - this.lastTransformK) < 0.001;
        
        if (viewport?.transform) {
            this.lastTransformK = viewport.transform.k;
        }
        
        this.currentViewportDomain = newDomain;
        
        console.log('[Packing] Operation type:', isPan ? 'PAN' : 'ZOOM');
        
        const maxLanes = this.orchestrator.getAvailableLanes();
        console.log('[Packing] Available lanes:', maxLanes);
        
        const result = this.calculateLanes(events, currentScale, maxLanes, isPan);
        
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
     * 
     * Events are processed by bin in a specific order to ensure viewport events
     * are packed first (preventing collisions), followed by buffer events:
     * 1. Center bins (7,8,6,9,5) - viewport events
     * 2. Right bins (4,3,2,1,0) - right buffer
     * 3. Left bins (10,11,12,13,14) - left buffer
     */
    calculateLanes(renderData, scale, maxLanes = Infinity, isPan = false) {
        const sublaneById = new Map();
        const skippedEvents = [];
        
        console.log(`[Packing] ========================================`);
        console.log(`[Packing] DEBUG: calculateLanes called`);
        console.log(`[Packing] DEBUG: isPan=${isPan}, events=${renderData.length}, maxLanes=${maxLanes}`);
        console.log(`[Packing] ========================================`);
        
        // Get viewport bounds for sticky lane logic
        const viewportBounds = this.currentViewportDomain ? {
            start: this.currentViewportDomain[0],
            end: this.currentViewportDomain[1]
        } : null;
        
        // Define bin processing order (center-out)
        const binOrder = [7, 8, 6, 9, 5, 4, 3, 2, 1, 0, 10, 11, 12, 13, 14];
        
        // Create a mapping from bin_num to sort priority
        const binPriority = new Map();
        binOrder.forEach((binNum, index) => {
            binPriority.set(binNum, index);
        });
        
        // Process events with span information
        const intervals = renderData
            .map(d => ({ d, span: this.getNumericSpan(d) }))
            .filter(x => x.span !== null);
        
        // Sort by bin order first, then by weight (higher weight = more important), then by time
        intervals.sort((a, b) => {
            const aBin = a.d.bin_num !== undefined ? a.d.bin_num : 999; // Events without bin go last
            const bBin = b.d.bin_num !== undefined ? b.d.bin_num : 999;
            
            const aPriority = binPriority.get(aBin) !== undefined ? binPriority.get(aBin) : 999;
            const bPriority = binPriority.get(bBin) !== undefined ? binPriority.get(bBin) : 999;
            
            // Primary sort: by bin priority (center bins first)
            if (aPriority !== bPriority) {
                return aPriority - bPriority;
            }
            
            // Secondary sort: by weight (DESCENDING - higher weight first)
            // Events with higher weight (more days) are more important and get priority placement
            const aWeight = a.d.weight !== undefined ? a.d.weight : 0;
            const bWeight = b.d.weight !== undefined ? b.d.weight : 0;
            if (aWeight !== bWeight) {
                return bWeight - aWeight; // Descending: higher weight first
            }
            
            // Tertiary sort: by start time within bin
            if (a.span.start !== b.span.start) {
                return a.span.start - b.span.start;
            }
            
            // Quaternary sort: by end time
            return a.span.end - b.span.end;
        });
        
        console.log('[Packing] Processing', intervals.length, 'events in bin order:', binOrder);
        
        // During PAN: Log how many events have cached lanes (will be frozen)
        if (isPan) {
            const eventsWithCache = intervals.filter(x => this.globalLaneAssignments.has(x.d.id)).length;
            console.log(`[Packing] DEBUG: During PAN - ${eventsWithCache} events have cached lanes (will be frozen)`);
        }
        
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
            
            // During PAN: ALL events with cached lanes are frozen (keep their lanes)
            // This prevents any re-packing during pan - events stay stable
            // Only new events (without cached lanes) get packed dynamically
            const shouldFreeze = isPan && cachedLane !== undefined;
            
            if (shouldFreeze) {
                console.log(`[Packing] DEBUG: FREEZING event ${d.id} (bin ${d.bin_num}) in lane ${cachedLane}`);
            }
            
            const lanesToTry = [];
            
            if (shouldFreeze) {
                // During pan, frozen events ONLY try their cached lane, no alternatives
                lanesToTry.push(cachedLane);
            } else {
                // Build priority list: cached lane first, then 0 to maxLanes
                if (cachedLane !== undefined && cachedLane < maxLanes) {
                    lanesToTry.push(cachedLane);
                }
                for (let i = 0; i < maxLanes; i++) {
                    if (i !== cachedLane) {
                        lanesToTry.push(i);
                    }
                }
            }
            
            for (const laneIdx of lanesToTry) {
                // Ensure lane exists
                if (!lanes[laneIdx]) {
                    lanes[laneIdx] = [];
                }
                
                // Check for HORIZONTAL collisions
                const hasCollision = lanes[laneIdx].some(existing => {
                    return this.boxesOverlapHorizontally(globalBbox, existing.bbox);
                });
                
                if (!hasCollision) {
                    // Place event in this lane
                    sublaneById.set(d.id, laneIdx);
                    lanes[laneIdx].push({ eventId: d.id, bbox: globalBbox });
                    this.globalLaneAssignments.set(d.id, laneIdx);
                    placed = true;
                    
                    if (shouldFreeze && laneIdx !== cachedLane) {
                        console.log(`[Packing] NOTE: Frozen event ${d.id} moved from lane ${cachedLane} to ${laneIdx} to avoid collision`);
                    }
                    break;
                }
            }
            
            if (!placed) {
                // Event couldn't find a collision-free lane
                if (shouldFreeze) {
                    console.log(`[Packing] Event ${d.id} (frozen, was in lane ${cachedLane}) couldn't find collision-free placement - skipping`);
                }
                skippedEvents.push(d.id);
            }
        }
        
        const totalLanes = lanes.length || 1;
        this.globalTotalLanes = Math.max(this.globalTotalLanes, totalLanes);
        
        // Clean up globalLaneAssignments - remove stale IDs that aren't in sublaneById
        // This prevents accumulation of old event IDs from previous packs
        const currentEventIds = new Set(sublaneById.keys());
        for (const eventId of this.globalLaneAssignments.keys()) {
            if (!currentEventIds.has(eventId)) {
                this.globalLaneAssignments.delete(eventId);
            }
        }
        
        return { sublaneById, totalLanes: this.globalTotalLanes, skippedEvents };
    }
    
    /**
     * Helper: Check if event has a span (vs point in time)
     */
    hasSpan(d) {
        return d.end_year !== null && d.end_year !== undefined;
    }
    
    /**
     * Helper: Check if event is fully within viewport bounds
     * For stretch goal: event must be completely visible
     */
    isEventFullyInViewport(span, viewportBounds) {
        if (!viewportBounds) return false;
        
        // Event is fully in viewport if both start and end are within bounds
        return span.start >= viewportBounds.start && 
               span.end <= viewportBounds.end;
    }
    
    /**
     * Helper: Check if event midpoint is within viewport bounds
     * For basic goal: event stays in lane until midpoint leaves viewport
     */
    isEventMidpointInViewport(span, viewportBounds) {
        if (!viewportBounds) return false;
        
        const midpoint = (span.start + span.end) / 2;
        return midpoint >= viewportBounds.start && 
               midpoint <= viewportBounds.end;
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
