const guideToggle = document.getElementById("guide-toggle");
const guidePopup = document.getElementById("guide-popup");

guideToggle.addEventListener("click", (e) => {
  e.stopPropagation();
  guidePopup.classList.toggle("show");
});

document.addEventListener("click", function (e) {
  if (!guidePopup.contains(e.target) && !guideToggle.contains(e.target)) {
    guidePopup.classList.remove("show");
  }
});
