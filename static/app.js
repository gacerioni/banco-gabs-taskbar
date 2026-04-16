/**
 * Redis Global Search Taskbar - Frontend
 * Real-time search with autocomplete and typed results
 */

// DOM Elements
const searchInput = document.getElementById('searchInput');
const autocompleteDropdown = document.getElementById('autocompleteDropdown');
const loadingIndicator = document.getElementById('loadingIndicator');
const searchInfo = document.getElementById('searchInfo');
const resultsContainer = document.getElementById('resultsContainer');

// Stats elements
const lastQueryEl = document.getElementById('lastQuery');
const latencyEl = document.getElementById('latency');
const intentEl = document.getElementById('intent');
const resultCountEl = document.getElementById('resultCount');

// State
const CONCIERGE_SESSION_KEY = 'redis_concierge_panel_session_id';

/** Tools exposed to the model (demo reference). */
const DEMO_AGENT_TOOLS = [
    ['search_inventory', 'Hybrid SKU search (+ FT fallback if empty)'],
    ['get_cart', 'Read Redis cart for this session'],
    ['add_to_cart', 'Add line (validates SKU in Redis)'],
    ['set_quantity', 'Set quantity or remove with 0'],
    ['remove_from_cart', 'Remove one cart line'],
    ['empty_cart', 'Clear the cart'],
];

let debounceTimer = null;
let selectedIndex = -1;
let currentResults = [];
let lastQuery = '';
let requestInFlight = false;
let conciergeWelcomed = false;

function getConciergeSessionId() {
    let sid = sessionStorage.getItem(CONCIERGE_SESSION_KEY);
    if (!sid && typeof crypto !== 'undefined' && crypto.randomUUID) {
        sid = crypto.randomUUID();
        sessionStorage.setItem(CONCIERGE_SESSION_KEY, sid);
    } else if (!sid) {
        sid = 'sess_' + String(Date.now()) + '_' + String(Math.random()).slice(2, 10);
        sessionStorage.setItem(CONCIERGE_SESSION_KEY, sid);
    }
    return sid;
}

function escapeHtml(text) {
    if (text == null || text === '') return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function routingHintHtml(data) {
    if (!data || !data.routing_low_confidence || !data.routing_hint) return '';
    return `<p class="routing-hint" role="status">${escapeHtml(data.routing_hint)}</p>`;
}

function demoSetText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text == null ? '' : String(text);
}

function refreshDemoSessionId() {
    demoSetText('demoSid', getConciergeSessionId() || '—');
}

function initDemoSidebar() {
    refreshDemoSessionId();
    const ul = document.getElementById('demoToolList');
    if (ul) {
        ul.innerHTML = DEMO_AGENT_TOOLS.map(
            ([name, desc]) => `<li><strong>${escapeHtml(name)}</strong> — ${escapeHtml(desc)}</li>`
        ).join('');
    }
    const btn = document.getElementById('demoSidebarToggle');
    const page = document.querySelector('.page-with-sidebar');
    if (btn && page) {
        btn.addEventListener('click', () => {
            page.classList.toggle('sidebar-collapsed');
            const collapsed = page.classList.contains('sidebar-collapsed');
            btn.textContent = collapsed ? '⟩' : '⟨';
            btn.setAttribute('aria-expanded', String(!collapsed));
            btn.title = collapsed ? 'Expand panel' : 'Collapse panel';
        });
    }
}

function updateDemoObservabilitySearch(data, clientLatency) {
    if (!document.getElementById('demoLastSearchQuery')) return;
    demoSetText('demoLastSearchQuery', data.query || '—');
    demoSetText('demoLastSearchIntent', data.intent ? String(data.intent).toUpperCase() : '—');
    const c = data.confidence;
    demoSetText('demoLastSearchConf', c != null ? `${(Number(c) * 100).toFixed(1)}%` : '—');
    const srv = data.latency_ms != null ? Number(data.latency_ms).toFixed(1) : '—';
    demoSetText('demoLastSearchLat', clientLatency != null ? `${srv} ms srv · ${clientLatency} ms RTT` : `${srv} ms`);
    demoSetText('demoLastSearchRedis', data.redis_time_ms != null ? `${data.redis_time_ms} ms` : '—');
    if (data.intent === 'search') {
        demoSetText('demoLastSearchTotal', String(data.total ?? 0));
        const hit = data.breakdown && data.breakdown.cache_hit;
        demoSetText('demoLastSearchCache', hit ? 'hit' : 'miss');
    } else {
        demoSetText('demoLastSearchTotal', '— (chat mode)');
        demoSetText('demoLastSearchCache', '—');
    }
    const row = document.getElementById('demoLastSearchRouteRow');
    const hintEl = document.getElementById('demoLastSearchRoute');
    if (row && hintEl) {
        if (data.routing_low_confidence && data.routing_hint) {
            row.hidden = false;
            hintEl.textContent = data.routing_hint;
        } else {
            row.hidden = true;
            hintEl.textContent = '';
        }
    }
}

