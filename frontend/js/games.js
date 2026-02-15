/**
 * Gry Matematyczne
 * Dopasuj Pojecia, Uloz Rownanie, Znajdz Blad, Szybkie Liczenie
 */

var studentId = STATE.requireStudentId();
if (!studentId) { /* redirect triggered */ }
let currentGame = null;
let gameTimer = null;
let gameSeconds = 0;
let gameCorrect = 0;
let gameTotal = 0;
let gameData = null;

async function startGame(type) {
    const content = document.getElementById('game-content');
    content.innerHTML = '<div class="loading">Generowanie gry...</div>';

    document.getElementById('game-selection').classList.add('hidden');
    document.getElementById('game-area').classList.remove('hidden');
    document.getElementById('game-results').classList.add('hidden');

    currentGame = type;
    gameCorrect = 0;
    gameTotal = 0;
    gameSeconds = 0;

    try {
        const resp = await apiFetch(`/api/games/${studentId}/${type}`);
        gameData = await resp.json();

        startTimer(gameData.time_limit || 60);

        switch (type) {
            case 'concept-match': renderConceptMatch(gameData); break;
            case 'equation-builder': renderEquationBuilder(gameData); break;
            case 'error-hunt': renderErrorHunt(gameData); break;
            case 'speed-calc': renderSpeedCalc(gameData); break;
        }
    } catch (err) {
        content.innerHTML = '<p>Blad ladowania gry: ' + err.message + '</p>';
    }
}

function exitGame() {
    clearInterval(gameTimer);
    document.getElementById('game-selection').classList.remove('hidden');
    document.getElementById('game-area').classList.add('hidden');
    document.getElementById('game-results').classList.add('hidden');
    loadHistory();
}

function startTimer(limit) {
    clearInterval(gameTimer);
    gameSeconds = 0;
    updateTimerDisplay();

    gameTimer = setInterval(() => {
        gameSeconds++;
        updateTimerDisplay();
        if (gameSeconds >= limit) {
            clearInterval(gameTimer);
            endGame();
        }
    }, 1000);
}

function updateTimerDisplay() {
    const min = Math.floor(gameSeconds / 60);
    const sec = gameSeconds % 60;
    document.getElementById('game-timer').textContent = `${min}:${sec.toString().padStart(2, '0')}`;
}

function updateScoreDisplay() {
    document.getElementById('game-score-live').textContent = `${gameCorrect} / ${gameTotal}`;
}

// ===== DOPASUJ POJECIA =====
function renderConceptMatch(data) {
    const content = document.getElementById('game-content');
    const pairs = data.pairs || [];
    gameTotal = pairs.length;

    const concepts = pairs.map(p => p.concept).sort(() => Math.random() - 0.5);
    const definitions = pairs.map(p => p.definition).sort(() => Math.random() - 0.5);

    content.innerHTML = `
        <div class="match-game">
            <p class="game-instruction">Dopasuj pojecia do ich definicji.</p>
            <div class="match-columns">
                <div class="match-col" id="words-col">
                    ${concepts.map(w => `<div class="match-item match-word" data-word="${escapeHtml(w)}" onclick="selectMatchItem(this, 'word')">${escapeHtml(w)}</div>`).join('')}
                </div>
                <div class="match-col" id="trans-col">
                    ${definitions.map(t => `<div class="match-item match-trans" data-trans="${escapeHtml(t)}" onclick="selectMatchItem(this, 'trans')">${escapeHtml(t)}</div>`).join('')}
                </div>
            </div>
        </div>
    `;
    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(content, {delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}]});
    }

    window._matchPairs = pairs;
    window._matchSelected = { word: null, trans: null };
    window._matchMatched = new Set();
}

