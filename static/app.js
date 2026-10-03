document.addEventListener("DOMContentLoaded", () => {

    const cards = document.querySelectorAll(
        ".product-card"
    );

    cards.forEach((card, index) => {

        card.style.opacity = "0";
        card.style.transform = "translateY(25px)";

        setTimeout(() => {

            card.style.transition =
                "all .6s ease";

            card.style.opacity = "1";
            card.style.transform =
                "translateY(0)";

        }, index * 120);

    });

});
