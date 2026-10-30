/* =========================================================
   Newton's Rings AI Lab Mentor — Frontend Chat Logic
   Handles: chat messaging, typing animation, auto-scroll,
   sidebar topic buttons, viva mode UI, calculator modal.
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    // ---------------- DOM References ----------------
    const chatWindow = document.getElementById("chatWindow");
    const userInput = document.getElementById("userInput");
    const sendBtn = document.getElementById("sendBtn");
    const suggestionsRow = document.getElementById("suggestionsRow");
    const sidebar = document.getElementById("sidebar");
    const hamburgerBtn = document.getElementById("hamburgerBtn");
    const vivaBtn = document.getElementById("vivaBtn");
    const calcBtn = document.getElementById("calcBtn");
    const endVivaBtn = document.getElementById("endVivaBtn");
    const statusLine = document.getElementById("statusLine");

    const calcModal = document.getElementById("calcModal");
    const closeCalcModal = document.getElementById("closeCalcModal");
    const calcSubmitBtn = document.getElementById("calcSubmitBtn");
    const calcResult = document.getElementById("calcResult");

    const navButtons = document.querySelectorAll(".nav-btn[data-topic]");

    let vivaModeActive = false;

    // ---------------- Initial Greeting ----------------
    addBotMessage(
        "Hi there! 👋 I'm your Newton's Rings AI Lab Mentor.\n\n" +
        "I can explain the theory, apparatus, procedure, formulae, calculations, " +
        "graph plotting, precautions, and sources of error for this experiment. " +
        "I can also run an interactive viva session, or help you calculate the " +
        "wavelength from your own observation data.\n\n" +
        "What would you like to start with?"
    );
    renderSuggestions(["Explain the theory", "Explain the procedure", "Start Viva Mode", "Open Calculator"]);

    // ---------------- Send message on Enter / button click ----------------
    sendBtn.addEventListener("click", sendMessage);
    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            sendMessage();
        }
    });

    function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        addUserMessage(text);
        userInput.value = "";
        clearSuggestions();

        const typingEl = showTypingIndicator();

        fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text })
        })
        .then(res => res.json())
        .then(data => {
            removeTypingIndicator(typingEl);
            addBotMessage(data.reply);
            renderSuggestions(data.suggestions || []);
            if (data.viva_ended) {
                setVivaMode(false);
            }
        })
        .catch(() => {
            removeTypingIndicator(typingEl);
            addBotMessage("⚠️ I'm having trouble reaching the server. Please make sure app.py is running.");
        });
    }

    // ---------------- Sidebar topic buttons ----------------
    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const topic = btn.getAttribute("data-topic");

            navButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            addUserMessage(btn.textContent.trim());
            clearSuggestions();
            const typingEl = showTypingIndicator();

            fetch(`/api/topic/${topic}`)
                .then(res => res.json())
                .then(data => {
                    removeTypingIndicator(typingEl);
                    addBotMessage(data.reply);
                    renderSuggestions(data.suggestions || []);
                })
                .catch(() => {
                    removeTypingIndicator(typingEl);
                    addBotMessage("⚠️ Couldn't load that topic. Please check the server is running.");
                });

            closeSidebarOnMobile();
        });
    });

    // ---------------- Viva Mode ----------------
    vivaBtn.addEventListener("click", () => {
        addUserMessage("Start Viva Mode");
        clearSuggestions();
        const typingEl = showTypingIndicator();

        fetch("/api/viva/start", { method: "POST" })
            .then(res => res.json())
            .then(data => {
                removeTypingIndicator(typingEl);
                addBotMessage(data.reply);
                renderSuggestions(data.suggestions || []);
                setVivaMode(true);
            });

        closeSidebarOnMobile();
    });

    endVivaBtn.addEventListener("click", () => {
        const typingEl = showTypingIndicator();
        fetch("/api/viva/end", { method: "POST" })
            .then(res => res.json())
            .then(data => {
                removeTypingIndicator(typingEl);
                addBotMessage(data.reply);
                renderSuggestions(data.suggestions || []);
                setVivaMode(false);
            });
    });

    function setVivaMode(active) {
        vivaModeActive = active;
        if (active) {
            endVivaBtn.classList.remove("hidden");
            statusLine.innerHTML = '<span class="status-dot"></span> Viva Mode active';
        } else {
            endVivaBtn.classList.add("hidden");
            statusLine.innerHTML = '<span class="status-dot"></span> Online · Ready to help';
        }
    }

    // ---------------- Calculator Modal ----------------
    calcBtn.addEventListener("click", () => {
        calcModal.classList.remove("hidden");
        closeSidebarOnMobile();
    });

    closeCalcModal.addEventListener("click", () => {
        calcModal.classList.add("hidden");
        calcResult.classList.add("hidden");
    });

    calcModal.addEventListener("click", (e) => {
        if (e.target === calcModal) {
            calcModal.classList.add("hidden");
        }
    });

    calcSubmitBtn.addEventListener("click", () => {
        const d_np_m = document.getElementById("calc_d_np_m").value;
        const d_n = document.getElementById("calc_d_n").value;
        const m = document.getElementById("calc_m").value;
        const R = document.getElementById("calc_R").value;

        if (!d_np_m || !d_n || !m || !R) {
            calcResult.classList.remove("hidden");
            calcResult.innerHTML = `<span class="warning-line">⚠️ Please fill in all four fields.</span>`;
            return;
        }

        fetch("/api/calculate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                d_n_plus_m: parseFloat(d_np_m),
                d_n: parseFloat(d_n),
                m: parseFloat(m),
                R: parseFloat(R)
            })
        })
        .then(res => res.json())
        .then(data => {
            calcResult.classList.remove("hidden");
            if (data.error) {
                calcResult.innerHTML = `<span class="warning-line">⚠️ ${data.error}</span>`;
                return;
            }
            let html = `
                <div class="result-line">D²(n+m) − D²(n) = <strong>${data.diff_d_squared} cm²</strong></div>
                <div class="result-line">Wavelength (λ) = <strong>${data.wavelength_angstrom} Å</strong></div>
                <div class="result-line">Standard value = <strong>${data.standard_value_angstrom} Å</strong></div>
                <div class="result-line">Percentage error = <strong>${data.percent_error}%</strong></div>
            `;
            if (data.warning) {
                html += `<span class="warning-line">⚠️ ${data.warning}</span>`;
            }
            calcResult.innerHTML = html;
        })
        .catch(() => {
            calcResult.classList.remove("hidden");
            calcResult.innerHTML = `<span class="warning-line">⚠️ Server error. Please check app.py is running.</span>`;
        });
    });

    // ---------------- Hamburger (mobile sidebar) ----------------
    hamburgerBtn.addEventListener("click", () => {
        sidebar.classList.toggle("open");
    });

    function closeSidebarOnMobile() {
        if (window.innerWidth <= 860) {
            sidebar.classList.remove("open");
        }
    }

    // ---------------- Message rendering helpers ----------------
    function addUserMessage(text) {
        const row = document.createElement("div");
        row.className = "msg-row user";
        row.innerHTML = `
            <div class="avatar">🧑‍🎓</div>
            <div class="bubble"></div>
        `;
        row.querySelector(".bubble").textContent = text;
        chatWindow.appendChild(row);
        scrollToBottom();
    }

    function addBotMessage(text) {
        const row = document.createElement("div");
        row.className = "msg-row bot";
        row.innerHTML = `
            <div class="avatar">🔬</div>
            <div class="bubble"></div>
        `;
        row.querySelector(".bubble").textContent = text;
        chatWindow.appendChild(row);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const row = document.createElement("div");
        row.className = "msg-row bot";
        row.innerHTML = `
            <div class="avatar">🔬</div>
            <div class="bubble">
                <div class="typing-dots"><span></span><span></span><span></span></div>
            </div>
        `;
        chatWindow.appendChild(row);
        scrollToBottom();
        return row;
    }

    function removeTypingIndicator(el) {
        if (el && el.parentNode) {
            el.parentNode.removeChild(el);
        }
    }

    function renderSuggestions(list) {
        clearSuggestions();
        list.forEach(text => {
            const chip = document.createElement("button");
            chip.className = "suggestion-chip";
            chip.textContent = text;
            chip.addEventListener("click", () => {
                userInput.value = text;
                sendMessage();
            });
            suggestionsRow.appendChild(chip);
        });
    }

    function clearSuggestions() {
        suggestionsRow.innerHTML = "";
    }

    function scrollToBottom() {
        setTimeout(() => {
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }, 50);
    }
});