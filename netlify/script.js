function updateHeroMessage() {
    const hour = new Date().getHours();
    const mainTitle = document.querySelector('.main-title');
    const subTitle = document.querySelector('.sub-title');

    // Falls die Elemente noch nicht geladen sind, abbrechen
    if (!mainTitle || !subTitle) return;

    if (hour >= 6 && hour < 9) {
        mainTitle.innerText = "DER PERFEKTE START IN DEN TAG";
        subTitle.innerText = "GUTEN MORGEN BEI AUTO WALLSTEIN";
    } else if (hour >= 9 && hour < 17) {
        mainTitle.innerText = "FROHE WEIHNACHTEN";
        subTitle.innerText = "WÜSNCHT IHR PARTNER FÜR JAHRESWAGEN";
    } else if (hour >= 17 && hour < 22) {
        mainTitle.innerText = "ZEIT FÜR NEUE ZIELE";
        subTitle.innerText = "ENTSPANNT DEN NÄCHSTEN TRAUMWAGEN FINDEN";
    } else {
        mainTitle.innerText = "TRÄUME SCHLAFEN NIE";
        subTitle.innerText = "UNSERE DIGITALE GALERIE IST FÜR SIE GEÖFFNET";
    }
}

function toggleZeroPercent() {
    const isZero = document.getElementById('zero-percent').checked;
    const container = document.getElementById('zins-container');
    
    // Zinsfelder verstecken oder zeigen
    container.style.display = isZero ? 'none' : 'block';
    
    // Berechnung sofort aktualisieren
    updateCalc();
}

function updateCalc() {
    const priceEl = document.getElementById('price');
    const downEl = document.getElementById('downpayment');
    const monthsEl = document.getElementById('months');
    const balloonEl = document.getElementById('balloon'); // Neu
    const effInterestEl = document.getElementById('eff-interest');
    const sollInterestEl = document.getElementById('soll-interest');
    const isZero = document.getElementById('zero-percent').checked;

    if (!priceEl || !downEl || !monthsEl) return;

    let originalPrice = parseFloat(priceEl.value) || 0;
    const downpayment = parseFloat(downEl.value) || 0;
    const months = parseInt(monthsEl.value) || 12;
    const balloon = parseFloat(balloonEl.value) || 0; // Neu
    
    const targetRate = 5.9; 
    let currentEffRate;

    if (isZero) {
        currentEffRate = 0;
    } else {
        currentEffRate = parseFloat(effInterestEl.value);
        if (isNaN(currentEffRate)) currentEffRate = targetRate;
    }

    // Basis-Kreditbetrag
    let baseLoan = originalPrice - downpayment;
    if (baseLoan < 0) baseLoan = 0;

    // Monatlicher Zinsfaktor
    const i = currentEffRate > 0 ? Math.pow(1 + (currentEffRate / 100), 1/12) - 1 : 0;
    
    let monthlyRate = 0;

    if (baseLoan > 0) {
        if (currentEffRate === 0) {
            // Bei 0% Zins: Einfache Aufteilung
            monthlyRate = (baseLoan - balloon) / months;
        } else {
            // Formel für Ballonfinanzierung:
            // Rate = [Kredit * i * (1+i)^n - Schlussrate * i] / [(1+i)^n - 1]
            const q = Math.pow(1 + i, months);
            monthlyRate = (baseLoan * i * q - balloon * i) / (q - 1);
        }
    }

    // Falls die Rate negativ wird (Schlussrate zu hoch), auf 0 setzen
    if (monthlyRate < 0) monthlyRate = 0;

    // Sollzins-Feld im HTML updaten
    if (sollInterestEl) {
        sollInterestEl.value = (i * 12 * 100).toFixed(2);
    }

    // Gesamtkosten & Zinsen berechnen
    const totalReturn = (monthlyRate * months) + balloon + downpayment;
    const totalInterestDisplay = isZero ? 0 : (totalReturn - originalPrice);

    displayAllResults(monthlyRate, baseLoan, months, downpayment, totalInterestDisplay, isZero, balloon);
}