function selectMatchItem(el, type) {
    if (el.classList.contains('matched')) return;

    document.querySelectorAll(`.match-${type}`).forEach(e => e.classList.remove('selected'));
    el.classList.add('selected');

    window._matchSelected[type] = type === 'word' ? el.dataset.word : el.dataset.trans;

    if (window._matchSelected.word && window._matchSelected.trans) {
        const pair = window._matchPairs.find(p => p.concept === window._matchSelected.word);
        if (pair && pair.definition === window._matchSelected.trans) {
            gameCorrect++;
            document.querySelectorAll('.match-item.selected').forEach(e => {
                e.classList.remove('selected');
                e.classList.add('matched');
            });
            window._matchMatched.add(window._matchSelected.word);
        } else {
            document.querySelectorAll('.match-item.selected').forEach(e => {
                e.classList.add('wrong');
                setTimeout(() => e.classList.remove('wrong', 'selected'), 600);
            });
        }

        window._matchSelected = { word: null, trans: null };
        updateScoreDisplay();

        if (window._matchMatched.size === window._matchPairs.length) {
            setTimeout(() => endGame(), 500);
        }
    }
}

// ===== ULOZ ROWNANIE =====
function renderEquationBuilder(data) {
    const content = document.getElementById('game-content');
    const sentences = data.sentences || [];
    gameTotal = sentences.length;

    content.innerHTML = `
        <div class="sentence-game">
            <p class="game-instruction">Uloz elementy w odpowiedniej kolejnosci, aby utworzyc poprawne rownanie.</p>
            <div id="sentence-items"></div>
        </div>
    `;

    window._sentenceIdx = 0;
    window._sentences = sentences;
    renderNextSentence();
}

function renderNextSentence() {
    const idx = window._sentenceIdx;
    const sentences = window._sentences;

    if (idx >= sentences.length) {
        endGame();
        return;
    }

    const s = sentences[idx];
    const equation = s.equation || s.sentence || '';
    const words = equation.split(' ').sort(() => Math.random() - 0.5);
    const container = document.getElementById('sentence-items');

    container.innerHTML = `
        <div class="sb-progress">Rownanie ${idx + 1} z ${sentences.length}</div>
        ${s.hint ? `<p class="sb-hint">${escapeHtml(s.hint)}</p>` : ''}
        <div class="sb-answer-area" id="sb-answer"></div>
        <div class="sb-word-bank" id="sb-bank">
            ${words.map(w => `<span class="sb-word" onclick="addWord(this)">${escapeHtml(w)}</span>`).join('')}
        </div>
        <div class="sb-actions">
            <button onclick="clearSentence()" class="btn btn-sm">Wyczysc</button>
            <button onclick="checkSentence()" class="btn btn-sm btn-primary">Sprawdz</button>
        </div>
    `;
    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(container, {delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}]});
    }
}

function addWord(el) {
    if (el.classList.contains('used')) return;
    el.classList.add('used');
    const answer = document.getElementById('sb-answer');
    const word = document.createElement('span');
    word.className = 'sb-placed-word';
    word.textContent = el.textContent;
    word.onclick = function() {
        this.remove();
        el.classList.remove('used');
    };
    answer.appendChild(word);
}

function clearSentence() {
    document.getElementById('sb-answer').innerHTML = '';
    document.querySelectorAll('.sb-word').forEach(w => w.classList.remove('used'));
}

function checkSentence() {
    const placed = Array.from(document.querySelectorAll('.sb-placed-word')).map(w => w.textContent);
    const answer = placed.join(' ');
    const s = window._sentences[window._sentenceIdx];
    const correct = s.equation || s.sentence || '';

    if (answer.toLowerCase().trim() === correct.toLowerCase().trim()) {
        gameCorrect++;
        updateScoreDisplay();
    }

    window._sentenceIdx++;
    renderNextSentence();
}

// ===== ZNAJDZ BLAD =====
function renderErrorHunt(data) {
    const content = document.getElementById('game-content');
    const sentences = data.sentences || [];
    gameTotal = sentences.length;

    content.innerHTML = `
        <div class="error-hunt-game">
            <p class="game-instruction">Czy rozwiazanie jest poprawne, czy zawiera blad?</p>
            <div id="eh-items"></div>
        </div>
    `;

    window._ehIdx = 0;
    window._ehSentences = sentences;
    renderNextError();
}

