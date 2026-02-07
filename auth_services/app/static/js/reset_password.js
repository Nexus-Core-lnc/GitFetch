const codeInput = document.getElementById('code');
const newPasswordInput = document.getElementById('newPassword');
const confirmPasswordInput = document.getElementById('confirmPassword');
const form = document.getElementById('resetPasswordForm');
const codeFeedback = document.getElementById('codeFeedback');
const passwordCriteria = document.getElementById('passwordCriteria');
const matchIndicator = document.getElementById('matchIndicator');
const successModal = document.getElementById('successModal');
const resendButton = document.querySelector('.resend-code');

// Critères du mot de passe
const criteria = {
    length: { regex: /.{8,}/, element: document.getElementById('length') },
    uppercase: { regex: /[A-Z]/, element: document.getElementById('uppercase') },
    lowercase: { regex: /[a-z]/, element: document.getElementById('lowercase') },
    number: { regex: /[0-9]/, element: document.getElementById('number') },
    special: { regex: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]/, element: document.getElementById('special') }
};

// Timer pour le renvoi du code
let resendTimer = 60;
let canResend = false;

// Fonctions pour les modales
function showSuccessModal() {
    successModal.style.display = 'flex';
}

function closeSuccessModal() {
    successModal.style.display = 'none';
}

function redirectToLogin() {
    window.location.href = '/login';
}

// Fermer la modale en cliquant à l'extérieur
window.addEventListener('click', function(event) {
    if (event.target === successModal) {
        closeSuccessModal();
    }
});

// Fermer la modale avec la touche Échap
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeSuccessModal();
    }
});

// Validation du code en temps réel
codeInput.addEventListener('input', function() {
    const value = this.value.trim();
    
    if (!value) {
        this.classList.remove('valid', 'invalid');
        codeFeedback.textContent = '';
        codeFeedback.className = 'input-feedback';
        return;
    }
    
    // Code doit être 6 chiffres
    if (/^\d{6}$/.test(value)) {
        this.classList.add('valid');
        this.classList.remove('invalid');
        codeFeedback.textContent = '✓ Format de code valide';
        codeFeedback.className = 'input-feedback success';
    } else {
        this.classList.add('invalid');
        this.classList.remove('valid');
        codeFeedback.textContent = '✗ Le code doit contenir 6 chiffres';
        codeFeedback.className = 'input-feedback error';
    }
});

// Afficher les critères lors du focus
newPasswordInput.addEventListener('focus', function() {
    passwordCriteria.classList.add('show');
});

newPasswordInput.addEventListener('blur', function() {
    if (this.value.length === 0) {
        passwordCriteria.classList.remove('show');
    }
});

// Vérifier les critères en temps réel
newPasswordInput.addEventListener('input', function() {
    const password = this.value;
    
    if (password.length > 0) {
        passwordCriteria.classList.add('show');
    }
    
    let allMet = true;

    for (let key in criteria) {
        const criterion = criteria[key];
        const icon = criterion.element.querySelector('i');
        
        if (criterion.regex.test(password)) {
            criterion.element.classList.add('met');
            icon.classList.remove('fa-times');
            icon.classList.add('fa-check');
        } else {
            criterion.element.classList.remove('met');
            icon.classList.remove('fa-check');
            icon.classList.add('fa-times');
            allMet = false;
        }
    }

    if (allMet && password.length > 0) {
        newPasswordInput.classList.add('valid');
        newPasswordInput.classList.remove('invalid');
    } else if (password.length > 0) {
        newPasswordInput.classList.add('invalid');
        newPasswordInput.classList.remove('valid');
    } else {
        newPasswordInput.classList.remove('valid', 'invalid');
        passwordCriteria.classList.remove('show');
    }

    checkPasswordMatch();
});

confirmPasswordInput.addEventListener('input', checkPasswordMatch);

function checkPasswordMatch() {
    if (confirmPasswordInput.value.length > 0) {
        if (newPasswordInput.value === confirmPasswordInput.value) {
            confirmPasswordInput.classList.add('valid');
            confirmPasswordInput.classList.remove('invalid');
            matchIndicator.innerHTML = '<i class="fas fa-check-circle"></i> Les mots de passe correspondent';
            matchIndicator.classList.add('match');
            matchIndicator.classList.remove('no-match');
            matchIndicator.classList.add('show');
        } else {
            confirmPasswordInput.classList.add('invalid');
            confirmPasswordInput.classList.remove('valid');
            matchIndicator.innerHTML = '<i class="fas fa-times-circle"></i> Les mots de passe ne correspondent pas';
            matchIndicator.classList.add('no-match');
            matchIndicator.classList.remove('match');
            matchIndicator.classList.add('show');
        }
    } else {
        confirmPasswordInput.classList.remove('valid', 'invalid');
        matchIndicator.classList.remove('show');
    }
}

function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const toggleBtn = input.nextElementSibling;
    
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

// Fonction pour renvoyer le code
function resendCode() {
    if (!canResend) return;
    
    // Désactiver le bouton
    canResend = false;
    resendButton.disabled = true;
    resendTimer = 60;
    
    // Mettre à jour le texte du bouton
    updateResendButton();
    
    // Simuler l'envoi du code
    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.innerHTML;
    
    // Animation de chargement
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Renvoi en cours...';
    
    setTimeout(() => {
        // Réinitialiser le bouton principal
        submitBtn.innerHTML = originalText;
        
        // Démarrer le compte à rebours
        const countdown = setInterval(() => {
            resendTimer--;
            updateResendButton();
            
            if (resendTimer <= 0) {
                clearInterval(countdown);
                canResend = true;
                resendButton.disabled = false;
                resendButton.innerHTML = '<i class="fas fa-redo"></i> Renvoyer';
            }
        }, 1000);
        
    }, 1500);
}

function updateResendButton() {
    resendButton.innerHTML = `<i class="fas fa-clock"></i> ${resendTimer}s`;
}

// Soumission du formulaire
form.addEventListener('submit', function(e) {
    
    // Validation du code
    if (!/^\d{6}$/.test(codeInput.value.trim())) {
        codeInput.classList.add('invalid');
        codeInput.focus();
        return;
    }
    
    // Validation des critères du mot de passe
    let isValid = true;
    for (let key in criteria) {
        if (!criteria[key].regex.test(newPasswordInput.value)) {
            isValid = false;
            break;
        }
    }

    if (!isValid) {
        alert('⚠️ Veuillez respecter tous les critères du mot de passe');
        newPasswordInput.focus();
        return;
    }

    if (newPasswordInput.value !== confirmPasswordInput.value) {
        alert('⚠️ Les mots de passe ne correspondent pas');
        confirmPasswordInput.focus();
        return;
    }

    // Simulation de réinitialisation
    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.innerHTML;
    
    // Animation de chargement
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Réinitialisation en cours...';
    submitBtn.disabled = true;
    
    // Simuler un délai de traitement
    setTimeout(() => {
        // Afficher le message de succès
        showSuccessModal();
        
        // Réinitialiser le bouton
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
        
        // Rediriger vers la page de connexion après 3 secondes
        setTimeout(() => {
            window.location.href = '/login';
        }, 3000);
        
    }, 2000);
});

// Initialiser le bouton de renvoi
updateResendButton();
resendButton.disabled = true;

// Initialiser les validations
codeInput.dispatchEvent(new Event('input'));
newPasswordInput.dispatchEvent(new Event('input'));

// Activer le bouton de renvoi après 60 secondes
setTimeout(() => {
    canResend = true;
    resendButton.disabled = false;
    resendButton.innerHTML = '<i class="fas fa-redo"></i> Renvoyer';
}, 60000);