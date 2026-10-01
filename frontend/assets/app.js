const API = window.location.origin;

const state = {
  reports: [],
  health: null,
  filter: 'All',
  query: ''
};

const main = document.getElementById('main');
const topContext = document.getElementById('topContext');
const topDate = document.getElementById('topDate');
const popover = document.getElementById('notificationPopover');
const bellBtn = document.getElementById('bellBtn');
const bellDot = document.getElementById('bellDot');
const sidebar = document.getElementById('sidebar');
const studentModal = document.getElementById('studentModal');


/* =========================================================
   LABELS
   ========================================================= */

const featureLabels = {
  attendance_percentage: 'Attendance',
  assignment_submission_rate: 'Assignment Submission',
  quiz_average_score: 'Quiz Average',
  midterm_score: 'Midterm Score',
  previous_gpa: 'Previous GPA',
  late_submission_count: 'Late Submissions',
  missing_assignment_count: 'Missing Assignments',
  study_plan_adherence: 'Study Plan Adherence'
};

const backendFeatureLabels = {
  Attendance_Percentage: 'Attendance',
  Assignment_Submission_Rate: 'Assignment Submission',
  Quiz_Average_Score: 'Quiz Average',
  Midterm_Score: 'Midterm Score',
  Previous_GPA: 'Previous GPA',
  Late_Submission_Count: 'Late Submissions',
  Missing_Assignment_Count: 'Missing Assignments',
  Study_Plan_Adherence: 'Study Plan Adherence'
};


/* =========================================================
   SVG ICONS
   ========================================================= */

const svgArrow = `
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M5 12h14M13 6l6 6-6 6"/>
  </svg>
`;

const svgClose = `
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="m6 6 12 12M18 6 6 18"/>
  </svg>
`;

const svgBell = `
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/>
    <path d="M10 21h4"/>
  </svg>
`;


/* =========================================================
   HELPERS
   ========================================================= */

function esc(s = '') {
  return String(s).replace(
    /[&<>'"]/g,
    c => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[c])
  );
}


/* =========================================================
   POLICY LINK CLEANING
   ========================================================= */

