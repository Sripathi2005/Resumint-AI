/**
 * Dashboard interactivity for AI Resume Analyzer.
 * Manages Chart.js rendering, client-side role switching, modal updating, and localStorage checklist persistence.
 */

document.addEventListener("DOMContentLoaded", function () {
  const dashboardContainer = document.getElementById("dashboard-data");
  if (!dashboardContainer) return;

  const analysisId = dashboardContainer.dataset.analysisId;
  const topRoles = JSON.parse(dashboardContainer.dataset.topRoles || "[]");
  const allRoles = JSON.parse(dashboardContainer.dataset.allRoles || "[]");
  const targetRoleObj = JSON.parse(dashboardContainer.dataset.targetRole || "null");
  const learningResources = JSON.parse(dashboardContainer.dataset.learningResources || "{}");
  const initialRoleTitle = dashboardContainer.dataset.initialRole;

  // Chart defaults for clean modern aesthetic
  Chart.defaults.font.family = "'Plus Jakarta Sans', system-ui, sans-serif";
  Chart.defaults.color = "#64748b";

  // 1. Render Bar Chart (Top 5 Roles Skill Match %)
  const barCanvas = document.getElementById("rolesBarChart");
  if (barCanvas && topRoles.length > 0) {
    const labels = topRoles.map((r) => r.title);
    const skillScores = topRoles.map((r) => r.skill_score);
    const contextScores = topRoles.map((r) => r.text_score);

    new Chart(barCanvas, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Skill Match %",
            data: skillScores,
            backgroundColor: "rgba(79, 70, 229, 0.88)",
            borderColor: "rgb(79, 70, 229)",
            borderWidth: 1,
            borderRadius: 8,
          },
          {
            label: "Context Similarity %",
            data: contextScores,
            backgroundColor: "rgba(148, 163, 184, 0.35)",
            borderColor: "rgb(148, 163, 184)",
            borderWidth: 1,
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            grid: {
              display: false,
            },
            ticks: {
              font: {
                weight: '600',
              },
            },
          },
          y: {
            beginAtZero: true,
            max: 100,
            grid: {
              color: "#f1f5f9",
            },
            ticks: {
              callback: (val) => val + "%",
            },
          },
        },
        plugins: {
          legend: {
            labels: {
              boxWidth: 12,
              usePointStyle: true,
              pointStyle: 'circle',
              font: {
                weight: '600',
              },
            },
          },
          tooltip: {
            backgroundColor: "#0f172a",
            titleFont: { weight: 'bold' },
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: function (ctx) {
                return ctx.dataset.label + ": " + ctx.raw + "%";
              },
            },
          },
        },
      },
    });
  }

  const escapeHtml = (str) =>
    String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");

  // 2. Render Doughnut Chart & Checklist for Active Role
  let doughnutChart = null;
  const doughnutCanvas = document.getElementById("skillsDoughnutChart");

  function updateRoleDisplay(roleTitle) {
    // Prefer exact targetRoleObj metrics when switching to the specifically analyzed job posting
    const isTargetedRole =
      targetRoleObj &&
      targetRoleObj.title &&
      targetRoleObj.title.toLowerCase() === String(roleTitle || "").toLowerCase();
    const role =
      (isTargetedRole ? targetRoleObj : null) ||
      allRoles.find((r) => r.title.toLowerCase() === roleTitle.toLowerCase()) ||
      topRoles[0];
    if (!role) return;

    // Update headline badges & titles
    const titleEl = document.getElementById("active-role-title");
    if (titleEl) titleEl.textContent = role.title;

    const roadmapTitleEl = document.getElementById("active-roadmap-role-title");
    if (roadmapTitleEl) roadmapTitleEl.textContent = role.title;

    const skillScoreEl = document.getElementById("active-role-skill-score");
    if (skillScoreEl) skillScoreEl.textContent = role.skill_score.toFixed(1) + "%";

    const tierEl = document.getElementById("active-role-tier");
    if (tierEl) {
      tierEl.textContent = role.tier || "Match";
      tierEl.className = "tier-badge " + (
        role.skill_score >= 80 ? "tier-strong" : role.skill_score >= 50 ? "tier-moderate" : "tier-growth"
      );
    }

    // Update Search Links and Role Tracker Button
    const searchRoleName = document.getElementById("active-search-role-name");
    if (searchRoleName) searchRoleName.textContent = role.title;

    const encodedTitle = encodeURIComponent(role.title);
    const linkedinUrl = `https://www.linkedin.com/jobs/search/?keywords=${encodedTitle}`;
    const indeedUrl = `https://www.indeed.com/jobs?q=${encodedTitle}`;
    const googleUrl = `https://www.google.com/search?q=${encodeURIComponent(role.title + " jobs")}&ibp=htl;jobs`;
    const trackUrl = `/applications?add_title=${encodedTitle}`;

    const searchLk = document.getElementById("search-linkedin-link");
    if (searchLk) searchLk.href = linkedinUrl;
    const searchId = document.getElementById("search-indeed-link");
    if (searchId) searchId.href = indeedUrl;
    const searchGg = document.getElementById("search-google-link");
    if (searchGg) searchGg.href = googleUrl;

    const trackBtn = document.getElementById("active-role-track-btn");
    if (trackBtn) trackBtn.href = trackUrl;

    const guideUrl = `/roles?role=${encodedTitle}&analysis_id=${encodeURIComponent(analysisId)}#career-roadmap`;
    const roleGuideBtn = document.getElementById("active-role-guide-btn");
    if (roleGuideBtn) roleGuideBtn.href = guideUrl;
    const modalGuideBtn = document.getElementById("active-modal-guide-btn");
    if (modalGuideBtn) modalGuideBtn.href = guideUrl;

    // Update Modal Data
    const modalTitle = document.getElementById("activeRoleModalLabel");
    if (modalTitle) modalTitle.textContent = role.title;
    const modalJobId = document.getElementById("active-modal-job-id");
    if (modalJobId) modalJobId.textContent = role.job_id || "ROLE";
    const modalCat = document.getElementById("active-modal-category");
    if (modalCat) modalCat.textContent = role.category || "Engineering";
    const modalExp = document.getElementById("active-modal-exp");
    if (modalExp) modalExp.textContent = role.experience_level || "Entry-level";
    const modalDesc = document.getElementById("active-modal-desc");
    if (modalDesc) modalDesc.textContent = role.description || `Benchmark requirements for ${role.title}.`;

    const modalMatched = document.getElementById("active-modal-matched");
    if (modalMatched) {
      modalMatched.innerHTML = (role.matched || [])
        .map((m) => `<span class="badge-matched">${m}</span>`)
        .join(" ") || '<span class="text-muted small">None</span>';
    }

    const modalMissing = document.getElementById("active-modal-missing");
    if (modalMissing) {
      modalMissing.innerHTML = (role.missing || [])
        .map((m) => `<span class="badge-missing">${m}</span>`)
        .join(" ") || '<span class="badge bg-success-subtle text-success small">All required skills satisfied!</span>';
    }

    const modalLk = document.getElementById("modal-search-linkedin");
    if (modalLk) modalLk.href = linkedinUrl;
    const modalId = document.getElementById("modal-search-indeed");
    if (modalId) modalId.href = indeedUrl;
    const modalGg = document.getElementById("modal-search-google");
    if (modalGg) modalGg.href = googleUrl;
    const modalTrack = document.getElementById("active-modal-track-btn");
    if (modalTrack) modalTrack.href = trackUrl;

    const matchedCount = role.matched ? role.matched.length : 0;
    const missingCount = role.missing ? role.missing.length : 0;

    // Update Doughnut Chart with sleek cutout
    if (doughnutCanvas) {
      if (doughnutChart) {
        doughnutChart.data.datasets[0].data = [matchedCount, missingCount];
        doughnutChart.update();
      } else {
        doughnutChart = new Chart(doughnutCanvas, {
          type: "doughnut",
          data: {
            labels: ["Matched Skills", "Missing Skills"],
            datasets: [
              {
                data: [matchedCount, missingCount],
                backgroundColor: ["#10b981", "#f43f5e"],
                borderWidth: 0,
                borderRadius: 4,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "70%",
            plugins: {
              legend: {
                position: "bottom",
                labels: {
                  boxWidth: 12,
                  usePointStyle: true,
                  pointStyle: 'circle',
                  font: {
                    weight: '600',
                  },
                },
              },
              tooltip: {
                backgroundColor: "#0f172a",
                padding: 10,
                cornerRadius: 8,
              },
            },
          },
        });
      }
    }

    // Update Checklist DOM
    const checklistContainer = document.getElementById("checklist-items-container");
    const progressEl = document.getElementById("checklist-progress-text");
    if (!checklistContainer) return;

    checklistContainer.innerHTML = "";

    const missingList = role.missing || [];
    if (missingList.length === 0) {
      checklistContainer.innerHTML = `
        <div class="text-center py-4 text-success">
          <i class="bi bi-patch-check-fill fs-2"></i>
          <p class="mt-2 mb-0 fw-semibold">No skill gaps detected! 100% of required skills are satisfied.</p>
        </div>
      `;
      if (progressEl) progressEl.textContent = "100% Complete";
      return;
    }

    let checkedCount = 0;

    missingList.forEach((skillName, index) => {
      const storageKey = `chk_${analysisId}_${role.title}_${skillName}`;
      const isSavedChecked = localStorage.getItem(storageKey) === "true";
      if (isSavedChecked) checkedCount++;

      const rawRes = learningResources[skillName];
      const res = rawRes || {
        platform: `${skillName} Documentation`,
        url: `https://roadmap.sh/`,
        topics: `Core syntax, architecture, and industry standards for ${skillName}`,
        project: `Build a practical demo application using ${skillName} for your portfolio`,
        est_time: "1-2 weeks",
        resources: [
          {
            platform: "freeCodeCamp",
            title: `freeCodeCamp - Search ${skillName} Tutorials`,
            description: `Explore free interactive lessons and developer articles covering ${skillName}.`,
            url: `https://www.freecodecamp.org/news/search/?query=${encodeURIComponent(skillName)}`,
            cost: "Free",
          },
          {
            platform: "roadmap.sh",
            title: "Developer Learning Roadmaps",
            description: `Structured learning path and curated community resources related to ${skillName}.`,
            url: "https://roadmap.sh/",
            cost: "Free",
          },
        ],
      };

      const resourceList = Array.isArray(res.resources) && res.resources.length > 0
        ? res.resources
        : [
            {
              platform: res.platform || `${skillName} Resource`,
              title: res.platform || `Learn ${skillName}`,
              description: res.topics || `Step-by-step guide and tutorials for ${skillName}.`,
              url: res.url || "https://roadmap.sh/",
              cost: "Free",
            },
          ];

      const resourceCardsHtml = resourceList
        .map((r) => {
          const costBadgeClass = String(r.cost || "Free").includes("Free")
            ? "bg-success-subtle text-success"
            : "bg-light text-secondary border";
          return `
            <div class="col-md-4">
              <a href="${escapeHtml(r.url)}" target="_blank" rel="noopener noreferrer"
                 class="d-block p-2 rounded-3 bg-white border text-decoration-none h-100 resource-mini-card">
                <div class="d-flex justify-content-between align-items-center mb-1">
                  <span class="badge bg-primary-subtle text-primary small">${escapeHtml(r.platform)}</span>
                  <span class="badge ${costBadgeClass} small" style="font-size: 0.7rem;">${escapeHtml(r.cost || "Free")}</span>
                </div>
                <div class="fw-semibold text-dark small lh-sm mb-1">
                  ${escapeHtml(r.title)} <i class="bi bi-box-arrow-up-right text-primary ms-1" style="font-size: 0.72rem;"></i>
                </div>
                <div class="text-muted" style="font-size: 0.75rem; line-height: 1.35;">
                  ${escapeHtml(r.description)}
                </div>
              </a>
            </div>
          `;
        })
        .join("");

      const itemDiv = document.createElement("div");
      itemDiv.className = "checklist-item" + (isSavedChecked ? " checked" : "");

      const targetChecklistItem =
        isTargetedRole && Array.isArray(targetRoleObj.learning_checklist)
          ? targetRoleObj.learning_checklist.find((x) => x.skill === skillName)
          : null;
      const whatItIs = (targetChecklistItem && targetChecklistItem.what_it_is) || res.what_it_is || "";
      const whyImportant = (targetChecklistItem && targetChecklistItem.why_important) || "";
      const explanationHtml = whatItIs
        ? `<div class="p-2 rounded bg-light border mb-2 small">
             <div class="text-dark mb-1"><strong>What It Is:</strong> ${escapeHtml(whatItIs)}</div>
             ${whyImportant ? `<div class="text-secondary"><strong>Why Important for ${escapeHtml(role.title)}:</strong> ${escapeHtml(whyImportant)}</div>` : ""}
           </div>`
        : "";

      itemDiv.innerHTML = `
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2 w-100">
          <div class="form-check d-flex align-items-center mb-0">
            <input class="form-check-input me-3 fs-5" type="checkbox" id="chk-${index}" ${
        isSavedChecked ? "checked" : ""
      }>
            <label class="form-check-label fw-bold text-dark fs-6" for="chk-${index}">
              ${escapeHtml(skillName)}
            </label>
          </div>
          <div class="d-flex align-items-center gap-2">
            <span class="badge bg-light text-muted border small"><i class="bi bi-clock me-1"></i>${escapeHtml(res.est_time || "1-2 weeks")}</span>
            <span class="badge bg-danger-subtle text-danger border border-danger-subtle small">Missing Skill</span>
          </div>
        </div>

        <div class="ms-md-4 ps-md-2 mt-2 pt-2 border-top w-100">
          ${explanationHtml}
          <div class="small text-muted mb-2">
            <i class="bi bi-book text-primary me-1"></i><strong>Core Concepts:</strong> ${escapeHtml(res.topics || "Fundamental principles")}
          </div>
          <div class="small fw-semibold text-dark mb-2">
            <i class="bi bi-link-45deg text-primary me-1"></i>Recommended Learning Platforms (${resourceList.length}):
          </div>
          <div class="row g-2 mb-2">
            ${resourceCardsHtml}
          </div>
          <div class="small text-secondary" style="background-color: #f8fafc; padding: 0.45rem 0.75rem; border-radius: 6px;">
            <i class="bi bi-tools text-success me-1"></i><strong>Recommended Project Idea:</strong> ${escapeHtml(res.project || "Build a working prototype")}
          </div>
        </div>
      `;

      const checkbox = itemDiv.querySelector("input[type='checkbox']");
      checkbox.addEventListener("change", function () {
        localStorage.setItem(storageKey, this.checked ? "true" : "false");
        if (this.checked) {
          itemDiv.classList.add("checked");
        } else {
          itemDiv.classList.remove("checked");
        }
        updateProgress();
      });

      checklistContainer.appendChild(itemDiv);
    });

    function updateProgress() {
      const allCheckboxes = checklistContainer.querySelectorAll("input[type='checkbox']");
      const done = Array.from(allCheckboxes).filter((cb) => cb.checked).length;
      if (progressEl) {
        progressEl.textContent = `${done} of ${allCheckboxes.length} mastered`;
      }
    }

    updateProgress();
  }

  // Handle role switch dropdown
  const roleSelectEl = document.getElementById("role-switcher-select");
  if (roleSelectEl) {
    roleSelectEl.addEventListener("change", function () {
      updateRoleDisplay(this.value);
    });
  }

  // Initial load
  updateRoleDisplay(initialRoleTitle || (topRoles[0] ? topRoles[0].title : ""));
});