// Update der Anzeige-Funktion (um die Schlussrate im Text zu berücksichtigen)
function displayAllResults(rate, loan, months, down, interest, isZero, balloon) {
    const formatter = new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' });
    
    const safeRate = rate || 0;
    const totalReturn = (safeRate * months) + balloon + down;

    document.getElementById('monthly-rate').innerText = formatter.format(safeRate);
    document.getElementById('loan-amount').innerText = formatter.format(loan);
    document.getElementById('total-cost').innerText = formatter.format(totalReturn);
    
    const intEl = document.getElementById('total-interest');
    if (isZero) {
        intEl.innerText = "Inklusive";
        intEl.style.color = "#00ff00";
    } else {
        intEl.innerText = formatter.format(interest > 0 ? interest : 0);
        intEl.style.color = "#ffcc00";
    }
    
}



function toggleAccMenu() {
    const menu = document.getElementById('acc-menu');
    menu.classList.toggle('hidden');
}

function changeFontSize(action) {
    let html = document.documentElement;
    let currentSize = parseFloat(window.getComputedStyle(html).fontSize);
    html.style.fontSize = (action === 'increase' ? currentSize + 2 : currentSize - 2) + 'px';
}

function toggleInvert() {
    document.documentElement.classList.toggle('acc-invert');
}

function toggleGrayscale() {
    document.documentElement.classList.toggle('acc-grayscale');
}

function highlightLinks() {
    document.body.classList.toggle('acc-highlight-links');
}

function toggleReadableFont() {
    document.body.classList.toggle('acc-readable-font');
}

function resetAcc() {
    document.documentElement.style.fontSize = '';
    document.documentElement.classList.remove('acc-invert', 'acc-grayscale');
    document.body.classList.remove('acc-highlight-links', 'acc-readable-font');
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.querySelector(".scroll-hint");
  const iframeContainer = document.getElementById("fahrzeuge-iframe");

  if (!btn || !iframeContainer) return;

  btn.addEventListener("click", () => {
    const rect = iframeContainer.getBoundingClientRect();
    const iframeHeight = iframeContainer.offsetHeight;

    // 0.6 = eher untere Hälfte (0.5 Mitte, 0.7 noch weiter unten)
    const targetY = window.scrollY + rect.top + iframeHeight * 0.4;

    window.scrollTo({
      top: targetY,
      behavior: "smooth",
    });
  });
});
function updateLiveStatus() {
    const now = new Date();
    const day = now.getDay(); // 0 = So, 1 = Mo, ..., 6 = Sa
    const hour = now.getHours();
    const min = now.getMinutes();
    const currentTime = hour + min / 60;

    const statusText = document.getElementById('open-status');
    const statusDot = document.getElementById('status-dot');

    let isOpen = false;
    let isPause = false;

    // Logik für Montag bis Freitag
    if (day >= 1 && day <= 5) {
        if (currentTime >= 9 && currentTime < 18) {
            // Prüfung auf Mittagspause (13:00 bis 14:30)
            if (currentTime >= 13 && currentTime < 14.5) {
                isPause = true;
            } else {
                isOpen = true;
            }
        }
    } 
    // Logik für Samstag (keine Mittagspause)
    else if (day === 6) {
        if (currentTime >= 10 && currentTime < 14) {
            isOpen = true;
        }
    }

    // Anzeige aktualisieren
    if (isPause) {
        statusText.innerText = "AKTUELL MITTAGSPAUSE";
        statusDot.style.backgroundColor = "#ffcc00"; // Gelb für Pause
        statusDot.style.boxShadow = "0 0 8px #ffcc00";
    } else if (isOpen) {
        statusText.innerText = "JETZT GEÖFFNET";
        statusDot.style.backgroundColor = "#00ff00"; // Grün
        statusDot.style.boxShadow = "0 0 8px #00ff00";
    } else {
        statusText.innerText = "AKTUELL GESCHLOSSEN";
        statusDot.style.backgroundColor = "#ff4444"; // Rot
        statusDot.style.boxShadow = "0 0 8px #ff4444";
    }
}

document.addEventListener('DOMContentLoaded', updateLiveStatus);

