let currentStudentId = null;
let currentStudentName = null;
let assessmentData = null;

const urlParams = new URLSearchParams(window.location.search);
const returningStudentId = urlParams.get('student_id');
const returningFrom = urlParams.get('from');

if (returningStudentId && returningFrom === 'assessment') {
    currentStudentId = parseInt(returningStudentId);
    resumeAtStep3();
}

// Step 1: Submit basic info
document.getElementById('step1-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const data = {
        name: form.name.value,
        age: form.age.value ? parseInt(form.age.value) : null,
        filler: form.filler.value,
    };

    try {
        const resp = await apiFetch('/api/intake', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (!resp.ok) {
            const err = await resp.json();
            showError('Blad: ' + (err.detail || JSON.stringify(err)));
            return;
        }

        const result = await resp.json();
        currentStudentId = result.student_id;
        STATE.setStudentId(currentStudentId);
        currentStudentName = data.name;

        goToStep2();
    } catch (err) {
        showError('Blad sieci: ' + err.message);
    }
});

function goToStep2() {
    document.getElementById('wizard-step-1').classList.remove('active');
    document.getElementById('wizard-step-1').classList.add('completed');
    document.getElementById('wizard-step-2').classList.add('active');

    document.getElementById('step1-content').classList.add('hidden');
    document.getElementById('step2-content').classList.remove('hidden');

    document.getElementById('step2-student-name').textContent = currentStudentName || 'Uczen';
    document.getElementById('step2-student-id').textContent = currentStudentId;
    document.getElementById('assessment-link').href = `assessment.html?student_id=${currentStudentId}&return_to=intake`;

    document.getElementById('step2-waiting').classList.remove('hidden');
}

async function checkAssessmentAndProceed() {
    try {
        const resp = await apiFetch(`/api/assessment/${currentStudentId}`);
        if (resp.ok) {
            assessmentData = await resp.json();
            if (assessmentData.status === 'completed') {
                if (assessmentData.determined_level) {
                    await apiFetch(`/api/intake/${currentStudentId}/level`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ level: assessmentData.determined_level }),
                    });
                }
                goToStep3();
                return;
            }
        }
        showError('Test nie zostal jeszcze ukonczony. Prosze najpierw ukonczyc test lub pominac i ustawic poziom recznie.');
    } catch (err) {
        showError('Nie mozna sprawdzic statusu testu: ' + err.message);
    }
}

async function skipAssessment() {
    const selected = document.querySelector('input[name="manual_level"]:checked');
    if (!selected) {
        showError('Prosze wybrac poziom przed pominieciem testu.');
        return;
    }

    try {
        await apiFetch(`/api/intake/${currentStudentId}/level`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ level: selected.value }),
        });

        assessmentData = null;
        goToStep3();
    } catch (err) {
        showError('Blad ustawiania poziomu: ' + err.message);
    }
}

function goToStep3() {
    document.getElementById('wizard-step-2').classList.remove('active');
    document.getElementById('wizard-step-2').classList.add('completed');
    document.getElementById('wizard-step-3').classList.add('active');

    document.getElementById('step2-content').classList.add('hidden');
    document.getElementById('step3-content').classList.remove('hidden');

    if (assessmentData && assessmentData.status === 'completed') {
        const summaryPanel = document.getElementById('assessment-summary');
        summaryPanel.classList.remove('hidden');

        document.getElementById('summary-level').textContent = assessmentData.determined_level || '--';
        const confidence = assessmentData.confidence_score
            ? Math.round(assessmentData.confidence_score * 100) + '%'
            : '--';
        document.getElementById('summary-confidence').textContent = confidence;

        const weakDiv = document.getElementById('summary-weak-areas');
        if (assessmentData.weak_areas && assessmentData.weak_areas.length) {
            weakDiv.innerHTML = '<p style="margin-top:0.5rem;"><strong>Zidentyfikowane trudnosci:</strong></p><ul>' +
                assessmentData.weak_areas.map(a => `<li>${escapeHtml(a)}</li>`).join('') + '</ul>';

            document.getElementById('problems-desc').innerHTML =
                'Te obszary zostaly zaznaczone na podstawie testu. Mozesz je zmienic.';

            prePopulateProblemAreas(assessmentData.weak_areas);
        }
    }
}

