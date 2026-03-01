function showDates() {
    const today = new Date();

    // Gregorian Date
    const gregorianOptions = {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric"
    };

    document.getElementById("gregorian-date").innerText =
        today.toLocaleDateString("en-US", gregorianOptions);

    // Islamic (Hijri) Date
    const hijriOptions = {
        day: "numeric",
        month: "long",
        year: "numeric"
    };

    document.getElementById("hijri-date").innerText =
        today.toLocaleDateString("en-TN-u-ca-islamic", hijriOptions) + " AH";
}

showDates();