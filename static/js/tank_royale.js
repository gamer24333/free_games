const gameId = "{{ gameId }}";
const me = "{{ me }}";

const canvas = document.getElementById('tankCanvas');
const ctx = canvas.getContext('2d');
const shootBtn = document.getElementById('shootBtn'); // Korrekte ID aus dem HTML
const angleInput = document.getElementById('angleInput');
const powerInput = document.getElementById('powerInput');

let gameState = {};
let bullet = null;
const gravity = 0.15;

// 1. Status vom Server abrufen
async function updateStatus() {
    try {
        let res = await fetch(`/api/tankroyale/status/${gameId}`);
        if (!res.ok) return;
        
        gameState = await res.json();
        
        if (!gameState || !gameState.status) return;

        // Prüfen, ob man selbst an der Reihe ist
        const isMyTurn = (gameState.turn === me && gameState.status === "aktiv");
        
        // Button nur aktivieren, wenn man dran ist und kein Projektil fliegt
        shootBtn.disabled = !isMyTurn || bullet !== null;

        // Text-Anzeige aktualisieren
        const matchInfo = document.getElementById('matchInfo');
        if (gameState.status === "eingeladen") {
            matchInfo.innerText = "Warte darauf, dass der Gegner annimmt... ⏳";
        } else if (gameState.status.startsWith("gewonnen")) {
            let winner = gameState.status.split('_')[1];
            matchInfo.innerText = winner === me ? "🎉 DU HAST GEWONNEN! 🎉" : `❌ ${winner} hat dich zerstört!`;
            shootBtn.disabled = true;
        } else {
            matchInfo.innerText = isMyTurn ? "🔴 DU BIST DRAN! Schieß!" : `⏳ ${gameState.turn} berechnet den Schuss...`;
        }
    } catch (e) {
        console.error("Fehler beim Abrufen des Status:", e);
    }
}

// 2. Spielfeld zeichnen
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Boden zeichnen
    ctx.fillStyle = '#222831'; 
    ctx.fillRect(0, 370, canvas.width, 30);

    // Schutz: Wenn noch keine Serverdaten da sind, hier abbrechen
    if (!gameState || !gameState.status) return;

    let amIErsteller = (me === gameState.ersteller);
    let p1 = { x: gameState.p1_x, y: 350, hp: gameState.p1_hp, color: '#00adb5', name: gameState.ersteller };
    let p2 = { x: gameState.p2_x, y: 350, hp: gameState.p2_hp, color: '#ff2e63', name: gameState.gegner };

    // Panzer 1 (Ersteller) zeichnen
    ctx.fillStyle = p1.color; 
    ctx.fillRect(p1.x, p1.y, 40, 20);
    ctx.fillStyle = '#fff'; 
    ctx.font = '12px Arial'; 
    ctx.fillText(`${p1.name} (HP: ${p1.hp})`, p1.x - 10, p1.y - 10);

    // Panzer 2 (Gegner) zeichnen
    ctx.fillStyle = p2.color; 
    ctx.fillRect(p2.x, p2.y, 40, 20);
    ctx.fillStyle = '#fff'; 
    ctx.fillText(`${p2.name} (HP: ${p2.hp})`, p2.x - 10, p2.y - 10);

    // Projektil bewegen und zeichnen
    if (bullet) {
        bullet.vy += gravity;
        bullet.x += bullet.vx;
        bullet.y += bullet.vy;

        ctx.fillStyle = '#f9d423';
        ctx.beginPath(); 
        ctx.arc(bullet.x, bullet.y, 5, 0, Math.PI * 2); 
        ctx.fill();

        let target = amIErsteller ? p2 : p1;

        // Kollisionsprüfung (Lokal)
        if (bullet.x > target.x && bullet.x < target.x + 40 && bullet.y > target.y && bullet.y < target.y + 20) {
            let hitTarget = amIErsteller ? "p2" : "p1";
            sendShotResult(bullet.angle, bullet.power, hitTarget);
            bullet = null;
        } else if (bullet.y > 370 || bullet.x < 0 || bullet.x > canvas.width) {
            sendShotResult(bullet.angle, bullet.power, "none");
            bullet = null;
        }
    }
}

// 3. Schuss-Ergebnis an das Backend melden
async function sendShotResult(angle, power, hit) {
    try {
        await fetch(`/api/tankroyale/shoot/${gameId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ angle: angle, power: power, hit: hit })
        });
        updateStatus();
    } catch (e) {
        console.error("Fehler beim Senden des Schusses:", e);
    }
}

// 4. Klick auf den Feuer-Button
shootBtn.addEventListener('click', () => {
    if (!gameState.status || bullet !== null) return;

    let angle = parseFloat(angleInput.value);
    let power = parseFloat(powerInput.value);
    let rad = (angle * Math.PI) / 180;
    
    let amIErsteller = (me === gameState.ersteller);
    let startX = amIErsteller ? gameState.p1_x + 20 : gameState.p2_x + 20;

    bullet = {
        x: startX,
        y: 340,
        vx: Math.cos(rad) * power * (amIErsteller ? 1 : -1), // Richtung nach links/rechts spiegeln
        vy: -Math.sin(rad) * power,
        angle: angle,
        power: power
    };
    
    shootBtn.disabled = true;
});

// 5. Game Loop (Zeichnet permanent das Spielfeld)
function gameLoop() {
    draw();
    requestAnimationFrame(gameLoop);
}

// Intervalle und Start-Trigger
setInterval(updateStatus, 2000); // Alle 2 Sekunden Match-Daten aktualisieren
updateStatus(); // Sofort beim Laden einmalig ausführen
gameLoop(); // Animations-Schleife starten
