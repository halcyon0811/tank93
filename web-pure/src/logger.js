/**
 * Tank93 Web-Pure Logger - JS mirror of Python game/debug_logger.py
 * Shared taxonomy: docs/LOG_EVENT_SCHEMA.md
 * 
 * Zero external deps, ring buffer 1000 events, localStorage 50KB circular, ?debug=1 overlay
 * <0.1ms per log, never crashes game (all wrapped try/catch)
 * 
 * API mirrors Python:
 *   logger.log_event(tag, message, level, extra, withStack)
 *   logger.log_state(oldState, newState, reason, extra)
 *   logger.log_gameplay(eventType, levelIdx, playerId, data)
 *   logger.log_crash(where, error)
 *   logger.log_input(type, device, code, value, mappedAction)
 *   plus helpers: log_network, log_steel, log_edge, log_weapon, log_map, log_boss, log_perf_event
 *   query, tail, stats, report, export, clear
 */

const SCHEMA_VERSION = "1.0.0";
const MAX_EVENTS = 1000;
const MAX_GAMEPLAY = 500;
const MAX_STATE_CHANGES = 200;
const MAX_INPUTS = 300;
const MAX_EXCEPTIONS = 100;
const MAX_PERF = 200;
const STORAGE_KEY = "tank93_debug_logs_v1";
const STORAGE_MAX_BYTES = 50 * 1024; // 50KB

function nowISO() {
    try { return new Date().toISOString(); } catch { return Date.now().toString(); }
}

function safeStringify(obj, maxLen = 800) {
    try {
        let s = JSON.stringify(obj);
        if (s && s.length > maxLen) s = s.slice(0, maxLen) + "...(truncated)";
        return s;
    } catch {
        return String(obj).slice(0, maxLen);
    }
}

function getStack() {
    try {
        let e = new Error();
        let stack = e.stack || "";
        // Keep only relevant lines, first 5
        let lines = stack.split("\n").slice(2, 7).join(" | ");
        return lines.slice(0, 500);
    } catch { return ""; }
}

class DebugLoggerJS {
    constructor(opts = {}) {
        this.enabled = true; // always on, but cheap
        this.sessionId = Math.random().toString(36).slice(2, 10) + "-" + Date.now().toString(36);
        this.startTime = Date.now();
        this.events = [];
        this.gameplay = [];
        this.stateChanges = [];
        this.inputs = [];
        this.exceptions = [];
        this.perf = [];

        this.bounceCount = 0;
        this.errorCount = 0;
        this.frameCount = 0;
        this.lastGameState = "menu";

        // Platform info
        this.platform = {
            userAgent: (typeof navigator !== "undefined" ? navigator.userAgent : "node").slice(0, 200),
            url: (typeof location !== "undefined" ? location.href : ""),
            schemaVersion: SCHEMA_VERSION,
            isDebugOverlay: false,
        };

        // Debug overlay flag ?debug=1
        try {
            if (typeof location !== "undefined") {
                const params = new URLSearchParams(location.search);
                this.platform.isDebugOverlay = params.has("debug") || params.get("debug") === "1";
            }
        } catch {}

        // Load previous logs from localStorage for continuity
        this._loadFromStorage();

        // Global error handlers (mirror Python exceptions_log)
        this._installGlobalHandlers();

        // Initial log
        this.log_event("INIT", `JS Logger started session=${this.sessionId} schema=${SCHEMA_VERSION}`, "INFO", {
            platform: this.platform
        });

        // Expose globally for console access like Python debug_query.py
        try {
            if (typeof window !== "undefined") {
                window.tankLogger = this;
                window.logger = this; // shorthand
                console.log(`[Tank93] Logger ready: logger.query({tag:'STATE'}), logger.report(), logger.export(), ?debug=1 for overlay`);
            }
        } catch {}
    }

    _installGlobalHandlers() {
        try {
            if (typeof window === "undefined") return;
            // Capture unhandled errors
            window.addEventListener("error", (e) => {
                try {
                    this.log_crash("window.onerror", e.error || e.message, {
                        filename: e.filename,
                        lineno: e.lineno,
                        colno: e.colno,
                        message: e.message
                    });
                } catch {}
            });
            window.addEventListener("unhandledrejection", (e) => {
                try {
                    this.log_crash("unhandledrejection", e.reason, { reason: String(e.reason).slice(0,500) });
                } catch {}
            });
        } catch {}
    }

