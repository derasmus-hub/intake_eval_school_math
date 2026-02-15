/**
 * assessment.js — Robust assessment flow with STATE integration.
 * Polish math assessment version.
 */
(function () {
    'use strict';

    // ── State ──────────────────────────────────────────────────────────
    let assessmentId = null;
    let studentId = null;
    let placementAnswers = {};
    let diagnosticAnswers = {};
    let diagnosticQuestions = [];
    let submitting = false;

    // ── Helpers ────────────────────────────────────────────────────────

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function getScoreColor(score) {
        if (score >= 80) return '#2ecc71';
        if (score >= 60) return '#f39c12';
        if (score >= 40) return '#e67e22';
        return '#e74c3c';
    }

    function setStatus(message, type) {
        var el = document.getElementById('assessment-status');
        if (!el) return;
        el.textContent = message;
        el.className = 'assessment-status status-' + (type || 'info');
        el.style.display = 'block';
        console.log('[assessment] status (' + type + '):', message);
    }

    function clearStatus() {
        var el = document.getElementById('assessment-status');
        if (el) el.style.display = 'none';
    }

    /** Extract a human-readable error message from a non-ok response. */
    async function extractApiError(resp, context) {
        var detail = '';
        try {
            var body = await resp.text();
            var parsed = JSON.parse(body);
            detail = parsed.detail || JSON.stringify(parsed).substring(0, 300);
        } catch (_) {
            detail = 'Nieoczekiwana odpowied\u017A serwera';
        }
        var prefix = context ? context + ': ' : '';
        if (resp.status === 422) {
            return prefix + 'Nieprawid\u0142owe dane wys\u0142ane do serwera \u2014 ' + detail;
        }
        if (resp.status >= 500) {
            return prefix + 'B\u0142\u0105d serwera (' + resp.status + '). Sprawd\u017A logi backendu. ' + detail;
        }
        if (resp.status === 404) {
            return prefix + detail;
        }
        return prefix + '(' + resp.status + ') ' + detail;
    }

    // ── Expose answer handlers globally ────────────────────────────────
    window.onPlacementAnswer = function (questionId) {
        var input = document.getElementById('placement_input_' + questionId);
        if (input && input.value.trim()) {
            placementAnswers[questionId] = input.value.trim();
        } else {
            delete placementAnswers[questionId];
        }
        var total = document.querySelectorAll('#placement-questions .question-card').length;
        var answered = Object.keys(placementAnswers).length;
        document.getElementById('btn-submit-placement').disabled = answered < total;
        console.log('[assessment] placement answer', questionId, '\u2014 answered', answered, '/', total);
    };

    window.onDiagnosticAnswer = function (questionId) {
        var q = diagnosticQuestions.find(function (q) { return q.id === questionId; });
        if (!q) return;

        if (!q.options || !q.options.length) {
            var input = document.getElementById('diag_input_' + questionId);
            if (input && input.value.trim()) {
                diagnosticAnswers[questionId] = input.value.trim();
            } else {
                delete diagnosticAnswers[questionId];
            }
        } else {
            var selected = document.querySelector('input[name="diag_' + questionId + '"]:checked');
            if (selected) {
                diagnosticAnswers[questionId] = selected.value;
            }
        }

        var total = diagnosticQuestions.length;
        var answered = Object.keys(diagnosticAnswers).length;
        document.getElementById('btn-submit-diagnostic').disabled = answered < total;
        console.log('[assessment] diagnostic answer', questionId, '\u2014 answered', answered, '/', total);
    };

    // ── Core flow ──────────────────────────────────────────────────────

    async function startAssessment() {
        setStatus('Rozpoczynam test...', 'info');
        console.log('[assessment] startAssessment() student_id=', studentId);

        try {
            var endpoint = '/api/assessment/start';
            var payload = { student_id: studentId };
            console.log('[assessment] POST', endpoint, payload);

            var resp = await apiFetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            console.log('[assessment] startAssessment response status:', resp.status);

            if (!resp.ok) {
                var errMsg = await extractApiError(resp, 'Rozpocz\u0119cie testu');
                setStatus(errMsg, 'error');
                return;
            }

            var data = await STATE.safeJson(resp);
            assessmentId = data.assessment_id;
            console.log('[assessment] assessment_id=', assessmentId, 'questions=', data.questions && data.questions.length);

            if (!data.questions || !data.questions.length) {
                setStatus('B\u0142\u0105d: Serwer nie zwr\u00f3ci\u0142 pyta\u0144 klasyfikuj\u0105cych.', 'error');
                return;
            }

            renderPlacementQuestions(data.questions);
            clearStatus();
        } catch (e) {
            console.error('[assessment] startAssessment error:', e);
            setStatus('B\u0142\u0105d sieci: ' + e.message + '. Czy backend dzia\u0142a pod adresem ' + (window.API_BASE || ':8000') + '?', 'error');
        }
    }

    function renderPlacementQuestions(questions) {
        var container = document.getElementById('placement-questions');
        container.innerHTML = '';

        questions.forEach(function (q, idx) {
            var card = document.createElement('div');
            card.className = 'question-card';
            var domainBadge = q.math_domain
                ? '<span class="skill-tag">' + escapeHtml(q.math_domain) + '</span>'
                : '';
            card.innerHTML =
                '<div class="question-number">Pytanie ' + (idx + 1) + '</div>' +
                domainBadge +
                '<div class="question-text">' + escapeHtml(q.problem) + '</div>' +
                '<div class="fill-input">' +
                    '<input type="text" id="placement_input_' + q.id + '" class="fill-blank-input" ' +
                        'placeholder="Wpisz odpowied\u017A..." ' +
                        'oninput="onPlacementAnswer(' + q.id + ')">' +
                '</div>';
            container.appendChild(card);
        });
    }

    async function submitPlacement() {
        if (submitting) return;
        submitting = true;

        var btn = document.getElementById('btn-submit-placement');
        var origText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Wysy\u0142anie...';

        var total = document.querySelectorAll('#placement-questions .question-card').length;
        var answered = Object.keys(placementAnswers).length;
        if (answered < total) {
            setStatus('Odpowiedz na wszystkie ' + total + ' pyta\u0144. (' + answered + '/' + total + ')', 'error');
            btn.disabled = false;
            btn.textContent = origText;
            submitting = false;
            return;
        }

        var answers = Object.entries(placementAnswers).map(function (entry) {
            return { question_id: parseInt(entry[0]), answer: entry[1] };
        });

        var payload = { student_id: studentId, assessment_id: assessmentId, answers: answers };
        var endpoint = '/api/assessment/placement';
        console.log('[assessment] submit clicked \u2014 placement');
        console.log('[assessment] payload:', JSON.stringify(payload));
        console.log('[assessment] endpoint url:', window.API_BASE + endpoint);
        setStatus('Wysy\u0142anie odpowiedzi...', 'info');

        try {
            var resp = await apiFetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            console.log('[assessment] response status:', resp.status);

            if (!resp.ok) {
                var errMsg = await extractApiError(resp, 'Wysy\u0142anie klasyfikacji');
                setStatus(errMsg, 'error');
                btn.disabled = false;
                btn.textContent = origText;
                submitting = false;
                return;
            }

            var data = await STATE.safeJson(resp);
            console.log('[assessment] placement accepted \u2014 bracket:', data.placement_result && data.placement_result.bracket);
            setStatus('Klasyfikacja uko\u0144czona! \u0141adowanie diagnostyki...', 'success');
            showDiagnosticStage(data);
        } catch (e) {
            console.error('[assessment] submitPlacement error:', e);
            setStatus('B\u0142\u0105d sieci: ' + e.message, 'error');
            btn.disabled = false;
            btn.textContent = origText;
        } finally {
            submitting = false;
        }
    }

    function showDiagnosticStage(data) {
        document.getElementById('step-1').classList.remove('active');
        document.getElementById('step-1').classList.add('completed');
        document.getElementById('step-2').classList.add('active');

        document.getElementById('stage-placement').classList.add('hidden');
        document.getElementById('stage-diagnostic').classList.remove('hidden');

        var bracketLabels = {
            beginner: 'Pocz\u0105tkuj\u0105cy',
            intermediate: '\u015arednio\u200Bzaawansowany',
            advanced: 'Zaawansowany',
        };
        document.getElementById('bracket-display').textContent =
            bracketLabels[data.placement_result.bracket] || data.placement_result.bracket;
        document.getElementById('diagnostic-intro').innerHTML =
            'Na podstawie klasyfikacji zosta\u0142e\u015B/a\u015B przypisany/a do poziomu <strong>' + escapeHtml(bracketLabels[data.placement_result.bracket] || data.placement_result.bracket) + '</strong>. ' +
            'Odpowiedz na poni\u017Csze pytania, aby ustali\u0107 dok\u0142adny poziom matematyczny.';

        diagnosticQuestions = data.questions;
        renderDiagnosticQuestions(data.questions);
        clearStatus();
        window.scrollTo(0, 0);
    }

    function renderDiagnosticQuestions(questions) {
        var container = document.getElementById('diagnostic-questions');
        container.innerHTML = '';
        var questionNum = 0;

        questions.forEach(function (q) {
            questionNum++;
            var card = document.createElement('div');
            card.className = 'question-card';

            var skillBadge = '<span class="skill-tag skill-' + escapeHtml(q.skill) + '">' + escapeHtml(q.skill) + '</span>';
            var content = '<div class="question-header"><span class="question-number">P' + questionNum + '</span>' + skillBadge + '</div>';

            content += '<div class="question-text">' + escapeHtml(q.question) + '</div>';

            if (q.hint) {
                content += '<div class="question-hint"><em>Wskaz\u00f3wka: ' + escapeHtml(q.hint) + '</em></div>';
            }

            if (q.options && q.options.length) {
                content += '<div class="answer-options">';
                q.options.forEach(function (opt) {
                    content +=
                        '<label class="radio-label answer-label">' +
                            '<input type="radio" name="diag_' + q.id + '" value="' + escapeHtml(opt) + '" onchange="onDiagnosticAnswer(\'' + q.id + '\')">' +
                            '<span>' + escapeHtml(opt) + '</span>' +
                        '</label>';
                });
                content += '</div>';
            } else {
                content +=
                    '<div class="fill-input">' +
                        '<input type="text" id="diag_input_' + q.id + '" class="fill-blank-input" ' +
                            'placeholder="Wpisz odpowied\u017A..." ' +
                            'oninput="onDiagnosticAnswer(\'' + q.id + '\')">' +
                    '</div>';
            }

            card.innerHTML = content;
            container.appendChild(card);
        });
    }

    async function submitDiagnostic() {
        if (submitting) {
            console.log('[assessment] submitDiagnostic blocked \u2014 already submitting');
            return;
        }
        submitting = true;

        var btn = document.getElementById('btn-submit-diagnostic');
        var origText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Wysy\u0142anie...';

        var total = diagnosticQuestions.length;
        var answered = Object.keys(diagnosticAnswers).length;
        console.log('[assessment] submitDiagnostic \u2014 answered', answered, '/', total);

        if (answered < total) {
            setStatus('Odpowiedz na wszystkie ' + total + ' pyta\u0144. (' + answered + '/' + total + ')', 'error');
            btn.disabled = false;
            btn.textContent = origText;
            submitting = false;
            return;
        }

        var overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.classList.remove('hidden');

        var answers = Object.entries(diagnosticAnswers).map(function (entry) {
            return { question_id: entry[0], answer: entry[1] };
        });
        var payload = { student_id: studentId, assessment_id: assessmentId, answers: answers };
        var endpoint = '/api/assessment/diagnostic';
        console.log('[assessment] submit clicked \u2014 diagnostic');
        console.log('[assessment] student_id:', studentId, 'assessment_id:', assessmentId);
        console.log('[assessment] payload:', JSON.stringify(payload));
        console.log('[assessment] endpoint url:', window.API_BASE + endpoint);
        setStatus('Wysy\u0142anie diagnostyki \u2014 analiza AI w toku...', 'info');

        try {
            var resp = await apiFetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            console.log('[assessment] diagnostic response status:', resp.status);

            if (!resp.ok) {
                if (overlay) overlay.classList.add('hidden');
                var errMsg = await extractApiError(resp, 'B\u0142\u0105d przesy\u0142ania diagnostyki');
                console.error('[assessment] diagnostic error:', errMsg);
                setStatus(errMsg, 'error');
                btn.disabled = false;
                btn.textContent = origText;
                submitting = false;
                return;
            }

            var data = await STATE.safeJson(resp);
            console.log('[assessment] diagnostic response data:', JSON.stringify(data).substring(0, 500));
            console.log('[assessment] determined_level:', data.determined_level);
            console.log('[assessment] confidence_score:', data.confidence_score);
            console.log('[assessment] ai_error:', data.ai_error || 'none');

            if (overlay) overlay.classList.add('hidden');

            if (data.ai_error) {
                setStatus('Test oceniony (analiza AI niedost\u0119pna: ' + data.ai_error + ')', 'info');
            } else {
                setStatus('Test uko\u0144czony!', 'success');
            }

            showResults(data);

            // Trigger downstream pipeline (learner profile + learning path)
            triggerPostDiagnosticPipeline();
        } catch (e) {
            console.error('[assessment] submitDiagnostic network error:', e);
            if (overlay) overlay.classList.add('hidden');
            setStatus('B\u0142\u0105d sieci: ' + e.message + '. Czy backend dzia\u0142a?', 'error');
            btn.disabled = false;
            btn.textContent = origText;
        } finally {
            submitting = false;
        }
    }

    /**
     * After assessment completes, trigger downstream pipeline:
     * 1) Create learner profile (POST /api/diagnostic/{student_id})
     * 2) Generate learning path (POST /api/learning-path/{student_id}/generate)
     *
     * These are best-effort — failures don't block the results page.
     */
    async function triggerPostDiagnosticPipeline() {
        console.log('[assessment] triggerPostDiagnosticPipeline \u2014 student_id:', studentId);
        var pipelineEl = document.getElementById('pipeline-status');

        function setPipelineStatus(msg) {
            if (pipelineEl) pipelineEl.textContent = msg;
            console.log('[assessment] pipeline:', msg);
        }

        // Step 1: Create learner profile
        setPipelineStatus('Tworzenie profilu ucznia...');
        try {
            var profileResp = await apiFetch('/api/diagnostic/' + studentId, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (profileResp.ok) {
                var profileData = await STATE.safeJson(profileResp);
                console.log('[assessment] learner profile created:', JSON.stringify(profileData).substring(0, 300));
                setPipelineStatus('Profil ucznia utworzony. Generowanie \u015Bcie\u017Cki nauki...');
            } else {
                var profileErr = await extractApiError(profileResp, 'Profil ucznia');
                console.warn('[assessment] learner profile failed:', profileErr);
                setPipelineStatus('Profil ucznia: ' + profileErr + '. Generowanie \u015Bcie\u017Cki nauki...');
            }
        } catch (e) {
            console.warn('[assessment] learner profile network error:', e.message);
            setPipelineStatus('Profil ucznia niedost\u0119pny. Generowanie \u015Bcie\u017Cki nauki...');
        }

        // Step 2: Generate learning path
        try {
            var pathResp = await apiFetch('/api/learning-path/' + studentId + '/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (pathResp.ok) {
                var pathData = await STATE.safeJson(pathResp);
                console.log('[assessment] learning path generated:', JSON.stringify(pathData).substring(0, 300));
                setPipelineStatus('\u015acie\u017Cka nauki wygenerowana! Przejd\u017A do panelu, aby j\u0105 zobaczy\u0107.');
            } else {
                var pathErr = await extractApiError(pathResp, '\u015acie\u017Cka nauki');
                console.warn('[assessment] learning path failed:', pathErr);
                setPipelineStatus('\u015acie\u017Cka nauki: ' + pathErr);
            }
        } catch (e) {
            console.warn('[assessment] learning path network error:', e.message);
            setPipelineStatus('Generowanie \u015Bcie\u017Cki nauki niedost\u0119pne.');
        }
    }

    function showResults(data) {
        document.getElementById('step-2').classList.remove('active');
        document.getElementById('step-2').classList.add('completed');
        document.getElementById('step-3').classList.add('active');

        document.getElementById('stage-diagnostic').classList.add('hidden');
        document.getElementById('stage-results').classList.remove('hidden');

        document.getElementById('result-level').textContent = data.determined_level || '--';
        var confidence = data.confidence_score ? Math.round(data.confidence_score * 100) : 0;
        document.getElementById('result-confidence').textContent = confidence + '%';

        var skillsContainer = document.getElementById('skills-breakdown');
        skillsContainer.innerHTML = '';
        if (data.sub_skill_breakdown) {
            data.sub_skill_breakdown.forEach(function (skill) {
                var div = document.createElement('div');
                div.className = 'skill-bar-item';
                var score = Math.round(skill.score);
                div.innerHTML =
                    '<div class="skill-bar-header">' +
                        '<span class="skill-name">' + escapeHtml(skill.skill) + '</span>' +
                        '<span class="skill-score">' + score + '% (' + escapeHtml(skill.level) + ')</span>' +
                    '</div>' +
                    '<div class="progress-bar-container">' +
                        '<div class="progress-bar" style="width: ' + score + '%; background: ' + getScoreColor(score) + ';"></div>' +
                    '</div>' +
                    '<p class="skill-detail">' + escapeHtml(skill.details) + '</p>';
                skillsContainer.appendChild(div);
            });
        }

        if (data.scores) {
            var rawDiv = document.createElement('div');
            rawDiv.className = 'raw-scores';
            rawDiv.innerHTML =
                '<h4>Wyniki surowe</h4>' +
                '<div class="score-grid">' +
                    '<div class="score-item"><span class="score-label">Arytmetyka</span><span class="score-value">' + data.scores.arytmetyka + '%</span></div>' +
                    '<div class="score-item"><span class="score-label">Algebra</span><span class="score-value">' + data.scores.algebra + '%</span></div>' +
                    '<div class="score-item"><span class="score-label">Geometria</span><span class="score-value">' + data.scores.geometria + '%</span></div>' +
                    '<div class="score-item overall"><span class="score-label">Og\u00f3\u0142em</span><span class="score-value">' + data.scores.overall + '%</span></div>' +
                '</div>';
            skillsContainer.appendChild(rawDiv);
        }

        var weakList = document.getElementById('weak-areas');
        weakList.innerHTML = '';
        if (data.weak_areas && data.weak_areas.length) {
            data.weak_areas.forEach(function (area) {
                var li = document.createElement('li');
                li.textContent = area;
                weakList.appendChild(li);
            });
        } else {
            weakList.innerHTML = '<li>Nie zidentyfikowano istotnych s\u0142abych obszar\u00f3w.</li>';
        }

        var misconceptionsContainer = document.getElementById('math-misconceptions');
        misconceptionsContainer.innerHTML = '';
        if (data.common_misconceptions && data.common_misconceptions.length) {
            data.common_misconceptions.forEach(function (item) {
                var div = document.createElement('div');
                div.className = 'misconception-item';
                div.innerHTML =
                    '<strong>' + escapeHtml(item.area) + '</strong>' +
                    '<p>' + escapeHtml(item.description) + '</p>' +
                    (item.evidence ? '<p class="evidence"><em>Dow\u00f3d: ' + escapeHtml(item.evidence) + '</em></p>' : '');
                misconceptionsContainer.appendChild(div);
            });
        } else {
            misconceptionsContainer.innerHTML = '<p>Nie wykryto typowych b\u0142\u0119d\u00f3w matematycznych.</p>';
        }

        document.getElementById('result-summary').textContent = data.summary || 'Brak podsumowania.';

        var recList = document.getElementById('result-recommendations');
        recList.innerHTML = '';
        if (data.recommendations && data.recommendations.length) {
            data.recommendations.forEach(function (rec) {
                var li = document.createElement('li');
                li.textContent = rec;
                recList.appendChild(li);
            });
        }

        var returnTo = new URLSearchParams(window.location.search).get('return_to');
        if (returnTo === 'intake') {
            var actionsDiv = document.getElementById('result-actions');
            var continueLink = document.createElement('a');
            continueLink.href = 'index.html?student_id=' + studentId + '&from=assessment';
            continueLink.className = 'btn btn-primary';
            continueLink.textContent = 'Kontynuuj rejestracj\u0119 \u2192';
            actionsDiv.prepend(continueLink);
        }

        window.scrollTo(0, 0);
    }

    // ── Init ───────────────────────────────────────────────────────────

    document.addEventListener('DOMContentLoaded', function () {
        console.log('[assessment] DOMContentLoaded \u2014 wiring up');

        // Get student ID via STATE (URL param → localStorage fallback)
        studentId = STATE.requireStudentId();
        if (!studentId) return; // redirect already triggered

        console.log('[assessment] student_id:', studentId);

        // Wire submit buttons
        var btnPlacement = document.getElementById('btn-submit-placement');
        var btnDiagnostic = document.getElementById('btn-submit-diagnostic');

        if (btnPlacement) {
            btnPlacement.addEventListener('click', function (e) {
                e.preventDefault();
                console.log('[assessment] btn-submit-placement clicked');
                submitPlacement();
            });
        }
        if (btnDiagnostic) {
            btnDiagnostic.addEventListener('click', function (e) {
                e.preventDefault();
                console.log('[assessment] btn-submit-diagnostic clicked');
                submitDiagnostic();
            });
        }

        startAssessment();
    });
})();
