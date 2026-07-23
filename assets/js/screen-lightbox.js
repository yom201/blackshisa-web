(function () {
  var lightbox = document.querySelector("[data-screen-lightbox]");
  if (!lightbox) return;

  var image = lightbox.querySelector("[data-lightbox-image]");
  var closeButton = lightbox.querySelector("[data-lightbox-close]");
  var buttons = Array.prototype.slice.call(document.querySelectorAll(".screen-open"));
  var lastActive = null;
  var currentIndex = 0;
  var touchStartX = 0;
  var touchStartY = 0;
  var swipeThreshold = 42;

  function showPreview(index) {
    currentIndex = (index + buttons.length) % buttons.length;
    var button = buttons[currentIndex];
    var thumbnail = button.querySelector("img");
    lastActive = button;
    image.src = button.getAttribute("data-full");
    image.alt = thumbnail ? thumbnail.alt : "";
  }

  function openPreview(index) {
    showPreview(index);
    lightbox.hidden = false;
    document.documentElement.classList.add("lightbox-open");
    closeButton.focus();
  }

  function closePreview() {
    lightbox.hidden = true;
    image.removeAttribute("src");
    image.alt = "";
    document.documentElement.classList.remove("lightbox-open");
    if (lastActive) lastActive.focus({ preventScroll: true });
  }

  function showNext() {
    showPreview(currentIndex + 1);
  }

  function showPrevious() {
    showPreview(currentIndex - 1);
  }

  buttons.forEach(function (button, index) {
    button.addEventListener("click", function () {
      openPreview(index);
    });
  });

  closeButton.addEventListener("click", closePreview);

  lightbox.addEventListener("click", function (event) {
    if (event.target === lightbox) closePreview();
  });

  lightbox.addEventListener("touchstart", function (event) {
    if (lightbox.hidden || event.touches.length !== 1) return;
    touchStartX = event.touches[0].clientX;
    touchStartY = event.touches[0].clientY;
  }, { passive: true });

  lightbox.addEventListener("touchend", function (event) {
    if (lightbox.hidden || !event.changedTouches.length) return;
    var deltaX = event.changedTouches[0].clientX - touchStartX;
    var deltaY = event.changedTouches[0].clientY - touchStartY;
    if (Math.abs(deltaX) < swipeThreshold || Math.abs(deltaX) < Math.abs(deltaY) * 1.25) return;
    if (deltaX < 0) {
      showNext();
    } else {
      showPrevious();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (lightbox.hidden) return;
    if (event.key === "Escape") closePreview();
    if (event.key === "ArrowRight") showNext();
    if (event.key === "ArrowLeft") showPrevious();
  });
})();
