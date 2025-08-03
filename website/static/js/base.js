 document.addEventListener("DOMContentLoaded", () => {
 // Dark mode toggle logic
  const toggle = document.getElementById("dark-toggle");
  const html = document.documentElement;

  const savedTheme = localStorage.getItem("theme");
  if (
    savedTheme === "dark" ||
    (!savedTheme && window.matchMedia("(prefers-color-scheme: dark)").matches)
  ) {
    html.classList.add("dark");
  } else {
    html.classList.remove("dark");
  }

  if (toggle) {
    toggle.addEventListener("click", () => {
      html.classList.toggle("dark");
      if (html.classList.contains("dark")) {
        localStorage.setItem("theme", "dark");
        toggle.setAttribute("aria-pressed", "true");
      } else {
        localStorage.setItem("theme", "light");
        toggle.setAttribute("aria-pressed", "false");
      }
    });
  }

  // User dropdown toggle
  const userButton = document.getElementById("user-menu-button");
  const userDropdown = document.getElementById("user-dropdown");

  if (userButton && userDropdown) {
    userButton.addEventListener("click", () => {
      userDropdown.classList.toggle("hidden");
    });

    // Optional: Close dropdown if clicked outside
    document.addEventListener("click", (e) => {
      if (!userButton.contains(e.target) && !userDropdown.contains(e.target)) {
        userDropdown.classList.add("hidden");
      }
    });
  }


});