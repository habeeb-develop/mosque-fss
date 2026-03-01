document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("get-involved");
    const nameInput = document.getElementById("contact-name");
    const emailInput = document.getElementById("contact-email");
    const messageInput = document.getElementById("contact-message");

    // Create message display
    const messageBox = document.createElement("p");
    messageBox.style.marginTop = "15px";
    messageBox.style.fontWeight = "bold";
    form.appendChild(messageBox);

    // Form Submission
    form.addEventListener("submit", function (e) {
        e.preventDefault();

        const name = nameInput.value.trim();
        const email = emailInput.value.trim();
        const message = messageInput.value.trim();

        if (name === "" || email === "" || message === "") {
            messageBox.style.color = "red";
            messageBox.textContent = "Please fill in all fields.";
            return;
        }

        if (!validateEmail(email)) {
            messageBox.style.color = "red";
            messageBox.textContent = "Please enter a valid email address.";
            return;
        }

        // Success
        messageBox.style.color = "green";
        messageBox.textContent = "Thank you! Your message has been sent successfully.";

        form.reset();
    });

    // Email validation
    function validateEmail(email) {
        const pattern = /^[^ ]+@[^ ]+\.[a-z]{2,3}$/;
        return pattern.test(email.toLowerCase());
    }

    // Box Click Effects
    const boxes = document.querySelectorAll(".box");

    boxes.forEach(box => {
        box.style.cursor = "pointer";

        box.addEventListener("click", function () {

            boxes.forEach(b => b.style.border = "none");

            this.style.border = "3px solid #0f5132";

            alert("You selected: " + this.querySelector("h3").innerText);
        });
    });

});