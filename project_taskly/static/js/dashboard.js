document.addEventListener("DOMContentLoaded", function () {
    function renderAvatarContent(avatarUrl, initials, altText = "Avatar") {
        const safeAltText = String(altText || "Avatar").replace(/"/g, "&quot;");
        return avatarUrl
            ? `<img src="${avatarUrl}" alt="${safeAltText}" class="avatar-media avatar-media-cover">`
            : (initials || "");
    }

    function syncUserAvatar(userId, initials, avatarUrl, altText = "Avatar") {
        if (!userId) return;
        document.querySelectorAll(`[data-avatar-user-id="${userId}"]`).forEach(node => {
            node.dataset.avatarInitials = initials || node.dataset.avatarInitials || "";
            node.innerHTML = renderAvatarContent(avatarUrl, node.dataset.avatarInitials, altText);
        });
    }

    const savedTimezone = document.body?.dataset?.userTimezone || "";
    if (!savedTimezone) {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        fetch(setTimezoneUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
            body: JSON.stringify({ timezone: timezone })
        }).catch(() => {});
    }

    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const sidebarToggle = document.getElementById("sidebarToggle");

    if (sidebarToggle && sidebar && overlay) {
        sidebarToggle.addEventListener("click", () => {
            sidebar.classList.toggle("open");
            overlay.classList.toggle("open");
        });
    }

    if (overlay && sidebar) {
        overlay.addEventListener("click", () => {
            sidebar.classList.remove("open");
            overlay.classList.remove("open");
        });
    }

    const taskModal = document.getElementById("addTaskModal");
    const projectMapNode = document.getElementById("task-project-member-map");
    if (taskModal && projectMapNode) {
        const projectMemberMap = JSON.parse(projectMapNode.textContent);
        const projectSelect = taskModal.querySelector('select[name="project"]');
        const assigneeSelect = document.getElementById("taskAssigneeSelect");

        const updateTaskAssignees = (projectId) => {
            if (!assigneeSelect) return;
            const members = projectMemberMap[projectId] || [];
            assigneeSelect.innerHTML = '<option value="">Assign to me</option>';
            members.forEach(member => {
                const option = document.createElement("option");
                option.value = member.id;
                option.textContent = member.name;
                assigneeSelect.appendChild(option);
            });
        };

        if (projectSelect) {
            projectSelect.addEventListener("change", () => updateTaskAssignees(projectSelect.value));
        }

        taskModal.addEventListener("show.bs.modal", function (event) {
            const trigger = event.relatedTarget;
            const projectId = trigger ? trigger.getAttribute("data-project-id") : (projectSelect ? projectSelect.value : "");
            if (projectSelect && projectId) projectSelect.value = projectId;
            updateTaskAssignees(projectId || (projectSelect ? projectSelect.value : ""));
        });
    }

    function fixStatCards() {
        const cols = document.querySelectorAll('[style*="flex: 0 0 20%"]');
        if (window.innerWidth < 992) {
            cols.forEach(c => {
                c.style.flex = "0 0 50%";
                c.style.maxWidth = "50%";
            });
        } else if (window.innerWidth < 1200) {
            cols.forEach(c => {
                c.style.flex = "0 0 33.333%";
                c.style.maxWidth = "33.333%";
            });
        } else {
            cols.forEach(c => {
                c.style.flex = "0 0 20%";
                c.style.maxWidth = "20%";
            });
        }
    }

    fixStatCards();
    window.addEventListener("resize", fixStatCards);

    const chart = document.getElementById("commitChart");
    if (chart) {
        const safeData = (data && Array.isArray(data) && data.length > 0) ? data : [0, 0, 0, 0, 0, 0, 0];
        const validData = safeData.filter(v => typeof v === "number" && !isNaN(v));
        const renderEmptyChart = () => {
            const emptyMessage = document.createElement("div");
            emptyMessage.textContent = "No data available";
            emptyMessage.style.cssText = "width:100%;text-align:center;padding:20px;color:var(--text-secondary);";
            chart.appendChild(emptyMessage);
        };

        if (validData.length > 0) {
            const max = Math.max(...validData);
            if (isFinite(max) && max > 0) {
                validData.forEach(v => {
                    const bar = document.createElement("div");
                    bar.style.cssText = `flex:1;border-radius:3px 3px 0 0;height:${Math.max(4, (v / max) * 100)}%;background:${v > 6 ? "var(--accent)" : v > 3 ? "rgba(79,124,255,.5)" : "rgba(79,124,255,.25)"};transition:opacity .15s;cursor:default;`;
                    bar.title = `${v} tasks`;
                    bar.addEventListener("mouseenter", () => bar.style.opacity = ".7");
                    bar.addEventListener("mouseleave", () => bar.style.opacity = "1");
                    chart.appendChild(bar);
                });
            } else {
                renderEmptyChart();
            }
        } else {
            renderEmptyChart();
        }
    }

    // Projects Page
    const filterPills = document.querySelectorAll(".filter-pill");
    const allGridCards = document.querySelectorAll("#gridView .project-card-shell");
    const emptyState = document.getElementById("emptyState");

    function applyFilter(filter) {
        if (!allGridCards.length || !emptyState) return;
        let visibleCount = 0;
        allGridCards.forEach(card => {
            const match = filter === "all" || card.dataset.status === filter;
            card.style.display = match ? "" : "none";
            if (match) visibleCount++;
        });
        emptyState.style.display = visibleCount ? "none" : "block";
    }

    function setupColorIconPicker(colorPickerId, iconPickerId, colorInputId, iconInputId, selectedColor, selectedIcon) {
        const colorInput = document.getElementById(colorInputId);
        const iconInput = document.getElementById(iconInputId);
        const colorButtons = document.querySelectorAll(`#${colorPickerId} .color-swatch`);
        const iconButtons = document.querySelectorAll(`#${iconPickerId} .icon-opt`);

        colorButtons.forEach(button => {
            button.classList.toggle("selected", button.dataset.color === selectedColor);
            button.onclick = () => {
                colorButtons.forEach(item => item.classList.remove("selected"));
                button.classList.add("selected");
                if (colorInput) colorInput.value = button.dataset.color;
            };
        });

        iconButtons.forEach(button => {
            button.classList.toggle("selected", button.dataset.icon === selectedIcon);
            button.onclick = () => {
                iconButtons.forEach(item => item.classList.remove("selected"));
                button.classList.add("selected");
                if (iconInput) iconInput.value = button.dataset.icon;
            };
        });
    }

    if (filterPills.length) {
        filterPills.forEach(pill => {
            pill.addEventListener("click", () => {
                filterPills.forEach(p => p.classList.remove("active"));
                pill.classList.add("active");
                applyFilter(pill.dataset.filter);
            });
        });
    }

    if (document.getElementById("colorPicker")) {
        setupColorIconPicker("colorPicker", "iconPicker", "selectedProjectColor", "selectedProjectIcon", "#4f7cff", "globe");
    }

    const createTeamSearch = document.getElementById("createTeamSearch");
    const createTeamOptions = document.querySelectorAll(".create-team-list .manage-team-option");
    if (createTeamSearch && createTeamOptions.length) {
        const filterCreateTeamOptions = () => {
            const query = createTeamSearch.value.trim().toLowerCase();
            createTeamOptions.forEach(option => {
                const haystack = option.dataset.memberSearch || "";
                option.style.display = query && haystack.includes(query) ? "" : "none";
            });
        };

        filterCreateTeamOptions();
        createTeamSearch.addEventListener("input", () => {
            filterCreateTeamOptions();
        });
    }

    const editProjectModalEl = document.getElementById("editProjectModal");
    const manageTeamModalEl = document.getElementById("manageTeamModal");
    const deleteProjectModalEl = document.getElementById("deleteProjectModal");
    const editProjectModal = editProjectModalEl ? new bootstrap.Modal(editProjectModalEl) : null;
    const manageTeamModal = manageTeamModalEl ? new bootstrap.Modal(manageTeamModalEl) : null;
    const deleteProjectModal = deleteProjectModalEl ? new bootstrap.Modal(deleteProjectModalEl) : null;

    document.querySelectorAll(".project-card-menu, .project-card-menu .dropdown-menu").forEach(menu => {
        menu.addEventListener("click", event => {
            event.preventDefault();
            event.stopPropagation();
        });
    });

    document.querySelectorAll(".proj-menu-btn").forEach(button => {
        button.addEventListener("click", event => {
            event.preventDefault();
            event.stopPropagation();
        });
    });

    function closeProjectDropdown(button) {
        const dropdownToggle = button.closest(".dropdown")?.querySelector('[data-bs-toggle="dropdown"]');
        if (!dropdownToggle) return;
        bootstrap.Dropdown.getOrCreateInstance(dropdownToggle).hide();
    }

    document.querySelectorAll(".project-edit-trigger").forEach(button => {
        button.addEventListener("click", event => {
            event.preventDefault();
            event.stopPropagation();
            closeProjectDropdown(button);
            const editProjectForm = document.getElementById("editProjectForm");
            if (!editProjectForm) return;
            editProjectForm.action = `/dashboard/projects/${button.dataset.projectId}/update/`;
            document.getElementById("editProjectName").value = button.dataset.projectName;
            document.getElementById("editProjectDescription").value = button.dataset.projectDescription;
            document.getElementById("editProjectStatus").value = button.dataset.projectStatus;
            document.getElementById("editProjectBudget").value = button.dataset.projectBudget;
            document.getElementById("editProjectStart").value = button.dataset.projectStart;
            document.getElementById("editProjectEnd").value = button.dataset.projectEnd;
            document.getElementById("editProjectColor").value = button.dataset.projectColor;
            document.getElementById("editProjectIcon").value = button.dataset.projectIcon;
            setupColorIconPicker("editColorPicker", "editIconPicker", "editProjectColor", "editProjectIcon", button.dataset.projectColor, button.dataset.projectIcon);
            if (editProjectModal) editProjectModal.show();
        });
    });

    document.querySelectorAll(".project-team-trigger").forEach(button => {
        button.addEventListener("click", event => {
            event.preventDefault();
            event.stopPropagation();
            closeProjectDropdown(button);
            const manageTeamForm = document.getElementById("manageTeamForm");
            const manageTeamProjectName = document.getElementById("manageTeamProjectName");
            if (!manageTeamForm || !manageTeamProjectName) return;
            const selectedMembers = button.dataset.projectMembers ? button.dataset.projectMembers.split(",") : [];
            manageTeamForm.action = `/dashboard/projects/${button.dataset.projectId}/team/`;
            manageTeamProjectName.textContent = `Update team members for ${button.dataset.projectName}.`;
            document.querySelectorAll("#manageTeamMembers .manage-team-check").forEach(option => {
                option.checked = selectedMembers.includes(option.value);
            });
            if (manageTeamModal) manageTeamModal.show();
        });
    });

    document.querySelectorAll(".project-delete-trigger").forEach(button => {
        button.addEventListener("click", event => {
            event.preventDefault();
            event.stopPropagation();
            closeProjectDropdown(button);
            const deleteProjectForm = document.getElementById("deleteProjectForm");
            const deleteProjectName = document.getElementById("deleteProjectName");
            if (!deleteProjectForm || !deleteProjectName) return;
            deleteProjectForm.action = `/dashboard/projects/${button.dataset.projectId}/delete/`;
            deleteProjectName.textContent = button.dataset.projectName;
            if (deleteProjectModal) deleteProjectModal.show();
        });
    });

    // Project Board Page
    const board = document.querySelector(".kanban-board-match");
    const taskEditModalEl = document.getElementById("taskEditModal");
    const taskEditModal = taskEditModalEl ? new bootstrap.Modal(taskEditModalEl) : null;
    const deleteTaskModalEl = document.getElementById("deleteTaskModal");
    const deleteTaskModal = deleteTaskModalEl ? new bootstrap.Modal(deleteTaskModalEl) : null;
    const taskEditForm = document.getElementById("taskEditForm");
    const taskCommentForm = document.getElementById("taskCommentForm");
    const taskCommentsList = document.getElementById("taskCommentsList");
    const confirmDeleteTaskBtn = document.getElementById("confirmDeleteTaskBtn");
    const deleteTaskName = document.getElementById("deleteTaskName");
    let draggedTask = null;
    let activeTaskCard = null;
    let pendingDeleteTask = null;

    async function deleteTaskCard(taskEl) {
        if (!taskEl) return;

        const payload = await postForm(taskEl.dataset.deleteUrl, {});
        taskEl.remove();
        updateColumnCounts();
        updateBoardSummary();
        if (taskEditModal) taskEditModal.hide();
        if (deleteTaskModal) deleteTaskModal.hide();
        showToast("success", payload.message);
        pendingDeleteTask = null;
    }

    function updateColumnCounts() {
        if (!board) return;
        document.querySelectorAll(".match-column").forEach(column => {
            const count = column.querySelectorAll(".match-task").length;
            const countNode = column.querySelector(".column-count");
            if (countNode) countNode.textContent = count;
        });
    }

    function updateBoardSummary() {
        if (!board) return;
        const taskCards = Array.from(document.querySelectorAll(".match-task"));
        const totalTasks = taskCards.length;
        const totalProgress = taskCards.reduce((sum, card) => sum + Number(card.dataset.progressValue || 0), 0);
        const progress = totalTasks ? Math.round(totalProgress / totalTasks) : 0;
        const totalNode = document.getElementById("boardTaskTotal");
        const progressNode = document.getElementById("boardProgressValue");
        if (totalNode) totalNode.textContent = totalTasks;
        if (progressNode) progressNode.textContent = progress;
    }

    function getOptimisticProgressValue(taskEl, nextStatus) {
        if (nextStatus === "completed") return 100;
        if (nextStatus === "todo") return 0;
        const currentProgress = Number(taskEl.dataset.progressValue || 0);
        if (taskEl.dataset.status === "completed" && currentProgress >= 100) return 55;
        return Math.max(currentProgress, 15) || 55;
    }

    function applyTaskStatusVisualState(taskEl, nextStatus, progressValue = null) {
        const resolvedProgress = progressValue ?? getOptimisticProgressValue(taskEl, nextStatus);
        taskEl.dataset.status = nextStatus;
        taskEl.dataset.progressValue = String(resolvedProgress);
        taskEl.classList.toggle("is-completed", nextStatus === "completed");

        const existingProgress = taskEl.querySelector(".match-task-progress");
        if (existingProgress) {
            existingProgress.remove();
        }

        const meta = taskEl.querySelector(".match-task-meta");
        const dueDateText = meta?.querySelector("span:first-child")?.textContent?.trim() || "No date";
        const commentCount = Number(taskEl.dataset.comments || 0);
        if (meta) {
            meta.innerHTML = `
                <span><i class="bi bi-calendar3"></i> ${dueDateText}</span>
                ${nextStatus === "completed"
                    ? '<span class="match-done"><i class="bi bi-check-circle-fill"></i> Done</span>'
                    : `<span><i class="bi bi-chat"></i> ${commentCount}</span>`}
            `;
        }
    }

    function renderComments(comments) {
        if (!taskCommentsList) return;
        taskCommentsList.innerHTML = "";
        if (!comments.length) {
            taskCommentsList.innerHTML = '<div class="task-comment-empty">No comments yet.</div>';
            return;
        }

        comments.forEach(comment => {
            const item = document.createElement("div");
            item.className = "task-comment-item";
            item.innerHTML = `
                <div class="task-comment-head">
                    <div class="d-flex align-items-center gap-2">
                        <div class="task-comment-avatar" data-avatar-user-id="${comment.user_id || ""}" data-avatar-initials="${comment.user_initials || ""}">${renderAvatarContent(comment.user_avatar_url, comment.user_initials, comment.user_name || "Avatar")}</div>
                        <strong>${comment.user_name}</strong>
                    </div>
                    <span>${comment.created_at}</span>
                </div>
                <div class="task-comment-body">${comment.comment}</div>
            `;
            taskCommentsList.appendChild(item);
        });
    }

    function bindTaskDrag(task) {
        if (task.dataset.dragBound === "1") return;
        task.dataset.dragBound = "1";
        task.addEventListener("dragstart", event => {
            draggedTask = task;
            if (event.dataTransfer) {
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", task.dataset.taskId);
            }
            task.classList.add("is-dragging");
        });

        task.addEventListener("dragend", () => {
            task.classList.remove("is-dragging");
            draggedTask = null;
            document.querySelectorAll(".match-list, .match-column").forEach(node => node.classList.remove("is-over"));
        });
    }

    function refreshTaskBindings() {
        if (!board) return;
        document.querySelectorAll(".match-task").forEach(bindTaskDrag);
    }

    function updateTaskCardUI(taskEl, task) {
        taskEl.dataset.status = task.status;
        taskEl.dataset.progressValue = String(task.progress_value || 0);
        taskEl.dataset.comments = String(task.comment_count ?? task.comments.length);
        taskEl.classList.toggle("is-completed", task.status === "completed");

        const title = taskEl.querySelector(".match-task-title");
        if (title) title.textContent = task.title;
        taskEl.setAttribute("draggable", "true");

        const project = taskEl.querySelector(".match-task-project");
        if (project) project.innerHTML = `<i class="bi bi-folder"></i> ${task.project_name}`;

        const priorityPill = taskEl.querySelector(".priority-pill");
        if (priorityPill) {
            priorityPill.className = `priority-pill ${task.priority}`;
            priorityPill.textContent = task.priority_label.toUpperCase();
        }

        const avatarWrap = taskEl.querySelector(".match-task-avatars");
        if (avatarWrap) {
            avatarWrap.innerHTML = task.assigned_to_initials
                ? `<div class="proj-ava" style="background:var(--accent);" data-avatar-user-id="${task.assigned_to_id || ""}" data-avatar-initials="${task.assigned_to_initials || ""}">${renderAvatarContent(task.assigned_to_avatar_url, task.assigned_to_initials, task.assigned_to_name || "Assignee")}</div>`
                : "";
        }

        const meta = taskEl.querySelector(".match-task-meta");
        const commentCount = task.comment_count ?? task.comments.length;
        if (meta) {
            meta.innerHTML = `
                <span><i class="bi bi-calendar3"></i> ${task.due_date_display}</span>
                ${task.status === "completed"
                    ? '<span class="match-done"><i class="bi bi-check-circle-fill"></i> Done</span>'
                    : `<span><i class="bi bi-chat"></i> ${commentCount}</span>`}
            `;
        }

        const existingProgress = taskEl.querySelector(".match-task-progress");
        if (existingProgress) {
            existingProgress.remove();
        }
    }

    async function postForm(url, data) {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": csrfToken,
                "X-Requested-With": "XMLHttpRequest"
            },
            body: new URLSearchParams(data)
        });

        const payload = await response.json();
        if (!response.ok || !payload.success) throw new Error(payload.message || "Request failed.");
        return payload;
    }

    async function openTaskEditor(taskEl) {
        const response = await fetch(taskEl.dataset.detailUrl, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
            cache: "no-store"
        });
        const payload = await response.json();
        if (!response.ok || !payload.success) throw new Error(payload.message || "Unable to load task.");

        const task = payload.task;
        activeTaskCard = taskEl;
        document.getElementById("taskEditTitle").textContent = task.title;
        document.getElementById("taskEditPriorityPill").className = `priority-pill ${task.priority}`;
        document.getElementById("taskEditPriorityPill").textContent = task.priority_label.toUpperCase();
        document.getElementById("taskEditProjectLabel").innerHTML = `<i class="bi bi-folder"></i> ${task.project_name}`;
        document.getElementById("taskEditProjectReadonly").textContent = task.project_name;
        document.getElementById("taskEditTitleInput").value = task.title;
        document.getElementById("taskEditDescription").value = task.description;
        document.getElementById("taskEditStatus").value = task.status;
        document.getElementById("taskEditPriority").value = task.priority;
        document.getElementById("taskEditDueDate").value = task.due_date;

        const assigneeSelect = document.getElementById("taskEditAssignee");
        assigneeSelect.innerHTML = '<option value="">Unassigned</option>';
        task.members.forEach(member => {
            const option = document.createElement("option");
            option.value = member.id;
            option.textContent = member.name;
            if (String(member.id) === String(task.assigned_to_id)) option.selected = true;
            assigneeSelect.appendChild(option);
        });

        taskEditForm.dataset.updateUrl = taskEl.dataset.fullUpdateUrl;
        taskCommentForm.dataset.commentUrl = taskEl.dataset.commentUrl;
        renderComments(task.comments);
        if (taskEditModal) taskEditModal.show();
    }

    if (taskEditForm) {
        taskEditForm.addEventListener("submit", async event => {
            event.preventDefault();
            if (!activeTaskCard) return;

            try {
                const payload = await postForm(taskEditForm.dataset.updateUrl, {
                    title: document.getElementById("taskEditTitleInput").value,
                    description: document.getElementById("taskEditDescription").value,
                    status: document.getElementById("taskEditStatus").value,
                    priority: document.getElementById("taskEditPriority").value,
                    due_date: document.getElementById("taskEditDueDate").value,
                    assigned_to: document.getElementById("taskEditAssignee").value
                });

                updateTaskCardUI(activeTaskCard, payload.task);
                bindTaskDrag(activeTaskCard);
                const targetColumn = document.querySelector(`.match-list[data-dropzone="${payload.task.status}"]`);
                if (targetColumn && activeTaskCard.parentElement !== targetColumn) targetColumn.appendChild(activeTaskCard);
                updateColumnCounts();
                updateBoardSummary();
                document.getElementById("taskEditTitle").textContent = payload.task.title;
                showToast("success", payload.message);
                if (taskEditModal) taskEditModal.hide();
            } catch (error) {
                showToast("error", error.message);
            }
        });
    }

    if (taskCommentForm) {
        taskCommentForm.addEventListener("submit", async event => {
            event.preventDefault();
            if (!activeTaskCard) return;

            const commentInput = document.getElementById("taskCommentInput");
            const comment = commentInput.value.trim();
            if (!comment) return;

            try {
                const payload = await postForm(taskCommentForm.dataset.commentUrl, { comment });
                commentInput.value = "";
                const existing = taskCommentsList.querySelector(".task-comment-empty");
                if (existing) existing.remove();

                renderComments([payload.comment, ...Array.from(taskCommentsList.querySelectorAll(".task-comment-item")).map(node => ({
                    user_id: node.querySelector(".task-comment-avatar")?.dataset.avatarUserId || "",
                    user_initials: node.querySelector(".task-comment-avatar")?.dataset.avatarInitials || node.querySelector(".task-comment-avatar")?.textContent || "",
                    user_avatar_url: node.querySelector(".task-comment-avatar img")?.getAttribute("src") || "",
                    user_name: node.querySelector("strong").textContent,
                    created_at: node.querySelector(".task-comment-head span").textContent,
                    comment: node.querySelector(".task-comment-body").textContent
                }))]);

                const count = Number(activeTaskCard.dataset.comments || "0") + 1;
                activeTaskCard.dataset.comments = count;
                if (activeTaskCard.dataset.status !== "completed") {
                    const commentMeta = activeTaskCard.querySelector(".match-task-meta span:last-child");
                    if (commentMeta) commentMeta.innerHTML = `<i class="bi bi-chat"></i> ${count}`;
                }
                showToast("success", payload.message);
            } catch (error) {
                showToast("error", error.message);
            }
        });
    }

    if (board) {
        board.addEventListener("click", async event => {
            const editBtn = event.target.closest(".task-edit-trigger");
            const moveBtn = event.target.closest(".task-move-trigger");
            const deleteBtn = event.target.closest(".task-delete-trigger");
            const taskMenuBtn = event.target.closest(".match-task-menu");
            const taskDropdown = event.target.closest(".board-task-dropdown");
            const taskEl = event.target.closest(".match-task");

            if (editBtn && taskEl) {
                try {
                    await openTaskEditor(taskEl);
                } catch (error) {
                    showToast("error", error.message);
                }
            }

            if (taskEl && !editBtn && !moveBtn && !deleteBtn && !taskMenuBtn && !taskDropdown) {
                try {
                    await openTaskEditor(taskEl);
                } catch (error) {
                    showToast("error", error.message);
                }
            }

            if (moveBtn && taskEl) {
                const nextMap = { todo: "in_progress", in_progress: "completed", completed: "todo" };
                const nextStatus = nextMap[taskEl.dataset.status] || "todo";
                const targetColumn = document.querySelector(`.match-list[data-dropzone="${nextStatus}"]`);
                const previousParent = taskEl.parentElement;
                const previousStatus = taskEl.dataset.status;
                const previousProgressValue = taskEl.dataset.progressValue;
                targetColumn.appendChild(taskEl);
                applyTaskStatusVisualState(taskEl, nextStatus);
                updateColumnCounts();
                updateBoardSummary();

                try {
                    const payload = await postForm(taskEl.dataset.updateUrl, { status: nextStatus, next: window.location.pathname });
                    updateTaskCardUI(taskEl, payload.task);
                    updateColumnCounts();
                    updateBoardSummary();
                    showToast("success", payload.message);
                } catch (error) {
                    previousParent.appendChild(taskEl);
                    applyTaskStatusVisualState(taskEl, previousStatus, Number(previousProgressValue || 0));
                    updateColumnCounts();
                    updateBoardSummary();
                    showToast("error", error.message);
                }
            }

            if (deleteBtn && taskEl) {
                pendingDeleteTask = taskEl;
                if (deleteTaskName) {
                    deleteTaskName.textContent = taskEl.querySelector(".match-task-title")?.textContent?.trim() || "this task";
                }
                if (deleteTaskModal) deleteTaskModal.show();
            }
        });

        refreshTaskBindings();
        updateColumnCounts();
        updateBoardSummary();

        document.querySelectorAll(".match-list").forEach(list => {
            const column = list.closest(".match-column");

            list.addEventListener("dragenter", event => {
                event.preventDefault();
                column?.classList.add("is-over");
                list.classList.add("is-over");
            });

            list.addEventListener("dragover", event => {
                event.preventDefault();
                if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
                column?.classList.add("is-over");
                list.classList.add("is-over");
            });

            list.addEventListener("dragleave", event => {
                const nextTarget = event.relatedTarget;
                if (!nextTarget || !list.contains(nextTarget)) {
                    column?.classList.remove("is-over");
                    list.classList.remove("is-over");
                }
            });

            list.addEventListener("drop", async event => {
                event.preventDefault();
                column?.classList.remove("is-over");
                list.classList.remove("is-over");
                if (!draggedTask) return;

                const newStatus = list.dataset.dropzone;
                const oldStatus = draggedTask.dataset.status;
                if (newStatus === oldStatus) return;

                const previousParent = draggedTask.parentElement;
                const previousProgressValue = draggedTask.dataset.progressValue;
                list.appendChild(draggedTask);
                applyTaskStatusVisualState(draggedTask, newStatus);
                updateColumnCounts();
                updateBoardSummary();

                try {
                    const payload = await postForm(draggedTask.dataset.updateUrl, { status: newStatus, next: window.location.pathname });
                    updateTaskCardUI(draggedTask, payload.task);
                    bindTaskDrag(draggedTask);
                    updateColumnCounts();
                    updateBoardSummary();
                    showToast("success", payload.message);
                } catch (error) {
                    previousParent.appendChild(draggedTask);
                    applyTaskStatusVisualState(draggedTask, oldStatus, Number(previousProgressValue || 0));
                    updateColumnCounts();
                    updateBoardSummary();
                    showToast("error", error.message);
                }
            });
        });
    }

    if (confirmDeleteTaskBtn) {
        confirmDeleteTaskBtn.addEventListener("click", async () => {
            if (!pendingDeleteTask || confirmDeleteTaskBtn.dataset.loading === "true") return;

            confirmDeleteTaskBtn.dataset.loading = "true";
            try {
                await deleteTaskCard(pendingDeleteTask);
            } catch (error) {
                showToast("error", error.message);
            } finally {
                delete confirmDeleteTaskBtn.dataset.loading;
            }
        });
    }

    if (deleteTaskModalEl) {
        deleteTaskModalEl.addEventListener("hidden.bs.modal", () => {
            pendingDeleteTask = null;
            if (deleteTaskName) deleteTaskName.textContent = "";
        });
    }

    const notificationToggle = document.getElementById("notificationToggle");
    const notificationDropdown = notificationToggle?.closest(".dropdown");
    const notificationSubtitle = document.querySelector("[data-notification-subtitle]");

    function clearNotificationUnreadState() {
        if (notificationToggle) {
            notificationToggle.dataset.unreadCount = "0";
            const badge = notificationToggle.querySelector("[data-notification-badge]");
            if (badge) badge.remove();
        }

        document.querySelectorAll("[data-notification-item]").forEach(item => {
            item.classList.remove("is-unread");
        });

        document.querySelectorAll("[data-notification-item-dot]").forEach(dot => dot.remove());

        if (notificationSubtitle) {
            const hasNotifications = document.querySelectorAll("[data-notification-item]").length > 0;
            notificationSubtitle.textContent = hasNotifications ? "All caught up" : "No notifications yet";
        }
    }

    if (notificationDropdown && notificationToggle) {
        notificationDropdown.addEventListener("show.bs.dropdown", async () => {
            const unreadCount = Number(notificationToggle.dataset.unreadCount || "0");
            const markReadUrl = notificationToggle.dataset.markReadUrl;
            if (!markReadUrl || unreadCount <= 0 || notificationToggle.dataset.markingRead === "true") return;

            notificationToggle.dataset.markingRead = "true";

            try {
                const response = await fetch(markReadUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });
                const payload = await response.json();
                if (!response.ok || !payload.success) {
                    throw new Error(payload.message || "Unable to mark notifications as read.");
                }
                clearNotificationUnreadState();
            } catch (error) {
                showToast("error", error.message);
            } finally {
                delete notificationToggle.dataset.markingRead;
            }
        });
    }

    // Profile Page
    function getTimezonePresentation(timezoneValue, fallbackLabel = "") {
        try {
            const now = new Date();
            return {
                label: fallbackLabel || timezoneValue,
                date: new Intl.DateTimeFormat("en-US", {
                    timeZone: timezoneValue,
                    weekday: "long",
                    year: "numeric",
                    month: "long",
                    day: "2-digit"
                }).format(now),
                time: new Intl.DateTimeFormat("en-US", {
                    timeZone: timezoneValue,
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: true
                }).format(now)
            };
        } catch (error) {
            return {
                label: fallbackLabel || timezoneValue,
                date: "",
                time: ""
            };
        }
    }

    const saveProfileBtn = document.getElementById("saveProfileBtn");
    if (saveProfileBtn) {
        saveProfileBtn.addEventListener("click", function () {
            const editName = document.getElementById("editName");
            const editRole = document.getElementById("editRole");
            const editEmail = document.getElementById("editEmail");
            const editBio = document.getElementById("editBio");
            const editTeam = document.getElementById("editTeam");
            const editLocation = document.getElementById("editLocation");
            const editTimezone = document.getElementById("editTimezone");
            const editSkills = document.getElementById("editSkills");

            if (!editName || !editRole || !editEmail || !editBio || !editTeam || !editLocation || !editTimezone || !editSkills) {
                console.warn("Edit profile form elements missing");
                return;
            }

            const name = editName.value;
            const role = editRole.value;
            const email = editEmail.value;
            const bio = editBio.value;
            const team = editTeam.value;
            const timezoneValue = editTimezone.value;
            const timezoneLabel = editTimezone.options[editTimezone.selectedIndex]?.textContent || timezoneValue;
            const skills = editSkills.value.split(",").map(s => s.trim()).filter(s => s);
            const timezonePresentation = getTimezonePresentation(timezoneValue, timezoneLabel);

            const displayName = document.getElementById("displayName");
            if (displayName) displayName.textContent = name;
            const displayRole = document.getElementById("displayRole");
            if (displayRole) displayRole.innerHTML = `<i class="bi bi-shield-check"></i> ${role}`;
            const displayEmail = document.getElementById("displayEmail");
            if (displayEmail) displayEmail.textContent = email;
            const displayBio = document.getElementById("displayBio");
            if (displayBio) displayBio.textContent = bio;
            const displayTeam = document.getElementById("displayTeam");
            if (displayTeam) displayTeam.textContent = team;
            const displayLocation = document.getElementById("displayLocation");
            if (displayLocation) displayLocation.textContent = editLocation.value;
            const displayTimezone = document.getElementById("displayTimezone");
            if (displayTimezone) {
                displayTimezone.textContent = timezonePresentation.label;
                displayTimezone.dataset.timezoneValue = timezoneValue;
            }
            const displayLocalDate = document.getElementById("displayLocalDate");
            if (displayLocalDate) displayLocalDate.textContent = timezonePresentation.date;
            const displayLocalTime = document.getElementById("displayLocalTime");
            if (displayLocalTime) displayLocalTime.textContent = timezonePresentation.time;

            const avatarDisplay = document.getElementById("avatarDisplay");
            const nextInitials = name ? name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2) : "";
            if (avatarDisplay?.dataset?.avatarUserId) {
                const currentAvatarUrl = avatarDisplay.querySelector("img")?.getAttribute("src") || "";
                syncUserAvatar(avatarDisplay.dataset.avatarUserId, nextInitials, currentAvatarUrl, name || "Avatar");
            }

            const skillsContainer = document.getElementById("skillsContainer");
            if (skillsContainer) {
                skillsContainer.innerHTML = "";
                const skillIcons = {
                    Django: "bi-braces",
                    Python: "bi-code-slash",
                    MariaDB: "bi-database",
                    PostgreSQL: "bi-hdd-network",
                    "Node.js": "bi-node-plus",
                    React: "bi-browser-chrome",
                    Vue: "bi-browser-chrome",
                    Angular: "bi-browser-chrome",
                    default: "bi-tag"
                };

                skills.forEach(skill => {
                    const icon = skillIcons[skill] || skillIcons.default;
                    const skillTag = document.createElement("span");
                    skillTag.className = "skill-tag";
                    skillTag.innerHTML = `<i class="${icon}"></i> ${skill}`;
                    skillsContainer.appendChild(skillTag);
                });
            }

            const editModal = document.getElementById("editProfileModal");
            if (editModal) {
                const modal = bootstrap.Modal.getInstance(editModal);
                if (modal) modal.hide();
            }

            fetch(setTimezoneUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
                body: JSON.stringify({ timezone: timezoneValue })
            }).catch(() => {});

            showToast("success", "Profile updated successfully!");
        });
    }

    const editProfileModal = document.getElementById("editProfileModal");
    if (editProfileModal) {
        editProfileModal.addEventListener("show.bs.modal", function () {
            const displayName = document.getElementById("displayName");
            const displayRole = document.getElementById("displayRole");
            const displayEmail = document.getElementById("displayEmail");
            const displayBio = document.getElementById("displayBio");
            const displayTeam = document.getElementById("displayTeam");
            const displayLocation = document.getElementById("displayLocation");
            const displayTimezone = document.getElementById("displayTimezone");

            const editName = document.getElementById("editName");
            const editRole = document.getElementById("editRole");
            const editEmail = document.getElementById("editEmail");
            const editBio = document.getElementById("editBio");
            const editTeam = document.getElementById("editTeam");
            const editLocation = document.getElementById("editLocation");
            const editTimezone = document.getElementById("editTimezone");
            const editSkills = document.getElementById("editSkills");

            if (editName && displayName) editName.value = displayName.textContent;
            if (editRole && displayRole) {
                let roleText = displayRole.textContent;
                roleText = roleText.replace("âœ“", "").replace("bi-shield-check", "").trim();
                editRole.value = roleText;
            }
            if (editEmail && displayEmail) editEmail.value = displayEmail.textContent;
            if (editBio && displayBio) editBio.value = displayBio.textContent;
            if (editTeam && displayTeam) editTeam.value = displayTeam.textContent;
            if (editLocation && displayLocation) editLocation.value = displayLocation.textContent;
            if (editTimezone && displayTimezone) editTimezone.value = displayTimezone.dataset.timezoneValue || editTimezone.value;

            const skillsContainer = document.getElementById("skillsContainer");
            if (editSkills && skillsContainer) {
                editSkills.value = Array.from(skillsContainer.querySelectorAll(".skill-tag")).map(tag => tag.textContent.trim()).join(", ");
            }
        });
    }

    const profileAvatarTrigger = document.getElementById("profileAvatarTrigger");
    const profileAvatarInput = document.getElementById("profileAvatarInput");
    if (profileAvatarTrigger && profileAvatarInput && typeof uploadProfileAvatarUrl !== "undefined") {
        profileAvatarTrigger.addEventListener("click", () => profileAvatarInput.click());
        profileAvatarInput.addEventListener("change", async () => {
            const file = profileAvatarInput.files?.[0];
            if (!file) return;

            const formData = new FormData();
            formData.append("avatar", file);

            try {
                const response = await fetch(uploadProfileAvatarUrl, {
                    method: "POST",
                    headers: { "X-CSRFToken": csrfToken },
                    body: formData
                });
                const rawResponse = await response.text();
                let payload = {};

                try {
                    payload = rawResponse ? JSON.parse(rawResponse) : {};
                } catch (parseError) {
                    throw new Error("Unable to upload photo right now.");
                }

                if (!response.ok || !payload.success) throw new Error(payload.message || "Unable to upload photo.");
                syncUserAvatar(payload.user_id, payload.user_initials, payload.avatar_url, "Profile photo");
                showToast("success", payload.message);
            } catch (error) {
                showToast("error", error.message);
            } finally {
                profileAvatarInput.value = "";
            }
        });
    }
});
