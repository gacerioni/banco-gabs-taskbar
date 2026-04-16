async function loadExamples() {
    try {
        const lang = document.getElementById('filterLang').value;
        const intent = document.getElementById('filterIntent').value;
        
        let url = '/admin/api/router-examples?';
        if (lang) url += `language=${lang}&`;
        if (intent) url += `intent=${intent}&`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        // Update stats
        const stats = { pt: 0, en: 0, es: 0, search: 0, chat: 0 };
        data.items.forEach(item => {
            stats[item.language]++;
            stats[item.intent]++;
        });
        
        document.getElementById('statPT').textContent = stats.pt;
        document.getElementById('statEN').textContent = stats.en;
        document.getElementById('statES').textContent = stats.es;
        document.getElementById('statSearch').textContent = stats.search;
        document.getElementById('statChat').textContent = stats.chat;
        document.getElementById('totalExamples').textContent = data.total;
        
        // Render table
        const tbody = document.getElementById('examplesBody');
        tbody.innerHTML = data.items.map(item => `
            <tr>
                <td class="example-text">${item.example}</td>
                <td>${item.language.toUpperCase()}</td>
                <td><span style="background: ${item.intent === 'search' ? '#d1fae5' : '#fef3c7'}; padding: 4px 8px; border-radius: 4px; font-size: 12px;">${item.intent.toUpperCase()}</span></td>
                <td>${item.category || '-'}</td>
                <td style="font-size: 12px; color: #718096;">${item._file}</td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="deleteExample('${item._id}')">🗑️</button>
                </td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Error loading examples:', error);
        alert('Failed to load examples: ' + error.message);
    }
}

function createNew() {
    document.getElementById('modal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
    document.getElementById('exampleForm').reset();
}

async function saveExample(event) {
    event.preventDefault();

    const form = document.getElementById('exampleForm');
    const formData = new FormData(form);
    const example = {};

    for (let [key, value] of formData.entries()) {
        example[key] = value;
    }

    try {
        const response = await fetch('/admin/api/router-examples', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(example)
        });

        const data = await response.json();

        // HOT RELOAD SUCCESS!
        alert('✅ Example added successfully!\n\n🔥 HOT RELOAD: changes apply immediately, no restart!\n\n📝 ' + data.note);
        closeModal();
        loadExamples();
    } catch (error) {
        alert('❌ Save failed: ' + error.message);
    }
}

async function deleteExample(id) {
    if (!confirm(`🗑️ Delete example "${id}"?\n\nThis cannot be undone.`)) return;

    try {
        const response = await fetch(`/admin/api/router-examples/${encodeURIComponent(id)}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        // Router will auto-reload on next query
        alert('✅ ' + data.message + '\n\n🔄 The router reloads automatically on the next request.\n\n📝 ' + data.note);
        loadExamples();
    } catch (error) {
        alert('❌ Delete failed: ' + error.message);
    }
}

// Load on page load
loadExamples();