function updateDemoObservabilityConcierge(payload) {
    if (!document.getElementById('demoConcProv')) return;
    demoSetText('demoConcProv', payload.provider || '—');
    demoSetText('demoConcModel', payload.model || '—');
    demoSetText('demoConcLat', payload.latency_ms != null ? `${Number(payload.latency_ms).toFixed(1)} ms` : '—');
    const cart = payload.cart || {};
    const lines = cart.line_count != null ? cart.line_count : (Array.isArray(cart.items) ? cart.items.length : 0);
    const sub = cart.subtotal != null ? `R$ ${Number(cart.subtotal).toFixed(2)}` : '—';
    demoSetText('demoConcCart', `${lines} line(s) · ${sub}`);
    const pre = document.getElementById('demoConcTrace');
    const hint = document.getElementById('demoConcTraceHint');
    const trace = payload.tool_trace;
    if (pre && hint) {
        if (trace && Array.isArray(trace) && trace.length > 0) {
            pre.hidden = false;
            pre.textContent = JSON.stringify(trace, null, 2);
            hint.hidden = true;
        } else {
            pre.hidden = true;
            pre.textContent = '';
            hint.hidden = false;
        }
    }
    refreshDemoSessionId();
}

function formatConciergeReply(text) {
    let s = escapeHtml(text || '');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    const lines = s.split('\n');
    const parts = [];
    let listOpen = false;
    for (const line of lines) {
        const m = line.match(/^\s*-\s+(.*)$/);
        if (m) {
            if (!listOpen) {
                parts.push('<ul>');
                listOpen = true;
            }
            parts.push(`<li>${m[1]}</li>`);
        } else {
            if (listOpen) {
                parts.push('</ul>');
                listOpen = false;
            }
            parts.push(line);
        }
    }
    if (listOpen) {
        parts.push('</ul>');
    }
    return parts.join('<br>');
}

function appendConciergeTyping() {
    const wrap = document.getElementById('conciergeMessages');
    if (!wrap) return;
    const div = document.createElement('div');
    div.id = 'conciergeTypingIndicator';
    div.className = 'concierge-msg concierge-msg--typing';
    div.setAttribute('aria-live', 'polite');
    div.innerHTML = '<span class="concierge-dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span> Thinking…';
    wrap.appendChild(div);
    wrap.scrollTop = wrap.scrollHeight;
}

function removeConciergeTyping() {
    document.getElementById('conciergeTypingIndicator')?.remove();
}

function appendConciergeMessage(role, text) {
    const wrap = document.getElementById('conciergeMessages');
    if (!wrap) return;
    const div = document.createElement('div');
    div.className = `concierge-msg concierge-msg--${role}`;
    if (role === 'assistant') {
        div.innerHTML = formatConciergeReply(text);
    } else {
        div.textContent = text;
    }
    wrap.appendChild(div);
    wrap.scrollTop = wrap.scrollHeight;
}

