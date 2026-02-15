var studentId = STATE.requireStudentId();

let dueCards = [];
let currentCardIndex = 0;
let isFlipped = false;

if (studentId) {
    loadStats();
    loadDueCards();
}

function showVocabSection(name) {
    document.querySelectorAll('.vocab-section').forEach(s => s.style.display = 'none');
    document.querySelectorAll('.vocab-tabs .tab').forEach(t => t.classList.remove('active'));

    document.getElementById('section-' + name).style.display = 'block';
    document.querySelectorAll('.vocab-tabs .tab').forEach(t => {
        if (t.textContent.toLowerCase().includes(name)) t.classList.add('active');
    });

    if (name === 'all') loadAllCards();
}

async function loadStats() {
    try {
        const resp = await apiFetch(`/api/concepts/${studentId}/stats`);
        const stats = await resp.json();

        document.getElementById('vocab-stats').innerHTML = `
            <div class="stat-item">
                <span class="stat-value">${stats.total_cards}</span>
                <span class="stat-label">Lacznie</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${stats.due_now}</span>
                <span class="stat-label">Do powtorki</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${stats.mastered}</span>
                <span class="stat-label">Opanowane</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${stats.learning}</span>
                <span class="stat-label">W trakcie</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${stats.total_reviews}</span>
                <span class="stat-label">Powtorki</span>
            </div>
        `;
    } catch (err) {
        document.getElementById('vocab-stats').innerHTML = '<p>Blad ladowania statystyk.</p>';
    }
}

async function loadDueCards() {
    const area = document.getElementById('flashcard-area');
    try {
        const resp = await apiFetch(`/api/concepts/${studentId}/due`);
        const data = await resp.json();
        dueCards = data.cards;
        currentCardIndex = 0;

        if (dueCards.length === 0) {
            area.innerHTML = `
                <div class="detail-panel" style="text-align:center;">
                    <h3>Brak kart do powtorki!</h3>
                    <p>Dodaj nowe karty lub wroc pozniej.</p>
                    <button onclick="showVocabSection('add')" class="btn btn-primary" style="margin-top:1rem;">
                        Dodaj karty
                    </button>
                </div>
            `;
            return;
        }

        renderFlashcard();
    } catch (err) {
        area.innerHTML = '<p>Blad ladowania kart: ' + err.message + '</p>';
    }
}

function renderFlashcard() {
    const area = document.getElementById('flashcard-area');
    if (currentCardIndex >= dueCards.length) {
        area.innerHTML = `
            <div class="detail-panel" style="text-align:center;">
                <h3>Powtorka zakonczona!</h3>
                <p>Swietna robota.</p>
                <button onclick="loadDueCards()" class="btn btn-primary" style="margin-top:1rem;">
                    Sprawdz ponownie
                </button>
            </div>
        `;
        loadStats();
        return;
    }

    const card = dueCards[currentCardIndex];
    isFlipped = false;

    area.innerHTML = `
        <div class="flashcard-progress">
            Karta ${currentCardIndex + 1} z ${dueCards.length}
        </div>
        <div class="flashcard" onclick="flipCard()" id="flashcard">
            <div class="flashcard-front">
                <span class="flashcard-label">Pojecie</span>
                <h2>${escapeHtml(card.concept)}</h2>
                ${card.example ? '<p class="flashcard-example">' + escapeHtml(card.example) + '</p>' : ''}
                <p class="meta">Kliknij aby odkryc</p>
            </div>
            <div class="flashcard-back" style="display:none;">
                <span class="flashcard-label">Wzor / Formula</span>
                <h2>${escapeHtml(card.formula)}</h2>
                ${card.explanation ? '<p class="flashcard-example">' + escapeHtml(card.explanation) + '</p>' : ''}
                ${card.example ? '<p class="flashcard-example">' + escapeHtml(card.example) + '</p>' : ''}
            </div>
        </div>
        <div class="flashcard-actions" id="flashcard-actions" style="display:none;">
            <button onclick="submitReview(0)" class="btn-review btn-again">Jeszcze raz</button>
            <button onclick="submitReview(2)" class="btn-review btn-hard">Trudne</button>
            <button onclick="submitReview(3)" class="btn-review btn-ok">OK</button>
            <button onclick="submitReview(4)" class="btn-review btn-good">Dobre</button>
            <button onclick="submitReview(5)" class="btn-review btn-easy">Latwe</button>
        </div>
    `;
    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(area, {delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}]});
    }
}

function flipCard() {
    if (isFlipped) return;
    isFlipped = true;

    document.querySelector('.flashcard-front').style.display = 'none';
    document.querySelector('.flashcard-back').style.display = 'flex';
    document.getElementById('flashcard').classList.add('flipped');
    document.getElementById('flashcard-actions').style.display = 'flex';
}

async function submitReview(quality) {
    const card = dueCards[currentCardIndex];
    try {
        await apiFetch(`/api/concepts/${studentId}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ card_id: card.id, quality: quality }),
        });

        currentCardIndex++;
        renderFlashcard();
    } catch (err) {
        alert('Blad wysylania oceny: ' + err.message);
    }
}

async function addCard(event) {
    event.preventDefault();
    const msg = document.getElementById('add-card-message');
    const concept = document.getElementById('card-concept').value.trim();
    const formula = document.getElementById('card-formula').value.trim();
    const explanation = document.getElementById('card-explanation').value.trim();
    const example = document.getElementById('card-example').value.trim();
    const mathDomain = document.getElementById('card-math-domain').value;

    try {
        const resp = await apiFetch(`/api/concepts/${studentId}/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                concept,
                formula,
                explanation: explanation || null,
                example: example || null,
                math_domain: mathDomain || null,
            }),
        });

        if (resp.status === 409) {
            msg.innerHTML = '<p style="color:#e74c3c;">Karta dla tego pojecia juz istnieje.</p>';
            return;
        }
        if (!resp.ok) {
            const err = await resp.json();
            msg.innerHTML = '<p style="color:#e74c3c;">Blad: ' + (err.detail || 'Nieznany') + '</p>';
            return;
        }

        msg.innerHTML = '<p style="color:#2ecc71;">Karta dodana!</p>';
        document.getElementById('add-card-form').reset();
        loadStats();
    } catch (err) {
        msg.innerHTML = '<p style="color:#e74c3c;">Blad: ' + err.message + '</p>';
    }
}

async function loadAllCards() {
    const container = document.getElementById('all-cards-list');
    try {
        const resp = await apiFetch(`/api/concepts/${studentId}/due`);
        const data = await resp.json();

        if (data.cards.length === 0) {
            container.innerHTML = '<p>Brak kart. Dodaj nowe!</p>';
            return;
        }

        container.innerHTML = data.cards.map(card => `
            <div class="vocab-card-row">
                <div class="vocab-word">${escapeHtml(card.concept)}</div>
                <div class="vocab-translation">${escapeHtml(card.formula)}</div>
                <div class="vocab-meta">
                    Powtorki: ${card.review_count} | Odstep: ${card.interval_days}d
                </div>
            </div>
        `).join('');
        if (typeof renderMathInElement !== 'undefined') {
            renderMathInElement(container, {delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}]});
        }
    } catch (err) {
        container.innerHTML = '<p>Blad ladowania kart.</p>';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}