    _loadFromStorage() {
        try {
            if (typeof localStorage === "undefined") return;
            let raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return;
            let parsed = JSON.parse(raw);
            if (parsed && Array.isArray(parsed.events)) {
                // Keep last 50 events from previous session as context
                let tail = parsed.events.slice(-30);
                // Mark as previous session
                tail.forEach(ev => ev._fromPrevSession = true);
                this.events = tail;
            }
        } catch {}
    }

    _persist() {
        try {
            if (typeof localStorage === "undefined") return;
            // Throttle: only persist every 50 logs or on error
            if (this.events.length % 50 !== 0 && this.errorCount % 1 !== 0) {
                // still persist on WARN+
                let last = this.events[this.events.length - 1];
                if (last && last.level !== "WARN" && last.level !== "ERROR" && last.level !== "FATAL") return;
            }
            let toStore = {
                sessionId: this.sessionId,
                startTime: this.startTime,
                events: this.events.slice(-100), // last 100 only to stay under 50KB
                stats: this.stats()
            };
            let json = JSON.stringify(toStore);
            if (json.length > STORAGE_MAX_BYTES) {
                // Trim further
                toStore.events = toStore.events.slice(-40);
                json = JSON.stringify(toStore);
            }
            localStorage.setItem(STORAGE_KEY, json);
        } catch {
            // Storage full or disabled - ignore
            try { localStorage.removeItem(STORAGE_KEY); } catch {}
        }
    }

    _pushRing(arr, item, maxLen) {
        arr.push(item);
        if (arr.length > maxLen) arr.shift(); // keep recent
    }

    log_event(tag, message, level = "INFO", extra = null, withStack = false) {
        try {
            if (!this.enabled) return;
            let ev = {
                ts: nowISO(),
                t: Date.now() - this.startTime, // ms since start
                frame: this.frameCount,
                level,
                tag,
                message: String(message).slice(0, 800),
                extra: extra ? safeStringify(extra, 600) : null,
                extraObj: extra,
                stack: withStack ? getStack() : null,
                sessionId: this.sessionId
            };
            this._pushRing(this.events, ev, MAX_EVENTS);
            if (level === "ERROR" || level === "FATAL") this.errorCount++;

            // Count bounces playing->menu
            if (tag === "STATE" && typeof message === "string" && message.includes("playing -> menu")) {
                this.bounceCount++;
            }

            // Console mirror for DEBUG? Only INFO+ to avoid spam, but always for WARN+
            try {
                if (level === "ERROR" || level === "FATAL" || (this.platform.isDebugOverlay && level !== "DEBUG")) {
                    let fn = level === "ERROR" || level === "FATAL" ? console.error : console.warn;
                    fn.call(console, `[${level}] [${tag}] ${message}`, extra || "");
                } else if (level === "INFO" && tag !== "PERF") {
                    // Only log critical tags to console in normal mode to avoid spam
                    if (["STATE","BOSS","STUCK","STEEL","CRASH","INIT"].includes(tag)) {
                        console.log(`[${tag}] ${message}`);
                    }
                }
            } catch {}

            this._persist();
            return ev;
        } catch {
            return null;
        }
    }

    log_state(oldState, newState, reason, extra = null) {
        try {
            let msg = `${oldState} -> ${newState} | reason=${reason}`;
            let ev = {
                ts: nowISO(),
                t: Date.now() - this.startTime,
                oldState,
                newState,
                reason: String(reason).slice(0, 500),
                extra: extra ? safeStringify(extra, 600) : null,
                extraObj: extra,
                sessionId: this.sessionId
            };
            this._pushRing(this.stateChanges, ev, MAX_STATE_CHANGES);
            // Also as generic event with WARN if bounce
            let level = (oldState === "playing" && newState === "menu") ? "WARN" : "INFO";
            this.log_event("STATE", msg, level, extra, level === "WARN");
            this.lastGameState = newState;
            return ev;
        } catch { return null; }
    }

