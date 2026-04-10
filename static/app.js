/**
 * Banco Inter Task Bar - Frontend
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
let debounceTimer = null;
let selectedIndex = -1;
let currentResults = [];
let lastQuery = '';
let requestInFlight = false;

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
            <span>🔍 Buscando...</span>
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
        // Use unified API endpoint for routing info
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=20`);

        if (!response.ok) {
            throw new Error('Search request failed');
        }

        const data = await response.json();
        const endTime = performance.now();
        const clientLatency = Math.round(endTime - startTime);

        // Update stats
        updateStats(query, data, clientLatency);

        // Update debug panel
        updateDebugPanel(data, clientLatency);

        // Display results
        displaySearchResults(data);

    } catch (error) {
        console.error('Search error:', error);
        if (searchInfo) {
            searchInfo.innerHTML = `<p style="color: red;">❌ Erro na busca: ${error.message}</p>`;
            searchInfo.classList.remove('hidden');
        } else {
            alert(`❌ Erro na busca: ${error.message}`);
        }
    } finally {
        if (loadingIndicator) loadingIndicator.classList.add('hidden');
    }
}

function updateStats(query, data, clientLatency) {
    if (lastQueryEl) lastQueryEl.textContent = query;
    if (latencyEl) latencyEl.textContent = `${data.latency_ms}ms (server) + ${clientLatency}ms (client) = ${data.latency_ms + clientLatency}ms total`;

    // Display match types (2-phase search: text → vector)
    if (intentEl && data.results && Array.isArray(data.results)) {
        // Count match types
        const matchTypes = {};
        data.results.forEach(r => {
            const type = r.match_type || 'text';
            matchTypes[type] = (matchTypes[type] || 0) + 1;
        });

        let intentHtml = '';

        // Show badges for each match type found
        if (matchTypes['text']) {
            intentHtml += `<span class="strategy-badge strategy-exact">✅ Text: ${matchTypes['text']}</span> `;
        }
        if (matchTypes['vector']) {
            intentHtml += `<span class="strategy-badge strategy-vector">🧠 Semantic: ${matchTypes['vector']}</span> `;
        }

        intentEl.innerHTML = intentHtml || '<span class="strategy-badge">No matches</span>';
    }

    if (resultCountEl) resultCountEl.textContent = `${data.total} resultados`;
}

function displaySearchResults(data) {
    // Handle CHAT intent
    if (data.intent === 'chat' && data.chat_response) {
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="chat-response" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 16px; margin: 20px 0;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.2);">
                        <span style="font-size: 24px;">💬</span>
                        <strong style="font-size: 18px;">Resposta do Chat</strong>
                        <span style="margin-left: auto; padding: 4px 12px; background: rgba(255,255,255,0.2); border-radius: 20px; font-size: 12px;">${data.chat_provider || 'mock'}</span>
                    </div>
                    <div style="font-size: 16px; line-height: 1.6;">
                        ${data.chat_response.replace(/\n/g, '<br>')}
                    </div>
                </div>
            `;
        }
        if (searchInfo) {
            searchInfo.innerHTML = `<p><strong>Intent:</strong> Chat | <strong>Latency:</strong> ${data.latency_ms}ms</p>`;
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

            searchInfo.innerHTML = `
                <p>
                    <strong>Busca por:</strong> "${data.query}"
                </p>
                <p><strong>Total de resultados:</strong> ${data.total} em ${data.latency_ms}ms | ${matchInfo.join(' + ')}</p>
            `;
            searchInfo.classList.remove('hidden');
        } else {
            searchInfo.innerHTML = `<p><strong>Query:</strong> "${data.query}" | <strong>Latency:</strong> ${data.latency_ms}ms</p>`;
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
                <h3>😔 Nenhum resultado encontrado</h3>
                <p>Tente outro termo de busca</p>
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
            alert(`Navegando para: ${item.deep_link}\n\n(Em produção, isso abriria a tela correspondente)`);
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
    console.log('🏦 Initializing Banco Inter Task Bar...');

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

    // Focus on search
    searchInput.focus();

    console.log('✅ Banco Inter Task Bar initialized');
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

    if (debugRedis && data.redis_time_ms !== undefined) {
        debugRedis.textContent = `${data.redis_time_ms}ms 🔥`;
    }

    if (debugClient) {
        debugClient.textContent = `${clientLatency.toFixed(0)}ms`;
    }

    // Attach Feedback Logic
    const feedbackBtn = document.getElementById('feedbackBtn');
    if (feedbackBtn && data.query && data.intent) {
        // Clear old listeners
        const newBtn = feedbackBtn.cloneNode(true);
        feedbackBtn.parentNode.replaceChild(newBtn, feedbackBtn);

        newBtn.onclick = async () => {
            const expected = data.intent === 'search' ? 'chat' : 'search';
            const reason = prompt(`O sistema roteou isso como '${data.intent.toUpperCase()}'.\n\nVocê esperava que fosse '${expected.toUpperCase()}'?\nDigite "sim" para confirmar e enviar para curadoria:`, "sim");

            if (reason && reason.toLowerCase().includes('sim')) {
                newBtn.textContent = 'Enviando...';
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
                    newBtn.textContent = '✅ Feedback Enviado';
                    newBtn.style.background = '#10b981';
                    newBtn.style.color = '#fff';
                } catch (e) {
                    console.error("Feedback error", e);
                    newBtn.textContent = 'Erro ao enviar';
                }
            }
        };
    }
}
