document.addEventListener("DOMContentLoaded", function () {
    const grid = document.getElementById("tasksGrid");
    const searchInput = document.getElementById("taskSearchInput");
    const filterPills = document.querySelectorAll("[data-task-filter]");
    const emptyState = document.getElementById("tasksEmptyState");

    if (!grid || !filterPills.length || !emptyState) return;

    let activeFilter = "all";

    function applyTaskFilters() {
        const query = (searchInput?.value || "").trim().toLowerCase();
        const cards = Array.from(grid.querySelectorAll("[data-task-card]"));
        let visibleCount = 0;

        cards.forEach(card => {
            const status = card.dataset.status || "";
            const isOverdue = card.dataset.overdue === "true";
            const search = card.dataset.search || "";
            const matchesFilter =
                activeFilter === "all" ||
                (activeFilter === "overdue" ? isOverdue : status === activeFilter);
            const matchesQuery = !query || search.includes(query);
            const visible = matchesFilter && matchesQuery;

            card.style.display = visible ? "" : "none";
            if (visible) visibleCount += 1;
        });

        emptyState.style.display = visibleCount ? "none" : "block";
    }

    filterPills.forEach(pill => {
        pill.addEventListener("click", () => {
            filterPills.forEach(node => node.classList.remove("active"));
            pill.classList.add("active");
            activeFilter = pill.dataset.taskFilter || "all";
            applyTaskFilters();
        });
    });

    if (searchInput) {
        searchInput.addEventListener("input", applyTaskFilters);
    }

    applyTaskFilters();
});
