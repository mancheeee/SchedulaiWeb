const chatPopup = document.getElementById("chat-popup");
const chatLog = document.getElementById("chat-log");
const inputBox = document.getElementById("chat-input");
const chatForm = document.getElementById("chat-form");
const fullscreenBtn = document.getElementById("fullscreen-btn");



function toggleChat() {
  chatPopup.classList.toggle("active");
}

if (!chatPopup.classList.contains("active")) {
  chatPopup.classList.add("active");

  // Reset and trigger animation
  chatPopup.classList.remove("fade-in");
  void chatPopup.offsetWidth; // Forces reflow
  chatPopup.classList.add("fade-in");
} else {
  chatPopup.classList.remove("active");
  chatPopup.classList.remove("fade-in");
}

chatForm.onsubmit = async (e) => {
  e.preventDefault();
  const userMessage = inputBox.value.trim();
  if (!userMessage) return;

  appendMessage("You", userMessage, "user");
  inputBox.value = "";

  document.getElementById("loading").style.display = "block";

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: userMessage,
      }),
    });

    const data = await res.json();
    console.log("📦 FastAPI Response:", data);
    const botMessage =
  data.message ||
  (data.event_created &&
    `✅ Event created: ${data.details.summary} on ${data.details.start.dateTime}`) ||
  (data.error && `❌ Error: ${data.error}`) ||
  "";

if (
  botMessage.includes("✅ Event created") ||
  botMessage.includes("✅ Event deleted") ||
  botMessage.includes("✅ Event updated")
) {
  if (typeof refreshCalendar === "function") {
    refreshCalendar(); // 🔄 Real-time update
  }
}


    if (data.event_created) {
      appendMessage(
        "Schedulai",
        `✅ Event created: ${data.details.summary} on ${data.details.start.dateTime}`,
        "bot"
      );
    } else if (data.free_slots) {
      appendMessage("Schedulai", `${data.message}`, "bot");
      data.free_slots.forEach((slot) => {
        const readable = `🕒 ${new Date(slot.start).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })} - ${new Date(slot.end).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })}`;
        const el = document.createElement("div");
        el.className = "slot";
        el.textContent = readable;
        el.onclick = () => {
          inputBox.value = `Schedule meeting at ${readable} on ${
            slot.start.split("T")[0]
          }`;
          inputBox.focus();
        };
        chatLog.appendChild(el);
      });
    } else if (data.message) {
      appendMessage("Schedulai", data.message, "bot");
    } else if (data.error) {
      appendMessage("Schedulai", `❌ Error: ${data.error}`, "bot");
    } else {
      appendMessage("Schedulai", `⚠️ Unexpected response`, "bot");
    }

    chatLog.scrollTop = chatLog.scrollHeight;
  } catch (err) {
    appendMessage("Schedulai", `❌ Request failed: ${err.message}`, "bot");
  }

  document.getElementById("loading").style.display = "none";
};

function appendMessage(sender, text, cssClass) {
  const msg = document.createElement("div");
  msg.className = cssClass;
  msg.innerHTML = `<strong>${sender}:</strong> ${text}`;
  chatLog.appendChild(msg);
  chatLog.scrollTop = chatLog.scrollHeight;
}

document.addEventListener("click", function (e) {
  if (
    !chatPopup.contains(e.target) &&
    !document.getElementById("chat-toggle").contains(e.target)
  ) {
    chatPopup.classList.remove("active");
  }
});

async function loadBookedEvents() {
  const today = new Date().toISOString().split("T")[0];
  const res = await fetch(`/calendar/booked?date=${today}`);
  const data = await res.json();

  if (data.booked && data.booked.length > 0) {
    appendMessage("Schedulai", `📌 Booked Events for today:`, "bot");
    data.booked.forEach((event) => {
      const readable = `📍 ${event.summary} | 🕒 ${new Date(
        event.start
      ).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })} - ${new Date(event.end).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })}`;
      const el = document.createElement("div");
      el.className = "slot";
      el.style.background = "#ffe6e6";
      el.style.borderColor = "#ffb3b3";
      el.style.color = "#8b0000";
      el.textContent = readable;
      el.onclick = () => deleteEvent(event.id);
      chatLog.appendChild(el);
    });
  } else {
    appendMessage("Schedulai", "✅ No booked events today.", "bot");
  }
}

function deleteEvent(eventId) {
  fetch(`/calendar/event/${eventId}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  })
    .then((res) => res.json())
    .then(() => {
      appendMessage("Schedulai", `🗑️ Event deleted`, "bot");
    })
    .catch((err) => {
      appendMessage("Schedulai", `❌ Failed to delete: ${err.message}`, "bot");
    });
}

function typeMessage(text, callback) {
  let i = 0;
  const interval = setInterval(() => {
    if (i < text.length) {
      chatLog.lastChild.innerHTML += text.charAt(i++);
    } else {
      clearInterval(interval);
      if (callback) callback();
    }
  }, 20);
}

// ✅ Fullscreen Toggle
if (fullscreenBtn) {
  fullscreenBtn.addEventListener("click", () => {
    chatPopup.classList.toggle("fullscreen");

    if (chatPopup.classList.contains("fullscreen")) {
      fullscreenBtn.textContent = "🗕";
      fullscreenBtn.title = "Exit Fullscreen";
    } else {
      fullscreenBtn.textContent = "⛶";
      fullscreenBtn.title = "Enter Fullscreen";
    }
  });
}

const guideToggle = document.getElementById("guide-toggle");
const guidePopup = document.getElementById("guide-popup");

guideToggle.addEventListener("click", (e) => {
  e.stopPropagation(); // Prevent bubble to document
  guidePopup.classList.toggle("show");
});

document.addEventListener("click", function (e) {
  if (!guidePopup.contains(e.target) && !guideToggle.contains(e.target)) {
    guidePopup.classList.remove("show");
  }
});

function toggleCalendar() {
  const popup = document.getElementById("calendarPopup");
  popup.classList.toggle("hidden");
}

document
  .getElementById("calendarToggleBtn")
  .addEventListener("click", toggleCalendar);