function normalizePolicyUrls(text = '') {
  let raw = String(text);

  /*
   PDF extraction can split URLs like:

   https://example.com/ai-
   principles.pdf

   Join them again.
  */

  raw = raw.replace(
    /(https?:\/\/[^\s<>"']+)-\s*\n\s*([A-Za-z0-9])/g,
    '$1-$2'
  );

  /*
   Also repair some URL line breaks where no hyphen is present.
  */

  raw = raw.replace(
    /(https?:\/\/[^\s<>"']+)\s*\n\s*([A-Za-z0-9][^\s<>"']*)/g,
    (match, first, second) => {
      if (
        second.includes('/') ||
        second.includes('.') ||
        second.includes('?') ||
        second.includes('=')
      ) {
        return first + second;
      }

      return match;
    }
  );

  return raw;
}


function linkifyText(text = '') {
  const raw = normalizePolicyUrls(text);

  const regex = /https?:\/\/[^\s<>"']+/g;

  let html = '';
  let last = 0;

  for (const match of raw.matchAll(regex)) {
    let url = match[0];
    let trail = '';

    /*
     Remove punctuation that belongs to the sentence
     rather than the URL itself.
    */

    while (/[),.;:]$/.test(url)) {
      trail = url.slice(-1) + trail;
      url = url.slice(0, -1);
    }

    html += esc(raw.slice(last, match.index));

    html += `
      <a
        class="inline-source-link"
        href="${esc(url)}"
        target="_blank"
        rel="noopener noreferrer"
      >
        Open source ↗
      </a>${esc(trail)}
    `;

    last = match.index + match[0].length;
  }

  return html + esc(raw.slice(last));
}


/*
 Remove the source/citation that is embedded inside
 policy content itself.

 We already show the clean source separately below
 using p.source / r.source.
*/

function cleanPolicyContent(text = '') {
  let content = String(text);

  content = content.replace(
    /\s*Extracted from:[\s\S]*$/i,
    ''
  );

  return content.trim();
}


/* =========================================================
   RISK HELPERS
   ========================================================= */

function riskClass(r) {
  return r.startsWith('High')
    ? 'high'
    : r.startsWith('Medium')
      ? 'medium'
      : 'low';
}


function riskBadge(r) {
  return `
    <span class="risk ${riskClass(r)}">
      ${esc(r)}
    </span>
  `;
}


function pct(v, d = 0) {
  return `${(Number(v) * 100).toFixed(d)}%`;
}


function rawPct(v) {
  const number = Number(v);

  return `${number.toFixed(
    number % 1 === 0 ? 0 : 2
  )}%`;
}


function formatTime(s) {
  try {
    return new Date(s).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  } catch {
    return '—';
  }
}


function humanFeature(name) {
  return (
    backendFeatureLabels[name] ||
    featureLabels[name] ||
    String(name).replaceAll('_', ' ')
  );
}


function riskRank(risk) {
  if (risk.startsWith('High')) return 0;
  if (risk.startsWith('Medium')) return 1;

  return 2;
}


/*
 Sort:
 High Risk
 ↓
 Medium Risk
 ↓
 Low Risk

 Then highest probability first inside each category.
*/

function sortedReports(list = state.reports) {
  return [...list].sort(
    (a, b) =>
      riskRank(a.risk_level) -
        riskRank(b.risk_level) ||

      Number(b.risk_probability) -
        Number(a.risk_probability) ||

      a.student_id.localeCompare(b.student_id)
  );
}


/* =========================================================
   DATE / SEMESTER
   ========================================================= */

function getSemester(month) {
  if (month >= 7) return 'Fall Semester';
  if (month >= 5) return 'Summer Semester';

  return 'Spring Semester';
}


function updateDate() {
  const now = new Date();

  const date = now.toLocaleDateString([], {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric'
  });

  topDate.innerHTML = `
    <span class="date-line">${esc(date)}</span>
    <span class="semester-line">
      ${esc(getSemester(now.getMonth()))}
    </span>
  `;
}


/* =========================================================
   API
   ========================================================= */

async function getJson(url, opts) {
  const response = await fetch(url, opts);

  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({}));

    throw new Error(
      body.detail ||
      `Request failed (${response.status})`
    );
  }

  return response.json();
}


/* =========================================================
   ROUTING
   ========================================================= */

function nav(path) {
  closeStudentModal();

  history.pushState({}, '', path);

  route();

  sidebar.classList.remove('open');
}


document.addEventListener('click', e => {
  const a = e.target.closest('a[data-route]');

  if (!a) return;

  e.preventDefault();

  nav(a.getAttribute('href'));
});


window.addEventListener(
  'popstate',
  route
);


document
  .getElementById('menuBtn')
  .addEventListener(
    'click',
    () => sidebar.classList.toggle('open')
  );


/* =========================================================
   NOTIFICATIONS
   ========================================================= */

function getNotificationCount() {
  const hasHigh =
    state.reports.some(
      s => s.risk_level === 'High Risk'
    );

  const hasMedium =
    state.reports.some(
      s => s.risk_level === 'Medium Risk'
    );

  /*
   This represents actual notification categories.

   Example:
   High Risk exists = 1
   Medium Risk exists = 1

   Badge = 2
  */

  return Number(hasHigh) + Number(hasMedium);
}


function updateNotificationBadge() {
  const count = getNotificationCount();

  bellDot.textContent =
    count > 0 ? String(count) : '';

  bellDot.style.display =
    count > 0 ? 'grid' : 'none';
}


function renderNotifications() {
  const highs = sortedReports(
    state.reports.filter(
      s => s.risk_level === 'High Risk'
    )
  );

  const mediums = sortedReports(
    state.reports.filter(
      s => s.risk_level === 'Medium Risk'
    )
  );

  popover.innerHTML = `
    <div class="popover-head">

      <div>
        <span class="popover-kicker">
          Notifications
        </span>

        <h4>
          Advisor review signals
        </h4>
      </div>

      <button
        class="mark-read"
        type="button"
      >
        Mark all as read
      </button>

    </div>

    ${
      highs.length
        ? `
          <div class="notification-row">

            <span class="notification-dot high-dot">
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 3 2.8 19h18.4L12 3Z"/>
    <path d="M12 9v4M12 17h.01"/>
  </svg>
</span>

            <div>
              <strong>
                ${highs.length}
                High Risk signal${highs.length === 1 ? '' : 's'}
              </strong>

              <p>
                Flagged for advisor review.
                Final decisions remain with you.
              </p>
            </div>

          </div>
        `
        : `
          <div class="notification-row">

            <span
              class="notification-dot low-dot">
            </span>

            <div>
              <strong>
                No High Risk signals
              </strong>

              <p>
                No students are currently flagged
                by the High Risk alert rule.
              </p>
            </div>

          </div>
        `
    }

    ${
      mediums.length
        ? `
          <div class="notification-row">

            <span class="notification-dot medium-dot">
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="12" r="9"/>
    <path d="M12 7v5l3 2"/>
  </svg>
</span>

            <div>
              <strong>
                ${mediums.length}
                Medium Risk signal${mediums.length === 1 ? '' : 's'}
              </strong>

              <p>
                Available for review in the
                current student view.
              </p>
            </div>

          </div>
        `
        : ''
    }
  `;
}


/*
 Bell itself is clickable.

 Notification rows are intentionally NOT clickable.
*/

bellBtn.addEventListener(
  'click',
  () => {
    renderNotifications();

    popover.classList.toggle('hidden');

    bellBtn.setAttribute(
      'aria-expanded',
      String(
        !popover.classList.contains('hidden')
      )
    );
  }
);


document.addEventListener(
  'click',
  e => {
    if (
      !e.target.closest('#bellBtn') &&
      !e.target.closest('#notificationPopover')
    ) {
      popover.classList.add('hidden');

      bellBtn.setAttribute(
        'aria-expanded',
        'false'
      );
    }
  }
);


/* =========================================================
   STUDENT LIST MODAL
   ========================================================= */

function modalTitle(kind) {
  if (kind === 'High') {
    return 'High Risk signals';
  }

  if (kind === 'Medium') {
    return 'Medium Risk signals';
  }

  return 'Students in view';
}


function openStudentModal(kind = 'All') {
  let list = state.reports;

  if (kind === 'High') {
    list = list.filter(
      s => s.risk_level === 'High Risk'
    );
  }

  if (kind === 'Medium') {
    list = list.filter(
      s => s.risk_level === 'Medium Risk'
    );
  }

  list = sortedReports(list);

  studentModal.innerHTML = `
    <div
      class="modal-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modalTitle"
    >

      <div class="modal-head">

        <div>
          <div class="eyebrow">
            STUDENT VIEW
          </div>

          <h2 id="modalTitle">
            ${esc(modalTitle(kind))}
          </h2>

          <p>
            ${
              kind === 'All'
                ? 'All assigned students, prioritized by signal and probability.'
                : `${list.length} student${list.length === 1 ? '' : 's'} with ${kind} Risk signals, ordered by probability.`
            }
          </p>
        </div>

        <button
          class="modal-close"
          id="modalClose"
          aria-label="Close student list"
        >
          ${svgClose}
        </button>

      </div>

      <div class="modal-list">

        ${
          list.length
            ? list.map((s, i) => `
              <button
                class="modal-student"
                data-modal-student="${esc(s.student_id)}"
              >

                <span class="modal-rank">
                  ${String(i + 1).padStart(2, '0')}
                </span>

                <span class="modal-student-main">
                  <strong>
                    ${esc(s.student_id)}
                  </strong>

                  <small>
                    Course year ${esc(s.course_year)}
                  </small>
                </span>

                <span>
                  ${riskBadge(s.risk_level)}
                </span>

                <span class="modal-prob">
                  <strong>
                    ${pct(s.risk_probability)}
                  </strong>

                  <small>
                    probability
                  </small>
                </span>

                <span class="modal-arrow">
                  ${svgArrow}
                </span>

              </button>
            `).join('')
            : `
              <div class="empty">
                No students are currently
                in this category.
              </div>
            `
        }

      </div>

      <div class="modal-footer">
        AI-generated signals support advisor review;
        they do not determine interventions.
      </div>

    </div>
  `;

  studentModal.classList.remove('hidden');

  studentModal.setAttribute(
    'aria-hidden',
    'false'
  );

  document.body.classList.add(
    'modal-open'
  );

  const closeButton =
    document.getElementById('modalClose');

  closeButton.focus();

  closeButton.onclick =
    closeStudentModal;

  studentModal
    .querySelectorAll('[data-modal-student]')
    .forEach(button => {
      button.onclick = () =>
        nav(
          `/students/${encodeURIComponent(
            button.dataset.modalStudent
          )}`
        );
    });
}


function closeStudentModal() {
  studentModal.classList.add('hidden');

  studentModal.setAttribute(
    'aria-hidden',
    'true'
  );

  document.body.classList.remove(
    'modal-open'
  );

  studentModal.innerHTML = '';
}


studentModal.addEventListener(
  'click',
  e => {
    if (e.target === studentModal) {
      closeStudentModal();
    }
  }
);


document.addEventListener(
  'keydown',
  e => {
    if (
      e.key === 'Escape' &&
      !studentModal.classList.contains('hidden')
    ) {
      closeStudentModal();
    }
  }
);


/* =========================================================
   BOOTSTRAP
   ========================================================= */

async function bootstrap() {
  updateDate();

  main.innerHTML = `
    <div class="page">

      <div class="card system-state">

        <div class="loader">
          <span class="spinner"></span>

          Connecting to ASAP services…
        </div>

      </div>

    </div>
  `;

  try {
    state.health =
      await getJson(`${API}/health`);

    if (
      !state.health.model_loaded ||
      !state.health.policy_store_loaded
    ) {
      return renderSystemState();
    }

    const data =
      await getJson(
        `${API}/caseload/predictions`
      );

    state.reports = data.students;

    updateNotificationBadge();

    route();

  } catch (err) {
    state.health = {
      status: 'error',
      error: err.message
    };

    renderSystemState();
  }
}


/* =========================================================
   SYSTEM STATUS
   ========================================================= */

function renderSystemState() {
  topContext.textContent = 'ASAP';

  main.innerHTML = `
    <div class="page">

      <div class="card system-state">

        <div class="eyebrow">
          SYSTEM STATUS
        </div>

        <h2>
          ASAP services are not ready
        </h2>

        <p class="state-copy">
          The advisor console will not substitute
          mock predictions while backend services
          are unavailable.
        </p>

        <div class="service-row">
          <span>
            Model service
          </span>

          <strong
            class="${
              state.health?.model_loaded
                ? 'status-ok'
                : 'status-bad'
            }"
          >
            ${
              state.health?.model_loaded
                ? 'Ready'
                : 'Unavailable'
            }
          </strong>
        </div>

        <div class="service-row">
          <span>
            Policy library
          </span>

          <strong
            class="${
              state.health?.policy_store_loaded
                ? 'status-ok'
                : 'status-bad'
            }"
          >
            ${
              state.health?.policy_store_loaded
                ? 'Ready'
                : 'Unavailable'
            }
          </strong>
        </div>

        <div class="btn-row">
          <button
            class="btn primary"
            id="retryBtn"
          >
            Retry connection
          </button>
        </div>

      </div>

    </div>
  `;

  document
    .getElementById('retryBtn')
    .onclick = bootstrap;
}


/* =========================================================
   NAVIGATION STATE
   ========================================================= */

function setNav() {
  document
    .querySelectorAll('.nav-item')
    .forEach(a => {
      const active =
        a.getAttribute('href') === location.pathname ||

        (
          location.pathname.startsWith('/students/') &&
          a.getAttribute('href') === '/'
        );

      a.classList.toggle(
        'active',
        active
      );
    });
}


/* =========================================================
   ROUTER
   ========================================================= */

function route() {
  updateDate();

  setNav();

  popover.classList.add('hidden');

  bellBtn.setAttribute(
    'aria-expanded',
    'false'
  );

  window.scrollTo({
    top: 0,
    behavior: 'instant'
  });

  if (location.pathname === '/policy') {
    return renderPolicy();
  }

  if (location.pathname === '/oversight') {
    return renderOversight();
  }

  if (
    location.pathname.startsWith('/students/')
  ) {
    return renderStudent(
      decodeURIComponent(
        location.pathname.split('/').pop()
      )
    );
  }

  renderDashboard();
}


/* =========================================================
   COMMAND CENTER
   ========================================================= */

function renderDashboard() {
  /*
   Top header says only ASAP.
   Hero eyebrow says COMMAND CENTER.
  */

  topContext.textContent = 'ASAP';

  const high = state.reports.filter(
    s => s.risk_level === 'High Risk'
  ).length;

  const medium = state.reports.filter(
    s => s.risk_level === 'Medium Risk'
  ).length;

  main.innerHTML = `
    <div class="page dashboard-page">

      <section class="hero-row compact-hero">

        <div class="hero">

          <div class="eyebrow">
            COMMAND CENTER
          </div>

          <h1>
            Good morning,
            <span class="gradient-name">
              Sara
            </span>
          </h1>

          <p>
            A summary of model-generated academic
            risk signals across your assigned students.
            <br>

            Final review and decisions remain with you.
          </p>

        </div>

      </section>


      <section
        class="metrics"
        aria-label="Risk summary"
      >

        <!-- STATIC: NOT CLICKABLE -->

        <div
          class="metric metric-static"
          aria-label="Students in view summary"
        >

          <span
            class="metric-icon students-icon"
          >
            <svg viewBox="0 0 24 24">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
          </span>

          <span class="metric-label">
            Students in view
          </span>

          <span class="metric-value">
            ${state.reports.length}
          </span>

          <span class="metric-sub">
            Assigned students
          </span>

        </div>


        <!-- HIGH RISK: CLICKABLE -->

        <button
          class="metric metric-action high"
          data-metric="High"
          aria-label="View High Risk students"
        >

          <span
            class="metric-icon high-icon"
          >
            <svg viewBox="0 0 24 24">
              <path d="M12 3 2.8 19h18.4L12 3Z"/>
              <path d="M12 9v4M12 17h.01"/>
            </svg>
          </span>

          <span class="metric-label">
            High Risk alerts
          </span>

          <span class="metric-value">
            ${high}
          </span>

          <span class="metric-sub">
            Flagged for advisor review
          </span>

          <span class="metric-cta">
            View High Risk
            ${svgArrow}
          </span>

        </button>


        <!-- MEDIUM RISK: CLICKABLE -->

        <button
          class="metric metric-action medium"
          data-metric="Medium"
          aria-label="View Medium Risk students"
        >

          <span
            class="metric-icon medium-icon"
          >
            <svg viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="9"/>
              <path d="M12 7v5l3 2"/>
            </svg>
          </span>

          <span class="metric-label">
            Medium Risk
          </span>

          <span class="metric-value">
            ${medium}
          </span>

          <span class="metric-sub">
            Signals available for review
          </span>

          <span class="metric-cta">
            View Medium Risk
            ${svgArrow}
          </span>

        </button>

      </section>


      <section class="card queue">

        <div class="queue-head">

          <div class="queue-title">

            <h2>
              Student list

              <span
                class="count-pill"
                id="visibleCount"
              >
                ${state.reports.length}
              </span>
            </h2>

            <p>
              Prioritized by risk signal,
              then highest prediction probability.
            </p>

          </div>


          <div class="controls">

            <div class="search">

              <input
                id="studentSearch"
                aria-label="Find student ID"
                placeholder="Find student ID"
                value="${esc(state.query)}"
              >

            </div>


            <div class="filters">

              ${['All', 'High', 'Medium', 'Low']
                .map(
                  f => `
                    <button
                      class="filter ${
                        state.filter === f
                          ? 'active'
                          : ''
                      }"
                      data-filter="${f}"
                    >
                      ${f}
                    </button>
                  `
                )
                .join('')}

            </div>

          </div>

        </div>


        <div class="table-wrap">

          <table class="table">

            <thead>
              <tr>
                <th>#</th>
                <th>Student</th>
                <th>Risk signal</th>
                <th>Probability</th>
                <th>Primary factor</th>
                <th>Last generated</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody id="studentRows"></tbody>

          </table>

        </div>

      </section>

    </div>
  `;


  const refreshRows = () => {
    const q =
      state.query
        .trim()
        .toLowerCase();

    const list = sortedReports(
      state.reports.filter(
        s =>
          (
            state.filter === 'All' ||
            s.risk_level.startsWith(state.filter)
          ) &&

          (
            !q ||
            s.student_id
              .toLowerCase()
              .includes(q)
          )
      )
    );


    document
      .getElementById('visibleCount')
      .textContent = list.length;


    document
      .getElementById('studentRows')
      .innerHTML = list.length
        ? list.map((s, index) => {
            const factor =
              s.contributing_factors?.[0];

            return `
              <tr
                data-row-student="${esc(s.student_id)}"
              >

                <td class="rank-cell">
                  ${index + 1}
                </td>


                <td>

                  <div class="student-cell">

                    <div class="student-icon">
                      ST
                    </div>

                    <div>

                      <a
                        href="/students/${encodeURIComponent(s.student_id)}"
                        data-route
                        class="student-id"
                      >
                        ${esc(s.student_id)}
                      </a>

                      <div class="student-year">
                        Course Year
                        ${esc(s.course_year)}
                      </div>

                    </div>

                  </div>

                </td>


                <td>
                  ${riskBadge(s.risk_level)}
                </td>


                <td class="prob">

                  <strong>
                    ${pct(s.risk_probability)}
                  </strong>

                  <div class="prob-track">

                    <div
                      class="prob-fill ${riskClass(s.risk_level)}"
                      style="width:${s.risk_probability * 100}%"
                    >
                    </div>

                  </div>

                </td>


                <td>

                  <div class="context-main">
                    ${
                      factor
                        ? esc(humanFeature(factor.feature))
                        : '—'
                    }
                  </div>

                  <div class="context-sub">
                    ${
                      factor
                        ? esc(
                            factor.direction
                              .replaceAll('_', ' ')
                          )
                        : 'No factor returned'
                    }
                  </div>

                </td>


                <td class="time">
                  ${formatTime(
                    s.prediction_timestamp_utc
                  )}
                </td>


                <td>

                  <button
                    class="review-link"
                    data-student="${esc(s.student_id)}"
                  >
                    Review
                    ${svgArrow}
                  </button>

                </td>

              </tr>
            `;
          }).join('')
        : `
          <tr>
            <td colspan="7">

              <div class="empty">
                No students match this view.
              </div>

            </td>
          </tr>
        `;


    document
      .querySelectorAll('[data-student]')
      .forEach(button => {
        button.onclick = () =>
          nav(
            `/students/${encodeURIComponent(
              button.dataset.student
            )}`
          );
      });
  };


  document
    .getElementById('studentSearch')
    .oninput = e => {
      state.query = e.target.value;

      refreshRows();
    };


  document
    .querySelectorAll('[data-filter]')
    .forEach(button => {
      button.onclick = () => {
        state.filter =
          button.dataset.filter;

        renderDashboard();
      };
    });


  document
    .querySelectorAll('[data-metric]')
    .forEach(button => {
      button.onclick = () =>
        openStudentModal(
          button.dataset.metric
        );
    });


  refreshRows();
}


/* =========================================================
   STUDENT REVIEW
   ========================================================= */

function renderStudent(id) {
  const student =
    state.reports.find(
      x => x.student_id === id
    );


  if (!student) {
    main.innerHTML = `
      <div class="page">

        <div class="card not-found">

          <h3>
            Student not found
          </h3>

          <p>
            This student is not part of
            the current assigned view.
          </p>

          <a
            href="/"
            data-route
            class="btn"
          >
            Back to Command Center
          </a>

        </div>

      </div>
    `;

    return;
  }


  topContext.textContent = 'ASAP';


  const features = [
    ['attendance_percentage', true],
    ['assignment_submission_rate', true],
    ['quiz_average_score', true],
    ['midterm_score', true],
    ['previous_gpa', false],
    ['late_submission_count', false],
    ['missing_assignment_count', false],
    ['study_plan_adherence', true]
  ];


  const maxContribution =
    Math.max(
      ...student.contributing_factors.map(
        f => Math.abs(f.contribution)
      ),
      0.001
    );


  main.innerHTML = `
    <div class="page">

      <a
        href="/"
        data-route
        class="back"
      >
        ← Back to Command Center
      </a>


      <div class="detail-head">

        <div class="student-title">

          <div class="student-icon">
            ST
          </div>

          <div>

            <div class="eyebrow">
              STUDENT REVIEW / COURSE YEAR
              ${esc(student.course_year)}
            </div>

            <h1>
              ${esc(student.student_id)}
            </h1>

            <p>
              Model-generated signal profile
              for advisor review
            </p>

          </div>

        </div>


        <div class="signal-side">

          <div class="eyebrow">
            CURRENT SIGNAL
          </div>

          <div class="signal-badges">

            ${riskBadge(student.risk_level)}

            ${
              student.high_risk_alert
                ? `
                  <span class="risk high">
                    High-Risk alert
                  </span>
                `
                : ''
            }

          </div>

        </div>

      </div>


      <div class="detail-grid">

        <section class="card signal-card">

          <div class="card-head">

            <div>

              <div class="eyebrow card-eyebrow">
                SIGNAL PROFILE
              </div>

              <h2>
                What the model is seeing
              </h2>

            </div>

            <div class="meta">
              Signal v${esc(student.model_version)}
              <br>

              ${formatTime(
                student.prediction_timestamp_utc
              )}
            </div>

          </div>


          <div class="features">

            ${features.map(([key, isPercent]) => `
              <div class="feature">

                <div class="feature-label">
                  ${featureLabels[key]}
                </div>

                <div class="feature-value">
                  ${
                    isPercent
                      ? rawPct(student[key])
                      : Number(student[key]).toFixed(
                          key === 'previous_gpa'
                            ? 2
                            : 0
                        )
                  }
                </div>

              </div>
            `).join('')}

          </div>


          <div class="tabs">

            <button
              class="tab active"
              data-tab="factors"
            >
              Contributing factors
            </button>

            <button
              class="tab"
              data-tab="context"
            >
              Context &amp; oversight
            </button>

          </div>


          <div
            id="factorsPanel"
            class="tab-panel"
          >

            ${student.contributing_factors
              .map(
                factor => `
                  <div class="factor">

                    <div class="factor-name">
                      ${esc(
                        humanFeature(
                          factor.feature
                        )
                      )}
                    </div>

                    <div class="factor-bar">

                      <div
                        class="factor-fill"
                        style="
                          width:${
                            Math.max(
                              8,
                              Math.abs(
                                factor.contribution
                              ) /
                              maxContribution *
                              100
                            )
                          }%
                        "
                      >
                      </div>

                    </div>

                    <div class="factor-dir">
                      ${esc(
                        factor.direction
                          .replaceAll('_', ' ')
                      )}

                      <br>

                      ${Number(
                        factor.contribution
                      ).toFixed(2)}
                    </div>

                  </div>
                `
              )
              .join('')}

          </div>


          <div
            id="contextPanel"
            class="tab-panel method-section hidden"
          >

            <h4>
              Model note
            </h4>

            <p>
              ${esc(student.explainability_note)}
            </p>


            <h4>
              Human oversight
            </h4>

            <p>
              ${esc(student.human_oversight_notice)}
            </p>


            <h4>
              Policy context
            </h4>


            ${
              student.policy_context.length
                ? student.policy_context
                    .map(
                      policy => `
                        <div class="policy-mini">

                          <strong>
                            ${esc(policy.title)}
                          </strong>

                          <p>
                            ${
                              linkifyText(
                                cleanPolicyContent(
                                  policy.content
                                )
                              )
                            }
                          </p>

                          <div class="policy-source-line">
                            ${
                              linkifyText(
                                policy.source
                              )
                            }
                          </div>

                        </div>
                      `
                    )
                    .join('')
                : `
                  <p>
                    No relevant policy context returned.
                  </p>
                `
            }

          </div>

        </section>


        <aside class="side-stack">

          <section class="card prob-card">

            <h3>
              Risk probability
            </h3>

            <div class="big-prob">
              ${pct(student.risk_probability)}
            </div>

            <div class="progress">

              <div
                style="
                  width:${student.risk_probability * 100}%
                "
              >
              </div>

            </div>

            <div class="prob-foot">

              <span>
                Predicted-class probability
              </span>

              <span>
                Not an intervention decision
              </span>

            </div>

            <button
              class="btn small"
              id="probToggle"
            >
              View class probabilities
            </button>


            <div
              id="classProbs"
              class="class-probs"
            >

              ${Object.entries(
                student.class_probabilities
              )
                .map(
                  ([key, value]) => `
                    <div class="class-row">

                      <span>
                        ${esc(key)}
                      </span>

                      <div class="mini-progress">

                        <div
                          style="
                            width:${value * 100}%
                          "
                        >
                        </div>

                      </div>

                      <strong>
                        ${pct(value)}
                      </strong>

                    </div>
                  `
                )
                .join('')}

            </div>

          </section>


          <section class="card checkpoint">

            <div class="checkpoint-icon">

              <svg viewBox="0 0 24 24">

                <path d="M12 3 20 6v5c0 5.2-3.4 8.5-8 10-4.6-1.5-8-4.8-8-10V6l8-3Z"/>

                <path d="m9 12 2 2 4-4"/>

              </svg>

            </div>


            <div>

              <h3>
                Human review checkpoint
              </h3>

              <p>
                AI-generated risk signal.
                Final review and decisions remain
                with the advisor.
              </p>

              <a
                href="/oversight"
                data-route
              >
                How oversight works →
              </a>

            </div>

          </section>

        </aside>

      </div>

    </div>
  `;


  document
    .querySelectorAll('[data-tab]')
    .forEach(button => {
      button.onclick = () => {

        document
          .querySelectorAll('.tab')
          .forEach(
            tab => tab.classList.remove('active')
          );

        button.classList.add('active');

        document
          .getElementById('factorsPanel')
          .classList.toggle(
            'hidden',
            button.dataset.tab !== 'factors'
          );

        document
          .getElementById('contextPanel')
          .classList.toggle(
            'hidden',
            button.dataset.tab !== 'context'
          );
      };
    });


  document
    .getElementById('probToggle')
    .onclick = () =>
      document
        .getElementById('classProbs')
        .classList.toggle('open');
}


/* =========================================================
   POLICY LIBRARY
   ========================================================= */

function renderPolicy() {
  topContext.textContent = 'ASAP';


  main.innerHTML = `
    <div class="page">

      <section class="policy-hero">

        <div class="eyebrow">
          POLICY LIBRARY
        </div>

        <h1>
          Policy, at the moment
          <br>

          <span class="blue-text">
            you need context.
          </span>
        </h1>

        <p>
          Search the policy library in plain language.
          Results are reference material for advisor
          review, with sources attached.
        </p>

      </section>


      <form
        class="policy-search"
        id="policyForm"
      >

        <div class="policy-input-wrap">

          <svg
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7"/>
            <path d="m20 20-3.5-3.5"/>
          </svg>

          <input
            id="policyInput"
            aria-label="Policy question"
            placeholder="Ask a policy-related question…"
            value=""
          >

        </div>

        <button
          class="btn primary"
          type="submit"
        >
          Search library
        </button>

      </form>


      <div class="chips">

        <button class="chip">
          What does the guidance say about human oversight?
        </button>

        <button class="chip">
          What does the policy say about minimal data use?
        </button>

        <button class="chip">
          What does the guidance say about accountability and responsibility?
        </button>

      </div>


      <div id="policyResult"></div>

    </div>
  `;


  const form =
    document.getElementById('policyForm');

  const input =
    document.getElementById('policyInput');

  const result =
    document.getElementById('policyResult');


  document
    .querySelectorAll('.chip')
    .forEach(chip => {
      chip.onclick = () => {
        input.value =
          chip.textContent.trim();

        form.requestSubmit();
      };
    });


  form.onsubmit = async e => {
    e.preventDefault();

    const query =
      input.value.trim();

    if (!query) return;


    result.innerHTML = `
      <div class="card policy-loading">

        <div class="loader">
          <span class="spinner"></span>

          Searching the grounded policy library…
        </div>

      </div>
    `;


    try {
      const data =
        await getJson(
          `${API}/policy/query`,
          {
            method: 'POST',

            headers: {
              'Content-Type':
                'application/json'
            },

            body: JSON.stringify({
              query,
              top_k: 3
            })
          }
        );


      if (!data.found) {
        result.innerHTML = `
          <div class="card not-found">

            <h3>
              No sufficiently relevant
              policy guidance found
            </h3>

            <p>
              ${
                esc(
                  data.note ||
                  'The current knowledge base did not return evidence for this query. Try another policy-related question.'
                )
              }
            </p>

          </div>
        `;

        return;
      }


      result.innerHTML = `
        <section class="card policy-result">

          <div class="result-head">

            <div>

              <div class="eyebrow result-eyebrow">
                RETRIEVED GUIDANCE
              </div>

              <h2>
                ${esc(data.query)}
              </h2>

            </div>

            <span class="source-count">
              ${data.results.length}
              source${data.results.length === 1 ? '' : 's'}
            </span>

          </div>


          <div class="result-grid">

            <div class="evidence">

              ${data.results
                .map(
                  (item, index) => `
                    <article class="evidence-item">

                      <div class="evidence-index">
                        ${String(index + 1).padStart(2, '0')}
                      </div>

                      <div>

                        <h3>
                          ${esc(item.title)}
                        </h3>

                        <p>
                          ${
                            linkifyText(
                              cleanPolicyContent(
                                item.content
                              )
                            )
                          }
                        </p>

                      </div>

                    </article>
                  `
                )
                .join('')}

            </div>


            <aside class="sources">

              <div class="sources-title">
                Sources
              </div>

              ${data.results
                .map(
                  (item, index) => `
                    <div class="source">

                      <strong>
                        ${String(index + 1).padStart(2, '0')}
                        ·
                        ${esc(item.title)}
                      </strong>

                      <div>
                        ${
                          linkifyText(
                            item.source
                          )
                        }
                      </div>

                      <span>
                        Relevance
                        ${Number(
                          item.relevance_score
                        ).toFixed(3)}
                      </span>

                    </div>
                  `
                )
                .join('')}

            </aside>

          </div>

        </section>
      `;

    } catch (err) {
      result.innerHTML = `
        <div class="card not-found">

          <h3>
            Policy search failed
          </h3>

          <p>
            ${esc(err.message)}.
            Please retry.
          </p>

        </div>
      `;
    }
  };
}


/* =========================================================
   MODEL & OVERSIGHT
   ========================================================= */

function renderOversight() {
  topContext.textContent = 'ASAP';


  main.innerHTML = `
    <div class="page">

      <section class="oversight-hero">

        <div class="eyebrow">
          MODEL &amp; OVERSIGHT
        </div>

        <h1>
          Transparent signals.
          <br>

          <span class="blue-text">
            Human decisions.
          </span>
        </h1>

        <p>
          ASAP supports academic advisors with
          model-generated risk signals and
          source-grounded policy context.
          It does not automate intervention decisions.
        </p>

      </section>


      <div class="oversight-grid">


        <section class="card info-card">

          <div class="info-icon blue">

            <svg viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="9"/>
              <path d="M12 11v6M12 7h.01"/>
            </svg>

          </div>

          <h2>
            About the signal
          </h2>

          <p>
            ASAP predicts one of three academic
            risk classes — Low Risk, Medium Risk,
            or High Risk — to support advisor review.

            The prediction is a decision-support
            signal, not a verdict about a student.
          </p>

        </section>


        <section class="card info-card">

          <div class="info-icon cyan">

            <svg viewBox="0 0 24 24">
              <path d="M12 3 20 6v5c0 5.2-3.4 8.5-8 10-4.6-1.5-8-4.8-8-10V6l8-3Z"/>
              <path d="m9 12 2 2 4-4"/>
            </svg>

          </div>

          <h2>
            What the model does not use
          </h2>

          <ul>
            <li>
              Student ID is display/linking
              context only.
            </li>

            <li>
              Course Year is advisor-facing
              context only.
            </li>

            <li>
              Policy documents do not train
              the ML model.
            </li>
          </ul>

        </section>


        <section class="card info-card">

          <div class="info-icon violet">

            <svg viewBox="0 0 24 24">
              <path d="M4 18V8M10 18V4M16 18v-7M22 18V6"/>
            </svg>

          </div>

          <h2>
            How explanations are shown
          </h2>

          <p>
            The model uses eight approved academic
            and learning-behavior features.

            The student review page surfaces the
            factors that contributed most strongly
            to each individual prediction so advisors
            can inspect the signal rather than
            receiving a black-box label.
          </p>

        </section>


        <section class="card info-card">

          <div class="info-icon amber">

            <svg viewBox="0 0 24 24">
              <path d="M12 3 2.8 19h18.4L12 3Z"/>
              <path d="M12 9v4M12 17h.01"/>
            </svg>

          </div>

          <h2>
            Current alert rule
          </h2>

          <p>
            A High Risk prediction creates an
            advisor-review alert.

            Medium Risk and Low Risk predictions
            do not trigger that alert.

            Prediction probability is displayed
            for context but is not used as an
            additional alert threshold.
          </p>

        </section>


        <section
          class="card info-card wide evaluation-card"
        >

          <div class="section-heading">

            <div>

              <div class="eyebrow">
                MODEL EVALUATION
              </div>

              <h2>
                Development evaluation
              </h2>

              <p>
                How the current model performed
                on data that was held back from
                training during development.
              </p>

            </div>

            <span class="evaluation-tag">
              Current model
            </span>

          </div>


          <div class="metric-strip">

            <div class="metric-small">

              <strong>
                82.4%
              </strong>

              <span>
                Accuracy
              </span>

              <small>
                Overall correct classifications
              </small>

            </div>


            <div class="metric-small">

              <strong>
                84.8%
              </strong>

              <span>
                Balanced accuracy
              </span>

              <small>
                Performance balanced across
                risk classes
              </small>

            </div>


            <div class="metric-small">

              <strong>
                89.8%
              </strong>

              <span>
                High Risk recall
              </span>

              <small>
                High Risk cases correctly
                identified
              </small>

            </div>

          </div>


          <p class="evaluation-note">
            These figures describe this development
            dataset only.

            A university deployment would require
            evaluation on appropriately governed
            institutional data.
          </p>

        </section>


        <section
          class="card info-card wide oversight-callout"
        >

          <div class="callout-mark">

            <svg viewBox="0 0 24 24">

              <path d="M12 3 20 6v5c0 5.2-3.4 8.5-8 10-4.6-1.5-8-4.8-8-10V6l8-3Z"/>

              <path d="m9 12 2 2 4-4"/>

            </svg>

          </div>


          <div>

            <h2>
              Human oversight
            </h2>

            <p>
              AI-generated risk signals remain
              subject to independent advisor review.

              Before institutional deployment,
              the system would require governed
              university data, re-evaluation,
              calibration, fairness review,
              privacy and security review,
              monitoring, and governance.

              ITU materials are used as architecture
              and alignment references,
              not as certification.
            </p>

          </div>

        </section>

      </div>

    </div>
  `;
}


/* =========================================================
   START APPLICATION
   ========================================================= */

bootstrap();