function renderNextError() {
    const idx = window._ehIdx;
    const sentences = window._ehSentences;

    if (idx >= sentences.length) {
        endGame();
        return;
    }

    const s = sentences[idx];
    const container = document.getElementById('eh-items');

    container.innerHTML = `
        <div class="sb-progress">Zadanie ${idx + 1} z ${sentences.length}</div>
        <div class="eh-sentence">"${escapeHtml(s.sentence)}"</div>
        <div class="eh-actions">
            <button onclick="ehAnswer(true)" class="btn btn-danger">Ma blad</button>
            <button onclick="ehAnswer(false)" class="btn btn-secondary">Poprawne</button>
        </div>
        <div id="eh-feedback" class="hidden"></div>
    `;
    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(container, {delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}]});
    }
}

function ehAnswer(saidError) {
    const s = window._ehSentences[window._ehIdx];
    const correct = saidError === s.has_error;

    if (correct) gameCorrect++;
    updateScoreDisplay();

    const fb = document.getElementById('eh-feedback');
    fb.classList.remove('hidden');
    fb.className = `eh-feedback ${correct ? 'correct' : 'wrong'}`;

    if (s.has_error) {
        fb.innerHTML = `
            <p>${correct ? 'Dobrze!' : 'Zle!'} To rozwiazanie zawiera blad.</p>
            <p>Poprawnie: <strong>${escapeHtml(s.corrected || '')}</strong></p>
            <p>${escapeHtml(s.explanation || '')}</p>
        `;
    } else {
        fb.innerHTML = `<p>${correct ? 'Dobrze!' : 'Zle!'} To rozwiazanie jest poprawne.</p>`;
    }

    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(fb, {delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}]});
    }

    setTimeout(() => {
        window._ehIdx++;
        renderNextError();
    }, 2000);
}

// ===== SZYBKIE LICZENIE =====
function renderSpeedCalc(data) {
    const content = document.getElementById('game-content');
    const phrases = data.phrases || [];
    gameTotal = phrases.length;

    content.innerHTML = `
        <div class="speed-calc-game">
            <p class="game-instruction">Oblicz jak najszybciej!</p>
            <div id="st-items"></div>
        </div>
    `;

    window._stIdx = 0;
    window._stPhrases = phrases;
    renderNextCalc();
}

function renderNextCalc() {
    const idx = window._stIdx;
    const phrases = window._stPhrases;

    if (idx >= phrases.length) {
        endGame();
        return;
    }

    const p = phrases[idx];
    const container = document.getElementById('st-items');

    container.innerHTML = `
        <div class="sb-progress">Zadanie ${idx + 1} z ${phrases.length}</div>
        <div class="st-polish">${escapeHtml(p.problem)}</div>
        ${p.hint ? `<div class="st-hint">Podpowiedz: ${escapeHtml(p.hint)}</div>` : ''}
        <input type="text" id="st-input" class="fill-blank-input" placeholder="Wpisz odpowiedz..."
               onkeydown="if(event.key==='Enter')checkCalc()">
        <button onclick="checkCalc()" class="btn btn-sm btn-primary" style="margin-top:0.5rem;">Sprawdz</button>
        <div id="st-feedback" class="hidden"></div>
    `;

    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(container, {delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}]});
    }

    document.getElementById('st-input').focus();
}