    log_gameplay(eventType, levelIdx = 0, playerId = null, data = null) {
        try {
            let ev = {
                ts: nowISO(),
                t: Date.now() - this.startTime,
                frame: this.frameCount,
                eventType,
                levelIdx,
                playerId,
                data: data ? safeStringify(data, 800) : null,
                dataObj: data,
                sessionId: this.sessionId
            };
            this._pushRing(this.gameplay, ev, MAX_GAMEPLAY);
            // Also mirror important ones as events
            if (["BOSS_ESCAPED","BOSS_RELEASE_TRAPPED","BASE_DESTROYED","STAGE_CLEAR","GAME_OVER","VENOM_SPILLOVER"].includes(eventType)) {
                this.log_event("GAMEPLAY", `${eventType} lvl=${levelIdx} ${safeStringify(data, 300)}`, "INFO", data);
            }
            return ev;
        } catch { return null; }
    }

    log_crash(where, error, extra = null) {
        try {
            let errStr = "";
            let stack = "";
            if (error) {
                if (error instanceof Error) {
                    errStr = error.message;
                    stack = error.stack || "";
                } else {
                    errStr = String(error).slice(0, 800);
                }
            }
            let ev = {
                ts: nowISO(),
                t: Date.now() - this.startTime,
                where: String(where).slice(0, 200),
                error: errStr.slice(0, 800),
                stack: stack.slice(0, 1000),
                extra: extra ? safeStringify(extra, 600) : null,
                sessionId: this.sessionId
            };
            this._pushRing(this.exceptions, ev, MAX_EXCEPTIONS);
            this.log_event("CRASH", `${where}: ${errStr}`, "ERROR", {stack, extra}, true);
            this.errorCount++;
            this._persist();
            return ev;
        } catch { return null; }
    }

    log_input(type, device, code, value, mappedAction = null) {
        try {
            // Throttle: don't log same key repeated within 50ms spam
            let now = Date.now();
            if (this._lastInput && this._lastInput.code === code && (now - this._lastInput.ts) < 50) return;
            this._lastInput = { code, ts: now };
            let ev = {
                ts: nowISO(),
                t: Date.now() - this.startTime,
                inputType: type,
                device,
                code,
                value,
                mappedAction,
                sessionId: this.sessionId
            };
            this._pushRing(this.inputs, ev, MAX_INPUTS);
            return ev;
        } catch { return null; }
    }

    log_perf(fps, dt, enemyCount, bulletCount) {
        try {
            this.frameCount++;
            if (this.frameCount % 30 !== 0) return; // sample every 30 frames
            let ev = {
                ts: nowISO(),
                t: Date.now() - this.startTime,
                frame: this.frameCount,
                fps, dt, enemyCount, bulletCount,
                sessionId: this.sessionId
            };
            this._pushRing(this.perf, ev, MAX_PERF);
            return ev;
        } catch { return null; }
    }

    // Helpers mirroring logger_integration.py safe wrappers
    log_network(eventType, data) { return this.log_gameplay(eventType, 0, null, data); }
    log_steel(eventType, data) { return this.log_gameplay(eventType, data?.levelIdx||0, null, data); }
    log_edge(eventType, data) { return this.log_gameplay(eventType, data?.levelIdx||0, data?.playerId||null, data); }
    log_weapon(eventType, data) { return this.log_gameplay(eventType, data?.levelIdx||0, data?.playerId||null, data); }
    log_map(eventType, data) { return this.log_gameplay(eventType, 0, null, data); }
    log_boss(eventType, data) { return this.log_gameplay(eventType, data?.levelIdx||0, null, data); }
    log_perf_event(eventType, data) { return this.log_gameplay(eventType, 0, null, data); }
    log_hud(eventType, data) { return this.log_gameplay(eventType, 0, null, data); }

    // ---- Query APIs (mirror debug_query.py) ----

    query(filter = {}) {
        try {
            let results = [];
            let { tag, level, eventType, limit = 100, sinceFrame, search } = filter;

            // Search in events
            if (tag || level || search) {
                let evs = this.events.slice().reverse();
                for (let ev of evs) {
                    if (tag && ev.tag !== tag) continue;
                    if (level && ev.level !== level) continue;
                    if (search && !((ev.message||"").includes(search) || (ev.extra||"").includes(search))) continue;
                    if (sinceFrame && ev.frame < sinceFrame) continue;
                    results.push(ev);
                    if (results.length >= limit) break;
                }
            }
            // Search in gameplay by eventType
            if (eventType) {
                let gps = this.gameplay.slice().reverse();
                for (let g of gps) {
                    if (g.eventType !== eventType) continue;
                    results.push(g);
                    if (results.length >= limit) break;
                }
            }
            // General gameplay query
            if (!tag && !eventType && !level && !search) {
                // Return recent mix
                results = [
                    ...this.stateChanges.slice(-20),
                    ...this.gameplay.slice(-20),
                    ...this.events.slice(-limit)
                ].sort((a,b) => (b.t||0)-(a.t||0)).slice(0, limit);
            }
            console.table(results.slice(0, Math.min(20, results.length)));
            console.log(`Query returned ${results.length} (showing first 20) filter=`, filter);
            return results;
        } catch (e) {
            console.error("query failed", e);
            return [];
        }
    }

