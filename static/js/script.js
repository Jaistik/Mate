/* =========================================================
   MATE — Hire a Professional
   Main JavaScript
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    /* =====================================================
       AUTO-HIDE FLASH MESSAGES
       ===================================================== */

    const alerts = document.querySelectorAll(
        ".mate-alert.alert"
    );

    alerts.forEach(function (alert) {

        setTimeout(function () {

            const bootstrapAlert =
                bootstrap.Alert.getOrCreateInstance(alert);

            bootstrapAlert.close();

        }, 5000);

    });


    /* =====================================================
       PASSWORD VISIBILITY TOGGLE
       ===================================================== */

    const passwordToggles =
        document.querySelectorAll(".password-toggle");

    passwordToggles.forEach(function (toggle) {

        toggle.addEventListener("click", function () {

            const targetId =
                toggle.getAttribute("data-target");

            const passwordInput =
                document.getElementById(targetId);

            if (!passwordInput) {
                return;
            }

            if (passwordInput.type === "password") {

                passwordInput.type = "text";

                toggle.innerHTML =
                    '<i class="bi bi-eye-slash"></i>';

            } else {

                passwordInput.type = "password";

                toggle.innerHTML =
                    '<i class="bi bi-eye"></i>';

            }

        });

    });


    /* =====================================================
       CONFIRMATION BUTTONS
       ===================================================== */

    const confirmButtons =
        document.querySelectorAll("[data-confirm]");

    confirmButtons.forEach(function (button) {

        button.addEventListener("click", function (event) {

            const message =
                button.getAttribute("data-confirm");

            if (!confirm(message)) {
                event.preventDefault();
            }

        });

    });


    /* =====================================================
       FILE INPUT — SHOW SELECTED FILE NAME
       ===================================================== */

    const fileInputs =
        document.querySelectorAll(".mate-file-input");

    fileInputs.forEach(function (input) {

        input.addEventListener("change", function () {

            const label =
                document.querySelector(
                    `[data-file-label="${input.id}"]`
                );

            if (!label) {
                return;
            }

            if (input.files.length > 0) {

                label.textContent =
                    input.files[0].name;

            } else {

                label.textContent =
                    "Choose a file";

            }

        });

    });


    /* =====================================================
       PROFILE IMAGE PREVIEW
       ===================================================== */

    const imageInputs =
        document.querySelectorAll(
            ".profile-image-input"
        );

    imageInputs.forEach(function (input) {

        input.addEventListener("change", function () {

            if (
                !input.files ||
                !input.files[0]
            ) {
                return;
            }

            const file =
                input.files[0];

            if (!file.type.startsWith("image/")) {

                alert(
                    "Please select a valid image file."
                );

                input.value = "";

                return;
            }

            const previewId =
                input.getAttribute(
                    "data-preview"
                );

            const preview =
                document.getElementById(previewId);

            if (!preview) {
                return;
            }

            const reader =
                new FileReader();

            reader.onload = function (event) {

                preview.src =
                    event.target.result;

            };

            reader.readAsDataURL(file);

        });

    });


    /* =====================================================
       CLIENT-SIDE IMAGE SIZE CHECK
       ===================================================== */

    const imageUploadInputs =
        document.querySelectorAll(
            'input[type="file"]'
        );

    imageUploadInputs.forEach(function (input) {

        input.addEventListener("change", function () {

            if (
                !input.files ||
                input.files.length === 0
            ) {
                return;
            }

            const file =
                input.files[0];

            const maxSize =
                5 * 1024 * 1024;

            if (file.size > maxSize) {

                alert(
                    "File size must be less than 5 MB."
                );

                input.value = "";

            }

        });

    });


    /* =====================================================
       SEARCH FILTER
       ===================================================== */

    const searchInputs =
        document.querySelectorAll(
            ".mate-live-search"
        );

    searchInputs.forEach(function (input) {

        input.addEventListener("input", function () {

            const searchValue =
                input.value.toLowerCase().trim();

            const targetSelector =
                input.getAttribute(
                    "data-search-target"
                );

            if (!targetSelector) {
                return;
            }

            const items =
                document.querySelectorAll(
                    targetSelector
                );

            items.forEach(function (item) {

                const text =
                    item.textContent.toLowerCase();

                if (text.includes(searchValue)) {

                    item.style.display = "";

                } else {

                    item.style.display = "none";

                }

            });

        });

    });


    /* =====================================================
       RAZORPAY PAYMENT
       ===================================================== */

    const razorpayButton =
        document.getElementById(
            "razorpay-pay-button"
        );

    if (
        razorpayButton &&
        typeof Razorpay !== "undefined"
    ) {

        razorpayButton.addEventListener(
            "click",
            function () {

                /* -----------------------------------------
                   PREVENT MULTIPLE CLICKS
                   ----------------------------------------- */

                if (razorpayButton.disabled) {
                    return;
                }


                /* -----------------------------------------
                   GET PAYMENT DATA FROM HTML
                   ----------------------------------------- */

                const keyId =
                    razorpayButton.getAttribute(
                        "data-key"
                    );

                const orderId =
                    razorpayButton.getAttribute(
                        "data-order-id"
                    );

                const amount =
                    razorpayButton.getAttribute(
                        "data-amount"
                    );

                const bookingId =
                    razorpayButton.getAttribute(
                        "data-booking-id"
                    );

                const verifyUrl =
                    razorpayButton.getAttribute(
                        "data-verify-url"
                    );


                /* -----------------------------------------
                   VALIDATE REQUIRED DATA
                   ----------------------------------------- */

                if (
                    !keyId ||
                    !orderId ||
                    !amount ||
                    !bookingId ||
                    !verifyUrl
                ) {

                    console.error(
                        "MATE: Required Razorpay payment data is missing."
                    );

                    alert(
                        "Unable to start payment. Please try again."
                    );

                    return;

                }


                /* -----------------------------------------
                   SAVE ORIGINAL BUTTON
                   ----------------------------------------- */

                const originalButtonHTML =
                    razorpayButton.innerHTML;


                /* -----------------------------------------
                   LOADING STATE
                   ----------------------------------------- */

                razorpayButton.disabled =
                    true;

                razorpayButton.innerHTML = `
                    <span
                        class="spinner-border spinner-border-sm me-2"
                        role="status"
                        aria-hidden="true"
                    ></span>
                    Opening Secure Payment...
                `;

                razorpayButton.classList.add(
                    "disabled"
                );


                /* -----------------------------------------
                   RAZORPAY CHECKOUT OPTIONS
                   ----------------------------------------- */

                const options = {

                    key: keyId,

                    amount: amount,

                    currency: "INR",

                    name: "MATE",

                    description:
                        "Professional Service",

                    order_id: orderId,


                    /* =====================================
                       PAYMENT SUCCESS
                       ===================================== */

                    handler: function (response) {

                        console.log(
                            "MATE: Razorpay payment successful."
                        );


                        console.log(
                            "Payment ID:",
                            response.razorpay_payment_id
                        );


                        console.log(
                            "Order ID:",
                            response.razorpay_order_id
                        );


                        console.log(
                            "Signature:",
                            response.razorpay_signature
                        );


                        /* ---------------------------------
                           VERIFICATION LOADING STATE
                           --------------------------------- */

                        razorpayButton.disabled =
                            true;

                        razorpayButton.innerHTML = `
                            <span
                                class="spinner-border spinner-border-sm me-2"
                                role="status"
                                aria-hidden="true"
                            ></span>
                            Verifying Payment...
                        `;


                        razorpayButton.classList.add(
                            "disabled"
                        );


                        /* ---------------------------------
                           CREATE VERIFICATION FORM
                           --------------------------------- */

                        const form =
                            document.createElement(
                                "form"
                            );

                        form.method = "POST";

                        form.action =
                            verifyUrl;


                        /* ---------------------------------
                           PAYMENT ID
                           --------------------------------- */

                        const paymentId =
                            document.createElement(
                                "input"
                            );

                        paymentId.type =
                            "hidden";

                        paymentId.name =
                            "razorpay_payment_id";

                        paymentId.value =
                            response.razorpay_payment_id;


                        /* ---------------------------------
                           ORDER ID
                           --------------------------------- */

                        const orderIdInput =
                            document.createElement(
                                "input"
                            );

                        orderIdInput.type =
                            "hidden";

                        orderIdInput.name =
                            "razorpay_order_id";

                        orderIdInput.value =
                            response.razorpay_order_id;


                        /* ---------------------------------
                           SIGNATURE
                           --------------------------------- */

                        const signature =
                            document.createElement(
                                "input"
                            );

                        signature.type =
                            "hidden";

                        signature.name =
                            "razorpay_signature";

                        signature.value =
                            response.razorpay_signature;


                        /* ---------------------------------
                           ADD FIELDS TO FORM
                           --------------------------------- */

                        form.appendChild(
                            paymentId
                        );

                        form.appendChild(
                            orderIdInput
                        );

                        form.appendChild(
                            signature
                        );


                        /* ---------------------------------
                           SUBMIT TO FLASK
                           --------------------------------- */

                        document.body.appendChild(
                            form
                        );

                        form.submit();

                    },


                    /* =====================================
                       PAYMENT WINDOW CLOSED
                       ===================================== */

                    modal: {

                        ondismiss: function () {

                            console.log(
                                "MATE: Razorpay payment window closed."
                            );


                            razorpayButton.disabled =
                                false;

                            razorpayButton.innerHTML =
                                originalButtonHTML;

                            razorpayButton.classList.remove(
                                "disabled"
                            );

                        }

                    },


                    /* =====================================
                       RAZORPAY THEME
                       ===================================== */

                    theme: {

                        color: "#8b0000"

                    }

                };


                /* -----------------------------------------
                   OPEN RAZORPAY
                   ----------------------------------------- */

                try {

                    const razorpay =
                        new Razorpay(
                            options
                        );

                    razorpay.open();

                } catch (error) {

                    console.error(
                        "MATE: Unable to open Razorpay.",
                        error
                    );


                    /* -------------------------------------
                       RESTORE BUTTON
                       ------------------------------------- */

                    razorpayButton.disabled =
                        false;

                    razorpayButton.innerHTML =
                        originalButtonHTML;

                    razorpayButton.classList.remove(
                        "disabled"
                    );


                    alert(
                        "Unable to open payment. Please try again."
                    );

                }

            }
        );

    } else if (razorpayButton) {

        /*
         * Razorpay checkout.js was not loaded.
         */

        console.error(
            "MATE: Razorpay Checkout is not loaded."
        );

    }


    /* =====================================================
       VOICE SEARCH
       ===================================================== */

    const voiceSearchButton =
        document.getElementById(
            "voiceSearchButton"
        );

    const professionalSearch =
        document.getElementById(
            "professionalSearch"
        );

    const voiceSearchIcon =
        document.getElementById(
            "voiceSearchIcon"
        );


    if (
        voiceSearchButton &&
        professionalSearch
    ) {

        const SpeechRecognition =
            window.SpeechRecognition ||
            window.webkitSpeechRecognition;

        if (SpeechRecognition) {

            const recognition =
                new SpeechRecognition();

            recognition.lang =
                "en-IN";

            recognition.continuous =
                false;

            recognition.interimResults =
                false;


            /* START */

            voiceSearchButton.addEventListener(
                "click",
                function () {

                    console.log(
                        "MATE: Voice search clicked."
                    );

                    try {

                        recognition.start();

                    } catch (error) {

                        console.log(
                            "MATE: Recognition already running."
                        );

                    }

                }
            );


            /* LISTENING */

            recognition.onstart =
                function () {

                    console.log(
                        "MATE: Listening..."
                    );

                    if (voiceSearchIcon) {

                        voiceSearchIcon.className =
                            "bi bi-mic-fill";

                    }

                    voiceSearchButton.classList.add(
                        "active"
                    );

                };


            /* RESULT */

            recognition.onresult =
                function (event) {

                    const text =
                        event.results[0][0]
                            .transcript;

                    console.log(
                        "MATE Voice:",
                        text
                    );

                    professionalSearch.value =
                        text;


                    /*
                     * Trigger the existing
                     * live-search system.
                     */

                    professionalSearch.dispatchEvent(
                        new Event(
                            "input",
                            {
                                bubbles: true
                            }
                        )
                    );

                };


            /* STOP */

            recognition.onend =
                function () {

                    console.log(
                        "MATE: Listening stopped."
                    );

                    if (voiceSearchIcon) {

                        voiceSearchIcon.className =
                            "bi bi-mic";

                    }

                    voiceSearchButton.classList.remove(
                        "active"
                    );

                };


            /* ERROR */

            recognition.onerror =
                function (event) {

                    console.error(
                        "MATE Voice Search Error:",
                        event.error
                    );

                    if (voiceSearchIcon) {

                        voiceSearchIcon.className =
                            "bi bi-mic";

                    }

                    voiceSearchButton.classList.remove(
                        "active"
                    );

                };

        } else {

            console.log(
                "MATE: Speech recognition is not supported."
            );

            voiceSearchButton.disabled =
                true;

        }

    }


    /* =====================================================
       MOBILE NAVBAR AUTO CLOSE
       ===================================================== */

    const navbar =
        document.getElementById(
            "mateNavbar"
        );

    if (navbar) {

        const navLinks =
            navbar.querySelectorAll(
                ".nav-link"
            );

        const navbarCollapse =
            bootstrap.Collapse.getOrCreateInstance(
                navbar,
                {
                    toggle: false
                }
            );

        navLinks.forEach(function (link) {

            link.addEventListener(
                "click",
                function () {

                    if (
                        window.innerWidth < 992 &&
                        navbar.classList.contains(
                            "show"
                        )
                    ) {

                        navbarCollapse.hide();

                    }

                }
            );

        });

    }


    /* =====================================================
       SMOOTH SCROLL
       ===================================================== */

    const smoothLinks =
        document.querySelectorAll(
            'a[href^="#"]'
        );

    smoothLinks.forEach(function (link) {

        link.addEventListener(
            "click",
            function (event) {

                const targetId =
                    link.getAttribute(
                        "href"
                    );

                if (
                    !targetId ||
                    targetId === "#"
                ) {
                    return;
                }

                const target =
                    document.querySelector(
                        targetId
                    );

                if (!target) {
                    return;
                }

                event.preventDefault();

                target.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });

            }
        );

    });


    /* =====================================================
       CURRENT YEAR
       ===================================================== */

    const yearElements =
        document.querySelectorAll(
            ".current-year"
        );

    yearElements.forEach(function (element) {

        element.textContent =
            new Date().getFullYear();

    });


    /* =====================================================
       BUTTON LOADING STATE
       ===================================================== */

    const loadingForms =
        document.querySelectorAll(
            "form[data-loading]"
        );

    loadingForms.forEach(function (form) {

        form.addEventListener(
            "submit",
            function () {

                const submitButton =
                    form.querySelector(
                        'button[type="submit"], input[type="submit"]'
                    );

                if (!submitButton) {
                    return;
                }

                submitButton.disabled =
                    true;

                const originalText =
                    submitButton.innerHTML;

                submitButton.innerHTML =
                    `
                    <span
                        class="spinner-border spinner-border-sm me-2"
                        aria-hidden="true"
                    ></span>
                    Processing...
                    `;

                submitButton.setAttribute(
                    "data-original-text",
                    originalText
                );

            }
        );

    });


    /* =====================================================
       BOOTSTRAP TOOLTIP INITIALIZATION
       ===================================================== */

    const tooltipElements =
        document.querySelectorAll(
            '[data-bs-toggle="tooltip"]'
        );

    tooltipElements.forEach(function (element) {

        new bootstrap.Tooltip(
            element
        );

    });


    /* =====================================================
       BOOTSTRAP POPOVER INITIALIZATION
       ===================================================== */

    const popoverElements =
        document.querySelectorAll(
            '[data-bs-toggle="popover"]'
        );

    popoverElements.forEach(function (element) {

        new bootstrap.Popover(
            element
        );

    });


    /* =====================================================
       CONSOLE MESSAGE
       ===================================================== */

    console.log(
        "MATE — Hire a Professional | Frontend loaded."
    );

});

