const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const form = document.getElementById('loginForm');
const emailFeedback = document.getElementById('emailFeedback');
const passwordFeedback = document.getElementById('passwordFeedback');
const errorModal = document.getElementById('errorModal');
const successModal = document.getElementById('successModal');
const errorMessage = document.getElementById('errorMessage');

// Fonctions pour les modales
function showErrorModal(message) {
    errorMessage.textContent = message;
    errorModal.style.display = 'flex';
}

function closeErrorModal() {
    errorModal.style.display = 'none';
}

function showSuccessModal() {
    successModal.style.display = 'flex';
    // Simulation de redirection après 2 secondes
    setTimeout(() => {
        closeSuccessModal();
        // Ici, vous pouvez rediriger vers le tableau de bord
        // window.location.href = '/dashboard';
    }, 2000);
}

function closeSuccessModal() {
    successModal.style.display = 'none';
}

// Fermer les modales en cliquant à l'extérieur
window.addEventListener('click', function(event) {
    if (event.target === errorModal) {
        closeErrorModal();
    }
    if (event.target === successModal) {
        closeSuccessModal();
    }
});

// Fermer les modales avec la touche Échap
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeErrorModal();
        closeSuccessModal();
    }
});

// Validation de l'email en temps réel
emailInput.addEventListener('input', function() {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (!this.value) {
        this.classList.remove('valid', 'invalid');
        emailFeedback.textContent = '';
        emailFeedback.className = 'input-feedback';
        return;
    }
    
    if (emailRegex.test(this.value)) {
        this.classList.add('valid');
        this.classList.remove('invalid');
        emailFeedback.textContent = '✓ Format d\'email valide';
        emailFeedback.className = 'input-feedback success';
    } else {
        this.classList.add('invalid');
        this.classList.remove('valid');
        emailFeedback.textContent = '✗ Veuillez entrer une adresse email valide';
        emailFeedback.className = 'input-feedback error';
    }
});

// Validation du mot de passe en temps réel
passwordInput.addEventListener('input', function() {
    if (!this.value) {
        this.classList.remove('valid', 'invalid');
        passwordFeedback.textContent = '';
        passwordFeedback.className = 'input-feedback';
        return;
    }
    
    if (this.value.length >= 6) {
        this.classList.add('valid');
        this.classList.remove('invalid');
        passwordFeedback.textContent = '✓ Mot de passe valide';
        passwordFeedback.className = 'input-feedback success';
    } else {
        this.classList.add('invalid');
        this.classList.remove('valid');
        passwordFeedback.textContent = '✗ Le mot de passe doit contenir au moins 6 caractères';
        passwordFeedback.className = 'input-feedback error';
    }
});

function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const toggleBtn = document.getElementById('togglePassword');
    
    if (input.type === 'password') {
        input.type = 'text';
        toggleBtn.classList.remove('fa-eye');
        toggleBtn.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        toggleBtn.classList.remove('fa-eye-slash');
        toggleBtn.classList.add('fa-eye');
    }
}



// // Connexion avec Google
// document.querySelector('.google-btn').addEventListener('click', function() {
//     showErrorModal('Connexion avec Google - Fonctionnalité à venir');
// });

// // Connexion avec GitHub
// document.querySelector('.github-btn').addEventListener('click', function() {
//     showErrorModal('Connexion avec GitHub - Fonctionnalité à venir');
// });

// Soumission du formulaire
form.addEventListener('submit', function(e) {
    // Validation des champs
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (!emailInput.value || !emailRegex.test(emailInput.value)) {
        showErrorModal('⚠️ Veuillez entrer une adresse e-mail valide');
        emailInput.focus();
        return;
    }
    
    if (!passwordInput.value || passwordInput.value.length < 6) {
        showErrorModal('⚠️ Le mot de passe doit contenir au moins 6 caractères');
        passwordInput.focus();
        return;
    }
    
    // Simulation d'une requête de connexion
    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.innerHTML;
    
    // Animation de chargement
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Connexion en cours...';
    submitBtn.disabled = true;
    
    // Simuler une requête API (remplacez par votre logique réelle)
    setTimeout(() => {
        // Ici, normalement, vous feriez une requête à votre backend
        // Pour cet exemple, on simule une connexion réussie
        
        // Simulation : vérifiez si c'est un utilisateur test
        if (emailInput.value === 'demo@example.com' && passwordInput.value === 'demo123') {
            showSuccessModal();
        } else {
            // Simulation d'une erreur d'authentification
            showErrorModal('❌ Identifiants incorrects. Veuillez vérifier votre email et mot de passe.');
        }
        
        // Réinitialiser le bouton
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }, 1500);
});

// Initialiser la validation au chargement de la page
emailInput.dispatchEvent(new Event('input'));
passwordInput.dispatchEvent(new Event('input'));