function renderConciergeCart(cart) {
    const el = document.getElementById('conciergeCart');
    if (!el) return;
    const items = cart && Array.isArray(cart.items) ? cart.items : [];
    if (!items.length) {
        el.innerHTML = '<div style="opacity:0.8;">Cart is empty for this session.</div>';
        return;
    }
    const rows = items.map((it) => `
        <tr>
            <td>${escapeHtml(it.title)}</td>
            <td><code>${escapeHtml(it.sku_id)}</code></td>
            <td class="num">${it.qty}</td>
            <td class="num">R$ ${Number(it.unit_price).toFixed(2)}</td>
            <td class="num">R$ ${Number(it.line_total).toFixed(2)}</td>
        </tr>
    `).join('');
    el.innerHTML = `
        <div style="margin-bottom:6px;font-weight:600;">Cart</div>
        <table>
            <thead><tr><th>Product</th><th>SKU</th><th class="num">Qty</th><th class="num">Unit</th><th class="num">Total</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
        <div class="cart-subtotal">Subtotal: ${Number(cart.subtotal || 0).toFixed(2)} ${cart.currency || 'BRL'}</div>
    `;
}

async function sendConciergeMessage(message) {
    appendConciergeMessage('user', message);
    appendConciergeTyping();
    const btn = document.getElementById('conciergeSend');
    const input = document.getElementById('conciergeInput');
    if (btn) btn.disabled = true;
    try {
        const sid = getConciergeSessionId();
        const res = await fetch('/api/concierge/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                session_id: sid,
            }),
        });
        let data = {};
        try {
            data = await res.json();
        } catch (_) {
            data = {};
        }
        if (!res.ok) {
            const detail = data.detail != null ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)) : res.statusText;
            throw new Error(detail || 'Request failed');
        }
        if (data.session_id) {
            sessionStorage.setItem(CONCIERGE_SESSION_KEY, data.session_id);
        }
        removeConciergeTyping();
        appendConciergeMessage('assistant', data.reply || '(no response)');
        renderConciergeCart(data.cart || {});
        updateDemoObservabilityConcierge({
            provider: data.provider,
            model: data.model,
            latency_ms: data.latency_ms,
            cart: data.cart,
            tool_trace: data.tool_trace,
        });
        const meta = document.getElementById('conciergeMeta');
        if (meta) {
            const bits = [
                data.language ? String(data.language).toUpperCase() : '',
                data.provider,
                data.model,
                data.latency_ms != null ? `${data.latency_ms} ms` : '',
            ].filter(Boolean);
            meta.textContent = bits.join(' · ');
        }
    } catch (err) {
        removeConciergeTyping();
        appendConciergeMessage('system', `Error: ${err.message || String(err)}`);
    } finally {
        removeConciergeTyping();
        if (btn) btn.disabled = false;
        input?.focus();
    }
}

function openConciergePanelFromUser() {
    const fab = document.getElementById('conciergeFab');
    const panel = document.getElementById('conciergePanel');
    if (!fab || !panel) return;
    panel.classList.remove('hidden');
    panel.classList.remove('concierge-panel--minimized');
    fab.classList.add('hidden');
    if (!conciergeWelcomed) {
        conciergeWelcomed = true;
        appendConciergeMessage('system', 'Tip: ask about products, add to cart, or FAQ-style questions. Portuguese or English is fine.');
    }
    document.getElementById('conciergeInput')?.focus();
}

function showBarRoutedConcierge(data) {
    openConciergePanelFromUser();
    if (data.query) {
        appendConciergeMessage('user', data.query);
    }
    appendConciergeMessage('assistant', data.chat_response || '(no response)');
    if (data.session_id) {
        sessionStorage.setItem(CONCIERGE_SESSION_KEY, data.session_id);
    }
    renderConciergeCart(data.cart || {});
    const meta = document.getElementById('conciergeMeta');
    if (meta) {
        const bits = [data.chat_provider, data.chat_model, data.latency_ms != null ? `${data.latency_ms} ms` : ''].filter(Boolean);
        meta.textContent = bits.join(' · ');
    }
}

function setupConciergePanel() {
    const fab = document.getElementById('conciergeFab');
    const panel = document.getElementById('conciergePanel');
    const closeBtn = document.getElementById('conciergeClose');
    const minBtn = document.getElementById('conciergeMinimize');
    const form = document.getElementById('conciergeForm');
    if (!fab || !panel) return;

    fab.addEventListener('click', () => {
        openConciergePanelFromUser();
    });

    closeBtn?.addEventListener('click', () => {
        panel.classList.add('hidden');
        fab.classList.remove('hidden');
    });

    minBtn?.addEventListener('click', () => {
        panel.classList.toggle('concierge-panel--minimized');
    });

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const input = document.getElementById('conciergeInput');
        const msg = (input?.value || '').trim();
        if (!msg) return;
        input.value = '';
        await sendConciergeMessage(msg);
    });

    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        if (panel.classList.contains('hidden')) return;
        panel.classList.add('hidden');
        fab.classList.remove('hidden');
    });
}


