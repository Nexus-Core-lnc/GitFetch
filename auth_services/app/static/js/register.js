        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirmPassword');
        const emailInput = document.getElementById('email');
        const form = document.getElementById('registerForm');
        const passwordCriteria = document.getElementById('passwordCriteria');
        const matchIndicator = document.getElementById('matchIndicator');

        // Critères du mot de passe
        const criteria = {
            length: { regex: /.{8,}/, element: document.getElementById('length') },
            uppercase: { regex: /[A-Z]/, element: document.getElementById('uppercase') },
            lowercase: { regex: /[a-z]/, element: document.getElementById('lowercase') },
            number: { regex: /[0-9]/, element: document.getElementById('number') },
            special: { regex: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]/, element: document.getElementById('special') }
        };

        // Afficher les critères lors du focus
        passwordInput.addEventListener('focus', function() {
            passwordCriteria.classList.add('show');
        });

        passwordInput.addEventListener('blur', function() {
            if (this.value.length === 0) {
                passwordCriteria.classList.remove('show');
            }
        });

        // Vérifier les critères en temps réel
        passwordInput.addEventListener('input', function() {
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
                passwordInput.classList.add('valid');
                passwordInput.classList.remove('invalid');
            } else if (password.length > 0) {
                passwordInput.classList.add('invalid');
                passwordInput.classList.remove('valid');
            } else {
                passwordInput.classList.remove('valid', 'invalid');
                passwordCriteria.classList.remove('show');
            }

            checkPasswordMatch();
        });

        confirmPasswordInput.addEventListener('input', checkPasswordMatch);

        function checkPasswordMatch() {
            if (confirmPasswordInput.value.length > 0) {
                if (passwordInput.value === confirmPasswordInput.value) {
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

        emailInput.addEventListener('input', function() {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            
            if (this.value && emailRegex.test(this.value)) {
                this.classList.add('valid');
                this.classList.remove('invalid');
            } else if (this.value) {
                this.classList.add('invalid');
                this.classList.remove('valid');
            } else {
                this.classList.remove('valid', 'invalid');
            }
        });

        function togglePassword(inputId) {
            const input = document.getElementById(inputId);
            const toggleBtn = inputId === 'password' 
                ? document.getElementById('togglePassword1') 
                : document.getElementById('togglePassword2');
            
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

        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            let isValid = true;
            for (let key in criteria) {
                if (!criteria[key].regex.test(passwordInput.value)) {
                    isValid = false;
                    break;
                }
            }

            if (!isValid) {
                alert('⚠️ Veuillez respecter tous les critères du mot de passe');
                return;
            }

            if (passwordInput.value !== confirmPasswordInput.value) {
                alert('⚠️ Les mots de passe ne correspondent pas');
                return;
            }

            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(emailInput.value)) {
                alert('⚠️ Veuillez entrer une adresse e-mail valide');
                return;
            }

            alert('✓ Inscription réussie ! Vous pouvez maintenant exporter vos informations.');
        });

        function exportCredentials() {
            const email = emailInput.value;
            const password = passwordInput.value;
            const confirmPassword = confirmPasswordInput.value;

            if (!email || !password || !confirmPassword) {
                alert('⚠️ Veuillez remplir tous les champs avant d\'exporter');
                return;
            }

            let isValid = true;
            for (let key in criteria) {
                if (!criteria[key].regex.test(password)) {
                    isValid = false;
                    break;
                }
            }

            if (!isValid) {
                alert('⚠️ Veuillez créer un mot de passe valide avant d\'exporter');
                return;
            }

            if (password !== confirmPassword) {
                alert('⚠️ Les mots de passe doivent correspondre avant d\'exporter');
                return;
            }

            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                alert('⚠️ Veuillez entrer une adresse e-mail valide');
                return;
            }

            const currentDate = new Date().toLocaleString('fr-FR');
            const txtContent = `========================================
    INFORMATIONS D'INSCRIPTION
========================================

Date de création : ${currentDate}

----------------------------------------
IDENTIFIANTS
----------------------------------------
Adresse e-mail : ${email}
Mot de passe   : ${password}

----------------------------------------
CRITÈRES DU MOT DE PASSE
----------------------------------------
✓ Au moins 8 caractères
✓ Au moins 1 majuscule
✓ Au moins 1 minuscule
✓ Au moins 1 chiffre
✓ Au moins 1 caractère spécial

----------------------------------------
STATUT
----------------------------------------
✓ Tous les critères respectés
✓ Mots de passe correspondants
✓ E-mail valide

========================================
⚠️  AVERTISSEMENT DE SÉCURITÉ
========================================
Ce fichier contient vos informations
sensibles. Conservez-le dans un endroit
sûr et ne le partagez avec personne.

========================================
`;

            const blob = new Blob([txtContent], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            const timestamp = new Date().getTime();
            link.href = url;
            link.download = `identifiants_${timestamp}.txt`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            const successMessage = document.getElementById('successMessage');
            successMessage.classList.add('show');
            setTimeout(() => {
                successMessage.classList.remove('show');
            }, 4000);
        }