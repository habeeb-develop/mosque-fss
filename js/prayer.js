// ======== DOM ELEMENTS ========
const loadPrayerBtn = document.getElementById("load-prayer-btn");
const prayerContainer = document.querySelector(".prayer-container");
const nextPrayerNameEl = document.getElementById("next-prayer-name");
const nextPrayerCountdownEl = document.getElementById("next-prayer-countdown");
const adhanAudio = document.getElementById("adhan-audio");

// Store prayer times dynamically
let prayerTimes = {};
let countdownInterval;

// ======== FETCH PRAYER TIMES FROM API ========
async function fetchPrayerTimes() {
    try {
        const response = await fetch(
            "https://api.aladhan.com/v1/timingsByCity?city=Lagos&country=Nigeria&method=2"
        );

        const data = await response.json();
        const timings = data.data.timings;

        // Store only required prayers
        prayerTimes = {
            Fajr: timings.Fajr,
            Zuhr: timings.Dhuhr,
            Asr: timings.Asr,
            Maghrib: timings.Maghrib,
            Isha: timings.Isha
        };

        updatePrayerCards();

        // Start countdown for next prayer
        if (countdownInterval) clearInterval(countdownInterval);
        updateCountdown();
        countdownInterval = setInterval(updateCountdown, 1000);

    } catch (error) {
        console.error("Error fetching prayer times:", error);
        alert("Failed to load prayer times. Try again later.");
    }
}

// ======== UPDATE PRAYER CARDS ========
function updatePrayerCards() {
    for (let prayer in prayerTimes) {
        const pEl = document.getElementById(prayer.toLowerCase());
        if (pEl) {
            pEl.textContent = prayerTimes[prayer];
        }
    }
}

// ======== GET NEXT PRAYER ========
function getNextPrayer() {
    const now = new Date();
    let nextPrayer = null;
    let nextPrayerTime = null;

    for (let prayer in prayerTimes) {
        let [hour, minute] = prayerTimes[prayer].split(":");
        let prayerDate = new Date();
        prayerDate.setHours(parseInt(hour));
        prayerDate.setMinutes(parseInt(minute));
        prayerDate.setSeconds(0);

        if (prayerDate > now) {
            nextPrayer = prayer;
            nextPrayerTime = prayerDate;
            break;
        }
    }

    // If all prayers passed, next is tomorrow's Fajr
    if (!nextPrayer) {
        let [hour, minute] = prayerTimes["Fajr"].split(":");
        nextPrayer = "Fajr";
        nextPrayerTime = new Date();
        nextPrayerTime.setDate(nextPrayerTime.getDate() + 1);
        nextPrayerTime.setHours(parseInt(hour));
        nextPrayerTime.setMinutes(parseInt(minute));
        nextPrayerTime.setSeconds(0);
    }

    return { name: nextPrayer, time: nextPrayerTime };
}

// ======== HIGHLIGHT NEXT PRAYER ========
function highlightNextPrayer() {
    const cards = document.querySelectorAll(".prayer-card");
    cards.forEach(card => card.classList.remove("active"));

    const next = getNextPrayer();
    const nextCard = Array.from(cards).find(
        card => card.querySelector("h3").textContent === next.name
    );

    if (nextCard) nextCard.classList.add("active");

    return next;
}

// ======== UPDATE COUNTDOWN ========
function updateCountdown() {
    const next = highlightNextPrayer();
    const now = new Date();
    const diff = next.time - now;

    if (diff <= 0) {
        adhanAudio.play();
        return;
    }

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);

    nextPrayerNameEl.textContent = next.name;
    nextPrayerCountdownEl.textContent = `${hours}h ${minutes}m ${seconds}s`;
}

// ======== BUTTON EVENT ========
loadPrayerBtn.addEventListener("click", fetchPrayerTimes);

// ======== AUTO LOAD ON PAGE OPEN ========
window.addEventListener("DOMContentLoaded", fetchPrayerTimes);