
document.addEventListener("DOMContentLoaded", function () {
    const hero = document.querySelector(".hero-slideshow");

    if (!hero) {
        console.error("Không tìm thấy .hero-slideshow");
        return;
    }

    const slides = hero.querySelectorAll(".hero-slide");
    const dots = hero.querySelectorAll(".hero-dot");
    const prev = hero.querySelector(".hero-prev");
    const next = hero.querySelector(".hero-next");

    if (slides.length === 0 || dots.length !== slides.length || !prev || !next) {
        console.error("Tên class của slideshow không khớp");
        return;
    }

    let current = 0;
    let timer;

    function showSlide(index) {
        current = (index + slides.length) % slides.length;

        slides.forEach((slide, i) => {
            slide.classList.toggle("active", i === current);
        });

        dots.forEach((dot, i) => {
            dot.classList.toggle("active", i === current);
        });
    }

    function startAutoPlay() {
        clearInterval(timer);
        timer = setInterval(() => {
            showSlide(current + 1);
        }, 5000);
    }

    prev.addEventListener("click", function () {
        showSlide(current - 1);
        startAutoPlay();
    });

    next.addEventListener("click", function () {
        showSlide(current + 1);
        startAutoPlay();
    });

    dots.forEach((dot, i) => {
        dot.addEventListener("click", function () {
            showSlide(i);
            startAutoPlay();
        });
    });

    showSlide(0);
    startAutoPlay();
});