    tail(lines = 50) {
        try {
            let all = this.events.slice(-lines);
            console.log(`--- Last ${lines} events ---`);
            all.forEach(ev => {
                console.log(`[${ev.level}] [${ev.tag}] f=${ev.frame} ${ev.message}${ev.extra? " "+ev.extra : ""}`);
            });
            return all;
        } catch(e) { console.error(e); return []; }
    }

    stats() {
        try {
            let s = {
                sessionId: this.sessionId,
                uptimeMs: Date.now() - this.startTime,
                uptimeSec: Math.floor((Date.now() - this.startTime)/1000),
                frames: this.frameCount,
                events: this.events.length,
                gameplay: this.gameplay.length,
                stateChanges: this.stateChanges.length,
                inputs: this.inputs.length,
                exceptions: this.exceptions.length,
                perf: this.perf.length,
                bounces: this.bounceCount,
                errors: this.errorCount,
                schema: SCHEMA_VERSION
            };
            console.log("Logger stats:", s);
            return s;
        } catch { return {}; }
    }

    report() {
        try {
            console.log(`\n========== TANK93 JS DEBUG REPORT session=${this.sessionId} ==========`);
            let s = this.stats();
            console.log(`Uptime ${s.uptimeSec}s, frames ${s.frames}, bounces ${s.bounces}, errors ${s.errors}`);

            // Bounces
            let bounces = this.stateChanges.filter(sc => sc.oldState==="playing" && sc.newState==="menu");
            if (bounces.length > 0) {
                console.warn(`--- BOUNCES (playing->menu) ${bounces.length} last ---`);
                bounces.slice(-5).forEach(b => {
                    console.log(`  ${b.ts} frame=${this.events.find(ev=>ev.t===b.t)?.frame} reason=${b.reason}`);
                    // Find breadcrumbs 50 before
                    let idx = this.events.findIndex(ev => Math.abs(ev.t - b.t) < 200);
                    if (idx >= 0) {
                        let start = Math.max(0, idx-50);
                        console.log(`  Breadcrumbs last 50 before bounce:`);
                        this.events.slice(start, idx).slice(-20).forEach(ev=> console.log(`    [${ev.tag}] ${ev.message}`));
                    }
                });
            } else {
                console.log("No bounces detected.");
            }

            // Exceptions
            if (this.exceptions.length > 0) {
                console.error(`--- EXCEPTIONS ${this.exceptions.length} ---`);
                this.exceptions.slice(-5).forEach(ex=> console.error(`  ${ex.where}: ${ex.error}\n  ${ex.stack?.slice(0,300)}`));
            }

            // Stuck
            let stuck = this.gameplay.filter(g=>["EDGE_BLOCK","PLAYER_STUCK","EDGE_AUTO_CLAMP","SLIDE_THROUGH_GAP"].includes(g.eventType));
            if (stuck.length > 0) {
                console.log(`--- STUCK/EDGE ${stuck.length} ---`);
                stuck.slice(-10).forEach(g=> console.log(`  f=${g.frame} ${g.eventType} ${g.data}`));
            }

            // Steel
            let steel = this.gameplay.filter(g=>["STEEL_DESTROY","STEEL_CHIP","BRICK_DESTROY"].includes(g.eventType));
            if (steel.length > 0) {
                console.log(`--- STEEL/BRICK ${steel.length} destroyed/chipped ---`);
                console.log(`  destroyed ${steel.filter(g=>g.eventType==="STEEL_DESTROY").length} steel, ${steel.filter(g=>g.eventType==="BRICK_DESTROY").length} brick`);
            }

            // Weapon
            let weapon = this.gameplay.filter(g=>g.eventType.includes("WEAPON")||g.eventType.includes("PWR_"));
            if (weapon.length > 0) {
                console.log(`--- WEAPON ${weapon.length} ---`);
                weapon.slice(-10).forEach(g=> console.log(`  ${g.eventType} ${g.data}`));
            }

            // Boss
            let boss = this.gameplay.filter(g=>g.eventType.startsWith("BOSS_")||g.eventType.includes("BOSS"));
            if (boss.length > 0) {
                console.log(`--- BOSS ${boss.length} ---`);
                boss.forEach(g=> console.log(`  ${g.eventType} lvl=${g.levelIdx} ${g.data}`));
            }

            // Perf
            if (this.perf.length > 0) {
                let last = this.perf.slice(-20);
                let avgFps = last.reduce((a,b)=>a+b.fps,0)/last.length;
                console.log(`--- PERF avg FPS last 20 samples: ${avgFps.toFixed(1)} ---`);
                if (avgFps < 30) console.warn("LOW FPS detected!");
            }

            // Map
            let maps = this.gameplay.filter(g=>g.eventType.startsWith("MAP_"));
            if (maps.length > 0) {
                console.log(`--- MAP ${maps.length} ---`);
                maps.slice(-10).forEach(g=> console.log(`  ${g.eventType} ${g.data}`));
            }

            // Last events
            console.log(`--- LAST 30 events ---`);
            this.events.slice(-30).forEach(ev=> console.log(`  [${ev.level}] [${ev.tag}] f=${ev.frame||'-'} ${ev.message}`));

            console.log(`========== END REPORT ==========\n`);
            console.log(`Tip: logger.query({tag:'BOSS'}), logger.query({tag:'STATE'}), logger.tail(100), logger.export()`);
            return s;
        } catch (e) {
            console.error("report failed", e);
            return {};
        }
    }

