// ==========================================
// LunchPilot - Main JavaScript
// ==========================================

document.addEventListener("DOMContentLoaded", function () {

    console.log("LunchPilot JavaScript loaded successfully.");

    // ==========================================
    // Budget Progress Bar
    // ==========================================

    const budgetBars = document.querySelectorAll(
        ".progress-bar[data-budget-percentage]"
    );

    budgetBars.forEach(function (bar) {

        const percentage = parseFloat(
            bar.dataset.budgetPercentage
        ) || 0;

        const safePercentage = Math.min(
            Math.max(percentage, 0),
            100
        );

        bar.style.width = safePercentage + "%";

    });

    
    // ==========================================
    // Auto Hide Flash Messages Only
    // ==========================================

    const flashAlerts = document.querySelectorAll(
        "main > .container.mt-3 .alert.alert-dismissible"
    );

    flashAlerts.forEach(function (alert) {

        setTimeout(function () {

            const alertInstance =
                bootstrap.Alert.getOrCreateInstance(alert);

            alertInstance.close();

        }, 4000);

    });


    // ==========================================
    // Order Confirmation
    // ==========================================

    const orderButtons = document.querySelectorAll(".order-btn");

    orderButtons.forEach(function (button) {

        button.addEventListener("click", function (event) {

            const mealName = button.dataset.mealName;

            if (mealName) {

                const confirmed = confirm(
                    "Do you want to order " + mealName + "?"
                );

                if (!confirmed) {
                    event.preventDefault();
                }

            }

        });

    });


    // ==========================================
    // Password Confirmation
    // ==========================================

    const registerForm = document.querySelector("#registerForm");

    if (registerForm) {

        registerForm.addEventListener("submit", function (event) {

            const password = document.querySelector("#password");
            const confirmPassword = document.querySelector("#confirm_password");

            if (password && confirmPassword) {

                if (password.value !== confirmPassword.value) {

                    event.preventDefault();

                    alert("Passwords do not match!");

                    confirmPassword.focus();

                }

            }

        });

    }


    // ==========================================
    // Prevent Empty Forms
    // ==========================================

    const forms = document.querySelectorAll("form");

    forms.forEach(function (form) {

        form.addEventListener("submit", function (event) {

            const requiredInputs = form.querySelectorAll("[required]");

            let valid = true;

            requiredInputs.forEach(function (input) {

                if (input.value.trim() === "") {

                    valid = false;

                    input.classList.add("is-invalid");

                } else {

                    input.classList.remove("is-invalid");

                }

            });

            if (!valid) {

                event.preventDefault();

                alert("Please fill in all required fields.");

            }

        });

    });


    // ==========================================
    // Remove Invalid Style While Typing
    // ==========================================

    const inputs = document.querySelectorAll("input");

    inputs.forEach(function (input) {

        input.addEventListener("input", function () {

            if (input.value.trim() !== "") {

                input.classList.remove("is-invalid");

            }

        });

    });

});


// ===========================
// LunchPilot Confirmation Modal
// ===========================

let confirmActionUrl = "";

function openConfirmModal(
    title,
    message,
    actionUrl,
    buttonText,
    buttonType = "success"
) {

    confirmActionUrl = actionUrl;

    // Title
    document.getElementById("confirmModalTitle").textContent = title;

    // Message
    document.getElementById("confirmModalMessage").textContent = message;

    // Button
    const confirmButton =
        document.getElementById("confirmModalButton");

    confirmButton.textContent = buttonText;

    // Remove old button classes
    confirmButton.classList.remove(
        "btn-success",
        "btn-danger",
        "btn-warning"
    );

    // Add new button class
    if (buttonType === "danger") {

        confirmButton.classList.add("btn-danger");

    } else if (buttonType === "warning") {

        confirmButton.classList.add("btn-warning");

    } else {

        confirmButton.classList.add("btn-success");

    }

    // Icon
    const icon =
        document.getElementById("confirmIcon");

    if (buttonType === "danger") {

        icon.textContent = "⚠️";

    } else {

        icon.textContent = "✅";

    }

    // Open Bootstrap Modal
    const modalElement =
        document.getElementById("confirmModal");

    const modal =
        new bootstrap.Modal(modalElement);

    modal.show();
}


// Confirm button
document.addEventListener("DOMContentLoaded", function () {

    const confirmButton =
        document.getElementById("confirmModalButton");

    if (confirmButton) {

        confirmButton.addEventListener("click", function () {

            if (confirmActionUrl) {

                window.location.href =
                    confirmActionUrl;

            }

        });

    }

});