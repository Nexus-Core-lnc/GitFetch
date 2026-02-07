// Sélection des éléments
const passwordInput = document.getElementById("password");
const confirmPasswordInput = document.getElementById("confirmPassword");
const emailInput = document.getElementById("email");
const form = document.getElementById("registerForm");
const passwordCriteria = document.getElementById("passwordCriteria");
const matchIndicator = document.getElementById("matchIndicator");
const errorModal = document.getElementById("errorModal");
const successModal = document.getElementById("successModal");
const errorMessage = document.getElementById("errorMessage");

// Critères de validation
const criteria = {
  length: { regex: /.{8,}/, element: document.getElementById("length") },
  uppercase: { regex: /[A-Z]/, element: document.getElementById("uppercase") },
  lowercase: { regex: /[a-z]/, element: document.getElementById("lowercase") },
  number: { regex: /[0-9]/, element: document.getElementById("number") },
  special: {
    regex: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]/,
    element: document.getElementById("special"),
  },
};

// Fonctions d'affichage des modales
function showErrorModal(message) {
  errorMessage.textContent = message;
  errorModal.style.display = "flex";
}

function closeErrorModal() {
  errorModal.style.display = "none";
}

function showSuccessModal() {
  successModal.style.display = "flex";
}

// --- GESTIONNAIRE DE SOUMISSION DU FORMULAIRE ---
form.addEventListener("submit", function (e) {
  // 1. On empêche l'envoi immédiat pour valider
  e.preventDefault();

  // Validation Email
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(emailInput.value)) {
    showErrorModal("⚠️ Veuillez entrer une adresse e-mail valide");
    return;
  }

  // Validation Critères Password
  let allMet = true;
  for (let key in criteria) {
    if (!criteria[key].regex.test(passwordInput.value)) {
      allMet = false;
      break;
    }
  }

  if (!allMet) {
    showErrorModal(
      "⚠️ Le mot de passe ne respecte pas tous les critères de sécurité",
    );
    return;
  }

  // Validation Correspondance
  if (passwordInput.value !== confirmPasswordInput.value) {
    showErrorModal("⚠️ Les mots de passe ne correspondent pas");
    return;
  }

  // 2. Si TOUT EST VALIDE
  showSuccessModal();

  // 3. ENVOI RÉEL AU SERVEUR (FLASK) après 2 secondes
  setTimeout(() => {
    form.submit();
  }, 2000);
});

// --- VALIDATIONS EN TEMPS RÉEL (VISUEL) ---
passwordInput.addEventListener("input", function () {
  const password = this.value;
  passwordCriteria.classList.add("show");

  for (let key in criteria) {
    const criterion = criteria[key];
    const icon = criterion.element.querySelector("i");
    if (criterion.regex.test(password)) {
      criterion.element.classList.add("met");
      icon.className = "fas fa-check";
    } else {
      criterion.element.classList.remove("met");
      icon.className = "fas fa-times";
    }
  }
  checkPasswordMatch();
});

confirmPasswordInput.addEventListener("input", checkPasswordMatch);

function checkPasswordMatch() {
  if (confirmPasswordInput.value.length > 0) {
    if (passwordInput.value === confirmPasswordInput.value) {
      confirmPasswordInput.classList.add("valid");
      confirmPasswordInput.classList.remove("invalid");
      matchIndicator.innerHTML =
        '<i class="fas fa-check-circle"></i> Les mots de passe correspondent';
      matchIndicator.className = "match-indicator show match";
    } else {
      confirmPasswordInput.classList.add("invalid");
      confirmPasswordInput.classList.remove("valid");
      matchIndicator.innerHTML =
        '<i class="fas fa-times-circle"></i> Les mots de passe ne correspondent pas';
      matchIndicator.className = "match-indicator show no-match";
    }
  }
}

function togglePassword(inputId) {
  const input = document.getElementById(inputId);
  const icon = event.currentTarget.querySelector("i");
  if (input.type === "password") {
    input.type = "text";
    icon.classList.replace("fa-eye", "fa-eye-slash");
  } else {
    input.type = "password";
    icon.classList.replace("fa-eye-slash", "fa-eye");
  }
}

// --- EXPORTATION DES IDENTIFIANTS (BOUTON BLEU) ---
function exportCredentials() {
  const email = emailInput.value;
  const password = passwordInput.value;

  if (!email || !password || password !== confirmPasswordInput.value) {
    showErrorModal("⚠️ Remplissez correctement les champs avant d'exporter");
    return;
  }

  const txtContent = `PROJET GITFETCH\n\nEmail: ${email}\nPassword: ${password}\nDate: ${new Date().toLocaleString()}`;
  const blob = new Blob([txtContent], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `gitfetch_credentials.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

// Fermeture modale
window.onclick = function (event) {
  if (event.target == errorModal) closeErrorModal();
};
