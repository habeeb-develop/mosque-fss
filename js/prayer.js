// ======== ELEMENTS ========
const loadBtn = document.getElementById("load-prayer-btn");
const nextName = document.getElementById("next-prayer-name");
const nextCountdown = document.getElementById("next-prayer-countdown");
const adhan = document.getElementById("adhan-audio");

let prayerTimes = {};
let interval;

// ======== FETCH PRAYER TIMES ========
async function fetchPrayerTimes() {
    try {
        const res = await fetch("https://api.aladhan.com/v1/timingsByCity?city=Lagos&country=Nigeria&method=2");
        const data = await res.json();
        const t = data.data.timings;

        // Store needed prayers
        prayerTimes = {
            Fajr: t.Fajr,
            Zuhr: t.Dhuhr,
            Asr: t.Asr,
            Maghrib: t.Maghrib,
            Isha: t.Isha
        };

        displayTimes();

        clearInterval(interval);
        updateCountdown();
        interval = setInterval(updateCountdown, 1000);

    } catch {
        alert("Failed to load prayer times");
    }
}

// ======== DISPLAY TIMES ========
function displayTimes() {
    for (let p in prayerTimes) {
        const el = document.getElementById(p.toLowerCase());
        if (el) el.textContent = prayerTimes[p];
    }
}

// ======== GET NEXT PRAYER ========
function getNextPrayer() {
    const now = new Date();

    for (let p in prayerTimes) {
        const [h, m] = prayerTimes[p].split(":");
        const time = new Date();
        time.setHours(h, m, 0);

        if (time > now) return { name: p, time };
    }

    // Tomorrow Fajr
    const [h, m] = prayerTimes.Fajr.split(":");
    const time = new Date();
    time.setDate(time.getDate() + 1);
    time.setHours(h, m, 0);

    return { name: "Fajr", time };
}

// ======== UPDATE COUNTDOWN ========
function updateCountdown() {
    const next = getNextPrayer();
    const diff = next.time - new Date();

    if (diff <= 0) return adhan.play();

    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);

    nextName.textContent = next.name;
    nextCountdown.textContent = `${h}h ${m}m ${s}s`;

    highlight(next.name);
}

// ======== HIGHLIGHT ========
function highlight(name) {
    document.querySelectorAll(".prayer-card").forEach(card => {
        card.classList.toggle(
            "active",
            card.querySelector("h3").textContent === name
        );
    });
}

// ======== EVENTS ========
loadBtn.addEventListener("click", fetchPrayerTimes);
window.addEventListener("DOMContentLoaded", fetchPrayerTimes);