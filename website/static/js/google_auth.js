document.addEventListener("DOMContentLoaded", () => {
  const loginBtn = document.getElementById("google-login");
  if (!loginBtn) {
    console.error("Login button not found!");
    return;
  }
  loginBtn.addEventListener("click", () => {
    loginBtn.disabled = true;
    loginBtn.textContent = "Redirecting...";
    window.location.href = "http://localhost:8000/auth/login";  
  });
});