// ============================================================================
// AUTOCOMPLETE (Simulated - using search results)
// ============================================================================

function handleInput(event) {
    const query = event.target.value.trim();

    clearTimeout(debounceTimer);

    if (query.length < 2) {
        hideAutocomplete();
        return;
    }

    // Show loading state immediately for better perceived performance
    showAutocompleteLoading();

    // Reduced debounce for snappier feel
    debounceTimer = setTimeout(() => {
        fetchAutocomplete(query);
    }, 100);
}

async function fetchAutocomplete(query) {
    // Prevent duplicate requests
    if (requestInFlight || query === lastQuery) {
        return;
    }

    requestInFlight = true;
    lastQuery = query;

    try {
        // Use dedicated autocomplete endpoint (FT.SUGGET)
        const response = await fetch(`/autocomplete?q=${encodeURIComponent(query)}&limit=5`);
        const data = await response.json();

        // Only update if query hasn't changed
        if (query === searchInput.value.trim()) {
            if (data.suggestions && data.suggestions.length > 0) {
                displayAutocomplete(data.suggestions);
            } else {
                hideAutocomplete();
            }
        }
    } catch (error) {
        console.error('Autocomplete error:', error);
        hideAutocomplete();
    } finally {
        requestInFlight = false;
    }
}

function showAutocompleteLoading() {
    autocompleteDropdown.innerHTML = `
        <div class="autocomplete-item" style="justify-content: center; opacity: 0.6;">
            <span>🔍 Searching…</span>
        </div>
    `;
    autocompleteDropdown.classList.remove('hidden');
}

function displayAutocomplete(results) {
    currentResults = results;
    selectedIndex = -1;

    autocompleteDropdown.innerHTML = results.map((item, index) => `
        <div class="autocomplete-item" data-index="${index}">
            <span class="autocomplete-icon">${item.icon || getDefaultIcon(item.type)}</span>
            <div class="autocomplete-content">
                <div class="autocomplete-title">${item.title}</div>
                <div class="autocomplete-subtitle">${item.subtitle || item.category}</div>
            </div>
            <span class="autocomplete-type type-${item.type}">${item.type}</span>
        </div>
    `).join('');

    autocompleteDropdown.classList.remove('hidden');

    // Add click handlers
    document.querySelectorAll('.autocomplete-item').forEach(item => {
        item.addEventListener('click', () => {
            const index = parseInt(item.dataset.index);
            selectAutocompleteItem(index);
        });
    });
}

function hideAutocomplete() {
    autocompleteDropdown.classList.add('hidden');
    // Don't clear results immediately - keep for potential reuse
    selectedIndex = -1;
}

function selectAutocompleteItem(index) {
    const item = currentResults[index];
    if (item) {
        searchInput.value = item.title;
        hideAutocomplete();
        performSearch(item.title);
    }
}

function getDefaultIcon(type) {
    const icons = {
        'route': '🔗',
        'sku': '🛍️',
        'product': '💼'
    };
    return icons[type] || '📌';
}

// ============================================================================
// KEYBOARD NAVIGATION
// ============================================================================

function handleKeyboard(event) {
    if (!autocompleteDropdown.classList.contains('hidden')) {
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            selectedIndex = Math.min(selectedIndex + 1, currentResults.length - 1);
            updateSelection();
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            selectedIndex = Math.max(selectedIndex - 1, -1);
            updateSelection();
        } else if (event.key === 'Enter') {
            event.preventDefault();
            if (selectedIndex >= 0) {
                selectAutocompleteItem(selectedIndex);
            } else {
                performSearch(searchInput.value.trim());
            }
        } else if (event.key === 'Escape') {
            hideAutocomplete();
        }
    } else if (event.key === 'Enter') {
        performSearch(searchInput.value.trim());
    }
}

