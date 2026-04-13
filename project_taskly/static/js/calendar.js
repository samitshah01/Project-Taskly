document.addEventListener("DOMContentLoaded", () => {
    const eventsNode = document.getElementById("calendar-events-data");
    const todayNode = document.getElementById("calendar-today-data");
    const monthView = document.getElementById("calendarMonthView");
    if (!eventsNode || !todayNode || !monthView) return;

    const events = JSON.parse(eventsNode.textContent || "[]");
    const todayIso = JSON.parse(todayNode.textContent || '"1970-01-01"');
    const today = new Date(`${todayIso}T00:00:00`);
    let current = new Date(`${todayIso}T00:00:00`);
    let view = "month";

    const monthGrid = document.getElementById("calendarMonthGrid");
    const weekHeader = document.getElementById("calendarWeekHeader");
    const weekHours = document.getElementById("calendarWeekHours");
    const weekColumns = document.getElementById("calendarWeekColumns");
    const dayTimeline = document.getElementById("calendarDayTimeline");
    const dayTitle = document.getElementById("calendarDayTitle");
    const daySubtitle = document.getElementById("calendarDaySubtitle");
    const title = document.getElementById("calendarTitle");
    const miniMonthLabel = document.getElementById("calendarMiniMonthLabel");
    const miniGrid = document.getElementById("calendarMiniGrid");

    const popover = document.createElement("div");
    popover.className = "calendar-event-popover";
    popover.innerHTML = `
        <button type="button" class="calendar-event-popover-close" aria-label="Close"><i class="bi bi-x-lg"></i></button>
        <div class="calendar-event-popover-strip"></div>
        <h6 class="calendar-event-popover-title"></h6>
        <div class="calendar-event-popover-row"><i class="bi bi-calendar3"></i><span data-calendar-popover-date></span></div>
        <div class="calendar-event-popover-row"><i class="bi bi-clock"></i><span data-calendar-popover-time></span></div>
        <div class="calendar-event-popover-row"><i class="bi bi-folder2"></i><span data-calendar-popover-project></span></div>
        <div class="calendar-event-popover-row"><i class="bi bi-info-circle"></i><span data-calendar-popover-meta></span></div>
        <div class="calendar-event-popover-row"><i class="bi bi-people"></i><span data-calendar-popover-team></span></div>
        <a class="btn-primary-custom calendar-event-popover-link" href="#">Open Project</a>
    `;
    document.body.appendChild(popover);

    const popoverStrip = popover.querySelector(".calendar-event-popover-strip");
    const popoverTitle = popover.querySelector(".calendar-event-popover-title");
    const popoverDate = popover.querySelector("[data-calendar-popover-date]");
    const popoverTime = popover.querySelector("[data-calendar-popover-time]");
    const popoverProject = popover.querySelector("[data-calendar-popover-project]");
    const popoverMeta = popover.querySelector("[data-calendar-popover-meta]");
    const popoverTeam = popover.querySelector("[data-calendar-popover-team]");
    const popoverLink = popover.querySelector(".calendar-event-popover-link");

    const monthNames = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];
    const dayNamesShort = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

    function formatIso(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, "0");
        const d = String(date.getDate()).padStart(2, "0");
        return `${y}-${m}-${d}`;
    }

    function formatLongDate(date) {
        return date.toLocaleDateString("en-GB", {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric"
        });
    }

    function getEventsOn(dateIso) {
        return events.filter((event) => event.date === dateIso);
    }

    function getStartOfWeek(date) {
        const copy = new Date(date);
        copy.setDate(copy.getDate() - copy.getDay());
        copy.setHours(0, 0, 0, 0);
        return copy;
    }

    function closePopover() {
        popover.classList.remove("is-visible");
    }

    function openPopover(event, anchor) {
        popoverStrip.style.background = event.color || "var(--accent)";
        popoverTitle.textContent = event.title;
        popoverDate.textContent = new Date(`${event.date}T00:00:00`).toLocaleDateString("en-GB", {
            weekday: "long",
            day: "numeric",
            month: "long"
        });
        popoverTime.textContent = event.time || "All day";
        popoverProject.textContent = event.project || "Project";
        popoverMeta.textContent = event.meta || "Calendar event";
        popoverTeam.textContent = event.team || "Team";
        popoverLink.href = event.url || "#";

        const rect = anchor.getBoundingClientRect();
        let top = rect.top + window.scrollY + 8;
        let left = rect.right + window.scrollX + 12;

        if (left + 300 > window.innerWidth + window.scrollX) {
            left = rect.left + window.scrollX - 280;
        }
        if (top + 240 > window.innerHeight + window.scrollY) {
            top = window.innerHeight + window.scrollY - 250;
        }

        popover.style.top = `${Math.max(window.scrollY + 12, top)}px`;
        popover.style.left = `${Math.max(window.scrollX + 12, left)}px`;
        popover.classList.add("is-visible");
    }

    function makeEventChip(event, compact = false) {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = compact ? "calendar-event-chip is-compact" : "calendar-event-chip";
        chip.textContent = compact ? event.title : `${event.time} · ${event.title}`;
        chip.style.setProperty("--event-color", event.color || "var(--accent)");
        chip.addEventListener("click", (domEvent) => {
            domEvent.stopPropagation();
            openPopover(event, chip);
        });
        return chip;
    }

    function renderMonth() {
        monthGrid.innerHTML = "";
        title.textContent = `${monthNames[current.getMonth()]} ${current.getFullYear()}`;

        const first = new Date(current.getFullYear(), current.getMonth(), 1);
        const startOffset = first.getDay();
        const daysInMonth = new Date(current.getFullYear(), current.getMonth() + 1, 0).getDate();
        const prevMonthDays = new Date(current.getFullYear(), current.getMonth(), 0).getDate();
        const totalCells = Math.ceil((startOffset + daysInMonth) / 7) * 7;

        for (let index = 0; index < totalCells; index += 1) {
            const cell = document.createElement("button");
            cell.type = "button";
            cell.className = "calendar-day-cell";

            let dayNumber;
            let date;
            let outsideCurrentMonth = false;

            if (index < startOffset) {
                dayNumber = prevMonthDays - startOffset + index + 1;
                date = new Date(current.getFullYear(), current.getMonth() - 1, dayNumber);
                outsideCurrentMonth = true;
            } else if (index >= startOffset + daysInMonth) {
                dayNumber = index - startOffset - daysInMonth + 1;
                date = new Date(current.getFullYear(), current.getMonth() + 1, dayNumber);
                outsideCurrentMonth = true;
            } else {
                dayNumber = index - startOffset + 1;
                date = new Date(current.getFullYear(), current.getMonth(), dayNumber);
            }

            const iso = formatIso(date);
            const dayEvents = getEventsOn(iso);

            if (outsideCurrentMonth) cell.classList.add("is-outside");
            if (iso === formatIso(today)) cell.classList.add("is-today");
            if (iso === formatIso(current)) cell.classList.add("is-selected");

            cell.innerHTML = `<span class="calendar-day-number">${dayNumber}</span>`;

            const stack = document.createElement("div");
            stack.className = "calendar-day-events";
            dayEvents.slice(0, 3).forEach((event) => stack.appendChild(makeEventChip(event, true)));

            if (dayEvents.length > 3) {
                const more = document.createElement("span");
                more.className = "calendar-day-more";
                more.textContent = `+${dayEvents.length - 3} more`;
                stack.appendChild(more);
            }

            cell.appendChild(stack);
            cell.addEventListener("click", () => {
                current = new Date(`${iso}T00:00:00`);
                renderAll();
            });
            monthGrid.appendChild(cell);
        }
    }

    function renderWeek() {
        title.textContent = `Week of ${formatLongDate(getStartOfWeek(current))}`;
        weekHeader.innerHTML = `<div class="calendar-week-corner"></div>`;
        weekHours.innerHTML = "";
        weekColumns.innerHTML = "";

        const start = getStartOfWeek(current);
        for (let hour = 0; hour < 24; hour += 1) {
            const hourLabel = document.createElement("div");
            hourLabel.className = "calendar-week-hour";
            hourLabel.textContent = `${String(hour).padStart(2, "0")}:00`;
            weekHours.appendChild(hourLabel);
        }

        for (let offset = 0; offset < 7; offset += 1) {
            const date = new Date(start);
            date.setDate(start.getDate() + offset);
            const iso = formatIso(date);
            const header = document.createElement("div");
            header.className = "calendar-week-day-head";
            header.innerHTML = `
                <span>${dayNamesShort[date.getDay()]}</span>
                <strong class="${iso === formatIso(today) ? "is-today" : ""}">${date.getDate()}</strong>
            `;
            weekHeader.appendChild(header);

            const column = document.createElement("div");
            column.className = "calendar-week-day-column";
            for (let hour = 0; hour < 24; hour += 1) {
                const slot = document.createElement("div");
                slot.className = "calendar-week-slot";
                column.appendChild(slot);
            }

            getEventsOn(iso).forEach((event) => {
                const [hoursRaw, minutesRaw] = String(event.time || "09:00").split(":");
                const hours = Number(hoursRaw || 0);
                const minutes = Number(minutesRaw || 0);
                const block = document.createElement("button");
                block.type = "button";
                block.className = "calendar-week-event";
                block.style.setProperty("--event-color", event.color || "var(--accent)");
                block.style.top = `${hours * 58 + (minutes / 60) * 58}px`;
                block.innerHTML = `<strong>${event.title}</strong><span>${event.time}</span>`;
                block.addEventListener("click", (domEvent) => {
                    domEvent.stopPropagation();
                    openPopover(event, block);
                });
                column.appendChild(block);
            });

            weekColumns.appendChild(column);
        }
    }

    function renderDay() {
        title.textContent = formatLongDate(current);
        dayTitle.textContent = formatLongDate(current);
        daySubtitle.textContent = `${getEventsOn(formatIso(current)).length} scheduled event(s)`;
        dayTimeline.innerHTML = "";

        const dayEvents = getEventsOn(formatIso(current));
        for (let hour = 0; hour < 24; hour += 1) {
            const row = document.createElement("div");
            row.className = "calendar-day-row";
            row.innerHTML = `
                <div class="calendar-day-time">${String(hour).padStart(2, "0")}:00</div>
                <div class="calendar-day-slot"></div>
            `;

            const slot = row.querySelector(".calendar-day-slot");
            dayEvents
                .filter((event) => Number(String(event.time || "09:00").split(":")[0]) === hour)
                .forEach((event) => {
                    const block = document.createElement("button");
                    block.type = "button";
                    block.className = "calendar-day-event";
                    block.style.setProperty("--event-color", event.color || "var(--accent)");
                    block.innerHTML = `
                        <strong>${event.title}</strong>
                        <span>${event.time} · ${event.project}</span>
                        <small>${event.meta || ""}</small>
                    `;
                    block.addEventListener("click", (domEvent) => {
                        domEvent.stopPropagation();
                        openPopover(event, block);
                    });
                    slot.appendChild(block);
                });

            dayTimeline.appendChild(row);
        }
    }

    function renderMiniCalendar() {
        miniGrid.innerHTML = "";
        miniMonthLabel.textContent = `${monthNames[current.getMonth()]} ${current.getFullYear()}`;

        const first = new Date(current.getFullYear(), current.getMonth(), 1);
        const startOffset = first.getDay();
        const daysInMonth = new Date(current.getFullYear(), current.getMonth() + 1, 0).getDate();
        const prevMonthDays = new Date(current.getFullYear(), current.getMonth(), 0).getDate();
        const totalCells = Math.ceil((startOffset + daysInMonth) / 7) * 7;

        for (let index = 0; index < totalCells; index += 1) {
            const cell = document.createElement("button");
            cell.type = "button";
            cell.className = "calendar-mini-day";

            let dayNumber;
            let date;
            let outsideCurrentMonth = false;

            if (index < startOffset) {
                dayNumber = prevMonthDays - startOffset + index + 1;
                date = new Date(current.getFullYear(), current.getMonth() - 1, dayNumber);
                outsideCurrentMonth = true;
            } else if (index >= startOffset + daysInMonth) {
                dayNumber = index - startOffset - daysInMonth + 1;
                date = new Date(current.getFullYear(), current.getMonth() + 1, dayNumber);
                outsideCurrentMonth = true;
            } else {
                dayNumber = index - startOffset + 1;
                date = new Date(current.getFullYear(), current.getMonth(), dayNumber);
            }

            const iso = formatIso(date);
            cell.textContent = dayNumber;
            if (outsideCurrentMonth) cell.classList.add("is-outside");
            if (iso === formatIso(today)) cell.classList.add("is-today");
            if (iso === formatIso(current)) cell.classList.add("is-selected");
            if (getEventsOn(iso).length) cell.classList.add("has-events");

            cell.addEventListener("click", () => {
                current = new Date(`${iso}T00:00:00`);
                renderAll();
            });
            miniGrid.appendChild(cell);
        }
    }

    function syncViewState() {
        monthView.classList.toggle("d-none", view !== "month");
        document.getElementById("calendarWeekView").classList.toggle("d-none", view !== "week");
        document.getElementById("calendarDayView").classList.toggle("d-none", view !== "day");

        document.querySelectorAll("[data-calendar-view]").forEach((button) => {
            button.classList.toggle("active", button.dataset.calendarView === view);
        });
    }

    function renderAll() {
        syncViewState();
        renderMiniCalendar();
        if (view === "month") renderMonth();
        if (view === "week") renderWeek();
        if (view === "day") renderDay();
    }

    document.querySelectorAll("[data-calendar-view]").forEach((button) => {
        button.addEventListener("click", () => {
            view = button.dataset.calendarView || "month";
            renderAll();
        });
    });

    document.getElementById("calendarPrevBtn")?.addEventListener("click", () => {
        if (view === "month") current.setMonth(current.getMonth() - 1);
        else if (view === "week") current.setDate(current.getDate() - 7);
        else current.setDate(current.getDate() - 1);
        current = new Date(current);
        renderAll();
    });

    document.getElementById("calendarNextBtn")?.addEventListener("click", () => {
        if (view === "month") current.setMonth(current.getMonth() + 1);
        else if (view === "week") current.setDate(current.getDate() + 7);
        else current.setDate(current.getDate() + 1);
        current = new Date(current);
        renderAll();
    });

    document.getElementById("calendarTodayBtn")?.addEventListener("click", () => {
        current = new Date(`${todayIso}T00:00:00`);
        renderAll();
    });

    document.getElementById("calendarMiniPrevBtn")?.addEventListener("click", () => {
        current.setMonth(current.getMonth() - 1);
        current = new Date(current);
        renderAll();
    });

    document.getElementById("calendarMiniNextBtn")?.addEventListener("click", () => {
        current.setMonth(current.getMonth() + 1);
        current = new Date(current);
        renderAll();
    });

    popover.querySelector(".calendar-event-popover-close")?.addEventListener("click", closePopover);
    document.addEventListener("click", (event) => {
        if (!popover.contains(event.target)) closePopover();
    });

    renderAll();
});