function prePopulateProblemAreas(weakAreas) {
    const mapping = {
        'arytmetyka': 'arytmetyka',
        'arithmetic': 'arytmetyka',
        'ulamki': 'ulamki',
        'fractions': 'ulamki',
        'algebra': 'algebra',
        'geometria': 'geometria',
        'geometry': 'geometria',
        'procenty': 'procenty',
        'percentages': 'procenty',
        'rownania': 'rownania',
        'equations': 'rownania',
        'funkcje': 'funkcje',
        'functions': 'funkcje',
        'trygonometria': 'trygonometria',
        'trigonometry': 'trygonometria',
        'statystyka': 'statystyka',
        'statistics': 'statystyka',
        'logika': 'logika',
        'logic': 'logika',
        'analiza': 'funkcje',
        'rachunek': 'arytmetyka',
        'wyrazenia': 'algebra',
    };

    const toCheck = new Set();
    for (const area of weakAreas) {
        const lower = area.toLowerCase();
        if (mapping[lower] !== undefined) {
            toCheck.add(mapping[lower]);
            continue;
        }
        for (const [key, val] of Object.entries(mapping)) {
            if (val && lower.includes(key)) {
                toCheck.add(val);
            }
        }
    }

    for (const val of toCheck) {
        const cb = document.querySelector(`#step3-form input[name="problem_areas"][value="${val}"]`);
        if (cb) cb.checked = true;
    }
}

// Step 3: Submit goals
document.getElementById('step3-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const goals = Array.from(form.querySelectorAll('input[name="goals"]:checked')).map(cb => cb.value);
    const problemAreas = Array.from(form.querySelectorAll('input[name="problem_areas"]:checked')).map(cb => cb.value);
    const additionalNotes = form.additional_notes.value || null;

    try {
        const resp = await apiFetch(`/api/intake/${currentStudentId}/goals`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                goals: goals,
                problem_areas: problemAreas,
                additional_notes: additionalNotes,
            }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            showError('Blad: ' + (err.detail || JSON.stringify(err)));
            return;
        }

        showFinalResult();
    } catch (err) {
        showError('Blad sieci: ' + err.message);
    }
});

async function showFinalResult() {
    document.getElementById('wizard-step-3').classList.remove('active');
    document.getElementById('wizard-step-3').classList.add('completed');

    document.getElementById('step3-content').classList.add('hidden');
    const resultPanel = document.getElementById('result');
    resultPanel.classList.remove('hidden');

    document.getElementById('final-student-id').textContent = currentStudentId;

    try {
        const resp = await apiFetch(`/api/intake/${currentStudentId}`);
        if (resp.ok) {
            const student = await resp.json();
            document.getElementById('final-level').textContent = student.current_level || 'oczekujacy';
        }
    } catch {
        document.getElementById('final-level').textContent = assessmentData?.determined_level || 'oczekujacy';
    }
}

async function resumeAtStep3() {
    document.getElementById('step1-content').classList.add('hidden');

    document.getElementById('wizard-step-1').classList.remove('active');
    document.getElementById('wizard-step-1').classList.add('completed');
    document.getElementById('wizard-step-2').classList.add('completed');

    try {
        const resp = await apiFetch(`/api/assessment/${currentStudentId}`);
        if (resp.ok) {
            assessmentData = await resp.json();
            if (assessmentData.status === 'completed' && assessmentData.determined_level) {
                await apiFetch(`/api/intake/${currentStudentId}/level`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ level: assessmentData.determined_level }),
                });
            }
        }
    } catch {
        // Assessment data not available
    }

    goToStep3();
}

async function runDiagnostic() {
    if (!currentStudentId) return;

    const diagResult = document.getElementById('diagnostic-result');
    const diagOutput = document.getElementById('diagnostic-output');
    diagResult.classList.remove('hidden');
    diagOutput.textContent = 'Uruchamianie analizy diagnostycznej...';

    try {
        const resp = await apiFetch(`/api/diagnostic/${currentStudentId}`, {
            method: 'POST',
        });

        if (!resp.ok) {
            const err = await resp.json();
            diagOutput.textContent = 'Blad: ' + (err.detail || JSON.stringify(err));
            return;
        }

        const profile = await resp.json();
        diagOutput.textContent = JSON.stringify(profile, null, 2);
    } catch (err) {
        diagOutput.textContent = 'Blad sieci: ' + err.message;
    }
}

function showError(message) {
    const existing = document.querySelector('.error-banner');
    if (existing) existing.remove();

    const banner = document.createElement('div');
    banner.className = 'error-banner';
    banner.innerHTML = `<strong>Blad:</strong> ${escapeHtml(message)}`;
    document.querySelector('.container').prepend(banner);

    setTimeout(() => banner.remove(), 8000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