function updateSelection() {
    document.querySelectorAll('.autocomplete-item').forEach((item, index) => {
        if (index === selectedIndex) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });
}

// ============================================================================
// SEARCH
// ============================================================================

async function performSearch(query) {
    if (!query || query.length === 0) {
        return;
    }

    hideAutocomplete();

    // Show loading
    if (loadingIndicator) loadingIndicator.classList.remove('hidden');
    if (searchInfo) searchInfo.classList.add('hidden');
    if (resultsContainer) resultsContainer.innerHTML = '';

    try {
        const startTime = performance.now();
        // Unified /api/search (intent router) + same Redis session as Concierge panel.
        const sid = getConciergeSessionId();
        const response = await fetch(
            `/api/search?q=${encodeURIComponent(query)}&limit=20&use_openai=true&session_id=${encodeURIComponent(sid)}`
        );

        if (!response.ok) {
            throw new Error('Search request failed');
        }

        const data = await response.json();
        const endTime = performance.now();
        const clientLatency = Math.round(endTime - startTime);

        if (data.session_id) {
            sessionStorage.setItem(CONCIERGE_SESSION_KEY, data.session_id);
        }

        // Update stats
        updateStats(query, data, clientLatency);

        // Update debug panel
        updateDebugPanel(data, clientLatency);

        // Display results
        displaySearchResults(data);

        updateDemoObservabilitySearch(data, clientLatency);
        if (data.intent === 'chat') {
            updateDemoObservabilityConcierge({
                provider: data.chat_provider,
                model: data.chat_model,
                latency_ms: data.latency_ms,
                cart: data.cart,
                tool_trace: data.tool_trace,
            });
        }

    } catch (error) {
        console.error('Search error:', error);
        if (searchInfo) {
            searchInfo.innerHTML = `<p style="color: red;">❌ Search error: ${error.message}</p>`;
            searchInfo.classList.remove('hidden');
        } else {
            alert(`❌ Search error: ${error.message}`);
        }
    } finally {
        if (loadingIndicator) loadingIndicator.classList.add('hidden');
    }
}

function updateStats(query, data, clientLatency) {
    if (lastQueryEl) lastQueryEl.textContent = query;
    const serverMs = Number(data.latency_ms) || 0;
    if (latencyEl) latencyEl.textContent = `${serverMs}ms (server) + ${clientLatency}ms (client) = ${serverMs + clientLatency}ms total`;

    if (intentEl) {
        if (data.intent === 'chat') {
            const prov = data.chat_provider || 'mock';
            let html = `<span class="strategy-badge strategy-vector">💬 Concierge · ${prov}</span>`;
            if (data.routing_low_confidence) {
                html += ' <span class="routing-low-badge">⚠ router</span>';
            }
            intentEl.innerHTML = html;
        } else if (data.results && Array.isArray(data.results)) {
            const matchTypes = {};
            data.results.forEach(r => {
                const type = r.match_type || 'text';
                matchTypes[type] = (matchTypes[type] || 0) + 1;
            });
            let intentHtml = '';
            if (matchTypes['text']) {
                intentHtml += `<span class="strategy-badge strategy-exact">✅ Text: ${matchTypes['text']}</span> `;
            }
            if (matchTypes['vector']) {
                intentHtml += `<span class="strategy-badge strategy-vector">🧠 Semantic: ${matchTypes['vector']}</span> `;
            }
            if (matchTypes['hybrid_rrf']) {
                intentHtml += `<span class="strategy-badge strategy-vector">⚡ Hybrid RRF: ${matchTypes['hybrid_rrf']}</span> `;
            }
            if (data.routing_low_confidence) {
                intentHtml += '<span class="routing-low-badge">⚠ router</span> ';
            }
            intentEl.innerHTML = intentHtml || '<span class="strategy-badge">No matches</span>';
        }
    }

    if (resultCountEl) {
        if (data.intent === 'chat') {
            const n = (data.cart && data.cart.line_count) || 0;
            resultCountEl.textContent = n ? `${n} cart line(s)` : 'chat · empty cart';
        } else {
            resultCountEl.textContent = `${data.total != null ? data.total : 0} results`;
        }
    }
}