    export() {
        try {
            let data = {
                sessionId: this.sessionId,
                schema: SCHEMA_VERSION,
                startTime: this.startTime,
                exportTime: nowISO(),
                stats: this.stats(),
                events: this.events,
                stateChanges: this.stateChanges,
                gameplay: this.gameplay,
                exceptions: this.exceptions,
                inputs: this.inputs.slice(-100),
                perf: this.perf.slice(-50)
            };
            let json = JSON.stringify(data, null, 2);
            let blob = new Blob([json], {type:"application/json"});
            let url = URL.createObjectURL(blob);
            let a = document.createElement("a");
            a.href = url;
            a.download = `tank93-debug-${this.sessionId}-${new Date().toISOString().slice(0,19)}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            console.log(`Exported debug log ${json.length} bytes`);
            return json;
        } catch (e) {
            console.error("export failed", e);
            return null;
        }
    }

    clear() {
        try {
            this.events = [];
            this.gameplay = [];
            this.stateChanges = [];
            this.inputs = [];
            this.exceptions = [];
            this.perf = [];
            this.bounceCount = 0;
            this.errorCount = 0;
            try { localStorage.removeItem(STORAGE_KEY); } catch {}
            console.log("Logger cleared");
        } catch {}
    }

    // Frame tick for perf
    tick(fps, dt, enemyCount, bulletCount) {
        this.log_perf(fps, dt, enemyCount, bulletCount);
    }
}

// Singleton like Python debug_logger
let debugLoggerJS = null;
try {
    debugLoggerJS = new DebugLoggerJS();
} catch (e) {
    console.error("Failed to init JS logger", e);
    // Fallback no-op logger that won't crash game
    debugLoggerJS = {
        log_event: ()=>{},
        log_state: ()=>{},
        log_gameplay: ()=>{},
        log_crash: ()=>{},
        log_input: ()=>{},
        log_perf: ()=>{},
        log_network: ()=>{},
        log_steel: ()=>{},
        log_edge: ()=>{},
        log_weapon: ()=>{},
        log_map: ()=>{},
        log_boss: ()=>{},
        log_perf_event: ()=>{},
        log_hud: ()=>{},
        query: ()=>[],
        tail: ()=>[],
        stats: ()=>({}),
        report: ()=>{},
        export: ()=>null,
        clear: ()=>{},
        tick: ()=>{}
    };
}

export { DebugLoggerJS, debugLoggerJS, debugLoggerJS as logger, debugLoggerJS as debug_logger };
export default debugLoggerJS;