function checkCalc() {
    const input = document.getElementById('st-input').value.trim().toLowerCase();
    const p = window._stPhrases[window._stIdx];
    const correct = String(p.answer).toLowerCase().trim();

    const isCorrect = input === correct ||
        input.replace(/\s/g, '') === correct.replace(/\s/g, '') ||
        levenshtein(input, correct) <= 1;

    if (isCorrect) gameCorrect++;
    updateScoreDisplay();

    const fb = document.getElementById('st-feedback');
    fb.classList.remove('hidden');
    fb.className = `eh-feedback ${isCorrect ? 'correct' : 'wrong'}`;
    fb.innerHTML = `
        <p>${isCorrect ? 'Dobrze!' : 'Nie tym razem.'}</p>
        <p>Odpowiedz: <strong>${escapeHtml(String(p.answer))}</strong></p>
    `;

    setTimeout(() => {
        window._stIdx++;
        renderNextCalc();
    }, 1500);
}

// Levenshtein distance for fuzzy matching
function levenshtein(a, b) {
    const m = a.length, n = b.length;
    const dp = Array.from({length: m + 1}, (_, i) => [i]);
    for (let j = 0; j <= n; j++) dp[0][j] = j;
    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            dp[i][j] = a[i-1] === b[j-1] ? dp[i-1][j-1] :
                1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]);
        }
    }
    return dp[m][n];
}

// ===== KONIEC GRY =====
async function endGame() {
    clearInterval(gameTimer);

    const score = gameTotal > 0 ? Math.round((gameCorrect / gameTotal) * 100) : 0;

    document.getElementById('game-area').classList.add('hidden');
    document.getElementById('game-results').classList.remove('hidden');
    document.getElementById('final-score').textContent = score + '%';

    try {
        const resp = await apiFetch(`/api/games/${studentId}/submit`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                game_type: currentGame,
                score: score,
                data: {correct: gameCorrect, total: gameTotal, time: gameSeconds}
            })
        });
        const result = await resp.json();

        document.getElementById('xp-earned-display').innerHTML =
            `<span class="game-xp-earned">+${result.xp_earned} XP</span>`;

        if (typeof CELEBRATIONS !== 'undefined') {
            CELEBRATIONS.showXpGain(result.xp_earned);
            if (score >= 90) {
                CELEBRATIONS.triggerConfetti();
            }
        }

        const fb = document.getElementById('game-feedback');
        let msg = '';
        if (score >= 90) msg = 'Doskonale!';
        else if (score >= 70) msg = 'Swietna robota!';
        else if (score >= 50) msg = 'Dobra proba!';
        else msg = 'Cwicz dalej!';

        fb.innerHTML = `<p style="text-align:center;font-size:1.1rem;margin:1rem 0;">${msg}</p>
            <p style="text-align:center;color:#7f8c8d;">
                ${gameCorrect}/${gameTotal} poprawnie w ${gameSeconds}s
            </p>`;
    } catch (err) {
        console.error('Blad wysylania wyniku:', err);
    }
}

// ===== HISTORIA =====
async function loadHistory() {
    try {
        const resp = await apiFetch(`/api/games/${studentId}/history`);
        const data = await resp.json();
        renderHistory(data);
    } catch (err) {
        document.getElementById('history-content').innerHTML = '<p>Brak historii gier.</p>';
    }
}

function renderHistory(data) {
    const container = document.getElementById('history-content');
    const recent = data.recent || [];

    if (recent.length === 0) {
        container.innerHTML = '<p>Brak rozegranych gier. Wybierz gre powyzej!</p>';
        return;
    }

    const best = data.best_scores || {};
    let bestHtml = '<div class="game-best-scores">';
    for (const [type, info] of Object.entries(best)) {
        bestHtml += `<span class="best-score-chip">${type}: ${info.best}% (${info.times_played}x)</span>`;
    }
    bestHtml += '</div>';

    container.innerHTML = bestHtml + recent.slice(0, 5).map(r => `
        <div class="xp-entry">
            <span class="xp-source">${escapeHtml(r.game_type)}</span>
            <span class="xp-amount positive">${r.score}%</span>
            <span class="xp-detail">+${r.xp_earned} XP</span>
        </div>
    `).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

// Load history on page load
loadHistory();