function displaySearchResults(data) {
    if (data.intent === 'chat' && data.chat_response) {
        showBarRoutedConcierge(data);
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="concierge-nudge">
                    <strong>Chat mode</strong> — the reply opened in the <strong>Concierge</strong> panel (💬). The grid below is for global hybrid search (search intent).
                </div>
            `;
        }
        if (searchInfo) {
            const lowTag = data.routing_low_confidence ? ' <span class="routing-low-badge">low router confidence</span>' : '';
            searchInfo.innerHTML = `<p><strong>Intent:</strong> Chat (concierge)${lowTag} | <strong>Latency:</strong> ${data.latency_ms}ms</p>${routingHintHtml(data)}`;
            searchInfo.classList.remove('hidden');
        }
        return;
    }

    // Handle SEARCH intent
    if (searchInfo) {
        if (data.results && data.results.length > 0) {
            // Count match types
            const matchTypes = {};
            data.results.forEach(r => {
                const type = r.match_type || 'text';
                matchTypes[type] = (matchTypes[type] || 0) + 1;
            });

            let matchInfo = [];
            if (matchTypes['text']) matchInfo.push(`✅ Text: ${matchTypes['text']}`);
            if (matchTypes['vector']) matchInfo.push(`🧠 Semantic: ${matchTypes['vector']}`);
            if (matchTypes['hybrid_rrf']) matchInfo.push(`⚡ Hybrid RRF: ${matchTypes['hybrid_rrf']}`);

            const lowTag = data.routing_low_confidence ? ' <span class="routing-low-badge">low router confidence</span>' : '';
            searchInfo.innerHTML = `
                <p>
                    <strong>Search:</strong> "${data.query}"${lowTag}
                </p>
                <p><strong>Total results:</strong> ${data.total} in ${data.latency_ms}ms${matchInfo.length ? ` | ${matchInfo.join(' + ')}` : ''}</p>
                ${routingHintHtml(data)}
            `;
            searchInfo.classList.remove('hidden');
        } else {
            const lowTag = data.routing_low_confidence ? ' <span class="routing-low-badge">low router confidence</span>' : '';
            searchInfo.innerHTML = `<p><strong>Query:</strong> "${data.query}"${lowTag} | <strong>Latency:</strong> ${data.latency_ms}ms</p>${routingHintHtml(data)}`;
            searchInfo.classList.remove('hidden');
        }
    }

    // Display results
    if (!resultsContainer) {
        console.error('Results container not found');
        return;
    }

    // Check if results exist and is an array
    if (!data.results || !Array.isArray(data.results) || data.results.length === 0) {
        resultsContainer.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px; background: white; border-radius: 15px;">
                <h3>😔 No results found</h3>
                <p>Try another search term (Portuguese demo data works well).</p>
            </div>
        `;
        return;
    }

    resultsContainer.innerHTML = '';

    data.results.forEach(item => {
        const card = createResultCard(item);
        resultsContainer.appendChild(card);
    });
}

function createResultCard(item) {
    const card = document.createElement('div');
    card.className = 'result-card';

    const priceHtml = item.price ? `<div class="result-price">R$ ${parseFloat(item.price).toFixed(2)}</div>` : '';

    // Match type badge
    const matchTypeIcons = {
        'text': '✅',
        'vector': '🧠'
    };
    const matchTypeLabels = {
        'text': 'Text Match',
        'vector': 'Semantic'
    };
    const matchType = item.match_type || 'text';
    const matchIcon = matchTypeIcons[matchType] || '✅';
    const matchLabel = matchTypeLabels[matchType] || 'Text';

    card.innerHTML = `
        <div class="result-header">
            <span class="result-icon">${item.icon || getDefaultIcon(item.type)}</span>
            <div class="result-content">
                <div class="result-title">
                    ${item.title}
                    <span class="match-type-badge match-type-${matchType}" title="Match type: ${matchLabel}">${matchIcon}</span>
                </div>
                <div class="result-subtitle">${item.subtitle || ''}</div>
            </div>
        </div>
        <div class="result-footer">
            <div class="result-category">${item.category}</div>
            ${priceHtml}
        </div>
    `;

    // Add click handler
    card.addEventListener('click', () => {
        if (item.deep_link) {
            console.log('Navigate to:', item.deep_link);
            alert(`Navigate to: ${item.deep_link}\n\n(In production this would open the target screen.)`);
        }
    });

    return card;
}

