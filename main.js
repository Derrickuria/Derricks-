// Button pulse on load
window.addEventListener("load", () => {
    const btn = document.querySelector(".hero button");
    btn.animate(
        [
            { transform: "scale(1)", boxShadow: "0 12px 30px rgba(245,197,66,0.3)" },
            { transform: "scale(1.05)", boxShadow: "0 20px 40px rgba(245,197,66,0.5)" },
            { transform: "scale(1)" }
        ],
        {
            duration: 1400,
            iterations: 1
        }
    );
});

// Smooth scroll placeholder
document.querySelector(".hero button").addEventListener("click", () => {
    alert("🎲 Games catalogue coming next!");
});


const cartItems = [];
const cartList = document.getElementById("cart-items");
const totalPriceEl = document.getElementById("total-price");

document.querySelectorAll(".add-cart").forEach(button => {
    button.addEventListener("click", (e) => {
        const card = e.target.closest(".game-card");
        const name = card.dataset.name;
        const price = parseInt(card.dataset.price);

        // Add item to cart
        cartItems.push({ name, price });
        updateCart();
    });
});

function updateCart() {
    // Clear existing
    cartList.innerHTML = "";

    let total = 0;
    cartItems.forEach(item => {
        const li = document.createElement("li");
        li.textContent = `${item.name} - Ksh ${item.price}`;
        cartList.appendChild(li);
        total += item.price;
    });

    totalPriceEl.textContent = `Total: Ksh ${total}`;
}

// Cart actions
document.getElementById("continue-browsing").addEventListener("click", () => {
    alert("Keep browsing more games!");
});

document.getElementById("proceed-checkout").addEventListener("click", () => {
    alert(`Proceeding to checkout. Total: Ksh ${cartItems.reduce((a,b)=>a+b.price,0)}`);
});
