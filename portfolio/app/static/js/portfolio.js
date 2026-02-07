// Animation pour les cartes techniques et projets
document.addEventListener("DOMContentLoaded", function () {
  // Animation des cartes techniques et projets
  const observerOptions = {
    threshold: 0.2,
    rootMargin: "0px 0px -50px 0px",
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("animated");

        // Si c'est une carte technique, animer la barre de progression et le compteur
        if (entry.target.classList.contains("tech-card")) {
          const progressFill = entry.target.querySelector(".progress-fill");
          const percentageElement =
            entry.target.querySelector(".tech-percentage");
          const targetWidth = progressFill.getAttribute("data-width");
          const targetPercentage =
            percentageElement.getAttribute("data-target");

          // Animer la barre de progression
          setTimeout(() => {
            progressFill.style.width = targetWidth + "%";
          }, 300);

          // Animer le compteur
          animateCounter(percentageElement, 0, targetPercentage, 2000);
        }
      }
    });
  }, observerOptions);

  // Observer les cartes techniques et projets
  document.querySelectorAll(".tech-card, .project-card").forEach((card) => {
    observer.observe(card);
  });

  // Fonction pour animer les compteurs
  function animateCounter(element, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      const currentValue = Math.floor(progress * (end - start) + start);
      element.textContent = currentValue + "%";
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };
    window.requestAnimationFrame(step);
  }

  // Animation des boutons au survol
  const buttons = document.querySelectorAll(".btn");
  buttons.forEach((button) => {
    button.addEventListener("mouseenter", function () {
      this.style.transform = "translateY(-3px)";
    });

    button.addEventListener("mouseleave", function () {
      this.style.transform = "translateY(0)";
    });
  });

  // Animation des cartes de compétences
  const skillItems = document.querySelectorAll(".skill-item");
  skillItems.forEach((item, index) => {
    item.style.animationDelay = `${index * 0.1}s`;
  });
});
 