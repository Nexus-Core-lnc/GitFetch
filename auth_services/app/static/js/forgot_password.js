const emailInput = document.getElementById('email');
const form = document.getElementById('forgotPasswordForm');
const emailFeedback = document.getElementById('emailFeedback');
const successModal = document.getElementById('successModal');
const successMessage = document.getElementById('successMessage');

// Fonctions pour les modales
function showSuccessModal(message) {
    successMessage.textContent = message;
    successModal.style.display = 'flex';
}

function closeSuccessModal() {
    successModal.style.display = 'none';
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

// Soumission du formulaire
form.addEventListener('submit', function(e) {
    
    // Validation de l'email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (!emailInput.value || !emailRegex.test(emailInput.value)) {
        emailInput.classList.add('invalid');
        emailInput.focus();
        return;
    }
    
    // Simulation d'envoi d'email
    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.innerHTML;
    
    // Animation de chargement
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Envoi en cours...';
    submitBtn.disabled = true;
    
    // Simuler un délai d'envoi
    setTimeout(() => {
        // Réinitialiser le bouton
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
        
        // Afficher le message de succès
        showSuccessModal(`✓ Instructions de réinitialisation envoyées à ${emailInput.value}`);
        
        // Réinitialiser le formulaire après 3 secondes
        setTimeout(() => {
            form.reset();
            emailInput.classList.remove('valid');
            emailFeedback.textContent = '';
            emailFeedback.className = 'input-feedback';
        }, 3000);
        
    }, 2000);
});

// Initialiser la validation au chargement de la page
emailInput.dispatchEvent(new Event('input'));