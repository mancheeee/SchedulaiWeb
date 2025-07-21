const calendarToggle = document.getElementById("calendar-toggle");
const calendarPopup = document.getElementById("calendar-popup");
const calendarCloseBtn = document.getElementById("calendar-close");

let calendar; // To reuse and refresh calendar instance

calendarToggle.addEventListener("click", (e) => {
  e.stopPropagation();
  const isNowVisible = calendarPopup.classList.toggle("show");

  if (isNowVisible) {
    const calendarEl = document.getElementById("calendar");
    calendarEl.innerHTML = "<p>📡 Loading your events...</p>";

    fetch("/user_calendar_events?user_id=demo_user")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load calendar events");
        return res.json();
      })
      .then((data) => {
        calendarEl.innerHTML = "";

        // Destroy previous instance if exists
        if (calendar) calendar.destroy();

        calendar = new FullCalendar.Calendar(calendarEl, {
          initialView: "dayGridMonth",
          height: "auto",
          events: data.events.map((e) => ({
            id: e.id, // Optional: set ID to support later editing
            title: e.summary || "Untitled",
            start: e.start.dateTime || e.start.date,
            end: e.end.dateTime || e.end.date,
          })),
        });

        calendar.render();
      })
      .catch((err) => {
        console.error("❌ Error loading calendar:", err);
        calendarEl.innerHTML =
          "<p style='color: red;'>Failed to load calendar events.</p>";
      });
  }
});

// ❌ Close button inside the calendar header
calendarCloseBtn.addEventListener("click", () => {
  calendarPopup.classList.remove("show");
});

// ✅ Function to refresh calendar after bot actions
function refreshCalendar() {
  if (!calendar) return;

  fetch("/user_calendar_events?user_id=demo_user")
    .then((res) => {
      if (!res.ok) throw new Error("Failed to refresh events");
      return res.json();
    })
    .then((data) => {
      calendar.removeAllEvents();
      data.events.forEach((e) => {
        calendar.addEvent({
          id: e.id,
          title: e.summary || "Untitled",
          start: e.start.dateTime || e.start.date,
          end: e.end.dateTime || e.end.date,
        });
      });
    })
    .catch((err) => {
      console.error("❌ Failed to refresh calendar:", err);
    });
}