// ============================================================================
// QUICK ACCESS BUTTONS
// ============================================================================

function setupQuickButtons() {
    document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            searchInput.value = query;
            searchInput.focus();
            performSearch(query);
        });
    });
}

// ============================================================================
// CLICK OUTSIDE
// ============================================================================

function handleClickOutside(event) {
    if (!searchInput.contains(event.target) && !autocompleteDropdown.contains(event.target)) {
        hideAutocomplete();
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

function init() {
    console.log('🔍 Initializing Redis Global Search taskbar…');

    if (!searchInput) {
        console.error('❌ Search input not found!');
        return;
    }

    // Event listeners
    searchInput.addEventListener('input', handleInput);
    searchInput.addEventListener('keydown', handleKeyboard);
    document.addEventListener('click', handleClickOutside);

    // Quick buttons
    setupQuickButtons();

    setupConciergePanel();
    initDemoSidebar();

    // Focus on search
    searchInput.focus();

    console.log('✅ Redis Global Search taskbar initialized');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}




// ============================================================================
// DEBUG PANEL
// ============================================================================

function updateDebugPanel(data, clientLatency) {
    const debugPanel = document.getElementById('debugPanel');
    const debugLanguage = document.getElementById('debugLanguage');
    const debugIntent = document.getElementById('debugIntent');
    const debugConfidence = document.getElementById('debugConfidence');
    const debugLatency = document.getElementById('debugLatency');
    const debugRedis = document.getElementById('debugRedis');
    const debugClient = document.getElementById('debugClient');

    if (!debugPanel) return;

    // Show panel
    debugPanel.classList.remove('hidden');

    // Update values
    if (debugLanguage && data.language) {
        debugLanguage.textContent = data.language.toUpperCase();
    }

    if (debugIntent && data.intent) {
        debugIntent.textContent = data.intent.toUpperCase();
        // Color code intent
        if (data.intent === 'search') {
            debugIntent.style.background = 'rgba(52, 211, 153, 0.3)';
        } else {
            debugIntent.style.background = 'rgba(251, 191, 36, 0.3)';
        }
    }

    if (debugConfidence && data.confidence !== undefined) {
        const conf = (data.confidence * 100).toFixed(1);
        debugConfidence.textContent = `${conf}%`;
    }

    if (debugLatency) {
        const serverLatency = data.latency_ms || 0;
        debugLatency.textContent = `${serverLatency.toFixed(1)}ms`;
    }

    if (debugRedis) {
        if (data.redis_time_ms !== undefined) {
            debugRedis.textContent = `${data.redis_time_ms}ms 🔥`;
        } else if (data.intent === 'chat') {
            debugRedis.textContent = '—';
        }
    }

    if (debugClient) {
        debugClient.textContent = `${clientLatency.toFixed(0)}ms`;
    }

    const feedbackBtn = document.getElementById('feedbackBtn');
    if (feedbackBtn && data.query && data.intent) {
        // Clear old listeners
        const newBtn = feedbackBtn.cloneNode(true);
        feedbackBtn.parentNode.replaceChild(newBtn, feedbackBtn);

        newBtn.onclick = async () => {
            const expected = data.intent === 'search' ? 'chat' : 'search';
            const reason = prompt(`The router labeled this as '${data.intent.toUpperCase()}'.\n\nDid you expect '${expected.toUpperCase()}'?\nType "yes" (or "sim") to send feedback for curation:`, "yes");

            if (reason && (reason.toLowerCase().includes('yes') || reason.toLowerCase().includes('sim'))) {
                newBtn.textContent = 'Sending…';
                try {
                    await fetch('/api/feedback', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            query: data.query,
                            detected_intent: data.intent,
                            expected_intent: expected,
                            language: data.language || 'pt'
                        })
                    });
                    newBtn.textContent = '✅ Feedback sent';
                    newBtn.style.background = '#10b981';
                    newBtn.style.color = '#fff';
                } catch (e) {
                    console.error("Feedback error", e);
                    newBtn.textContent = 'Send failed';
                }
            }
        };
    }
}
