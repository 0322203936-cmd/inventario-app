// home.ts - Script para animaciones y efectos premium en el menú principal

document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll<HTMLElement>('.premium-card');

    cards.forEach((card) => {
        // Al mover el ratón sobre la tarjeta, creamos un efecto de brillo
        card.addEventListener('mousemove', (e: MouseEvent) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });

        // Al salir, reiniciamos variables
        card.addEventListener('mouseleave', () => {
            card.style.setProperty('--mouse-x', `-100px`);
            card.style.setProperty('--mouse-y', `-100px`);
        });
    });

    // Animación de entrada escalonada
    setTimeout(() => {
        cards.forEach((card, index) => {
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0) scale(1)';
            }, index * 100); // 100ms delay per card
        });
    }, 100);
});
