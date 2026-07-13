const canvas = document.getElementById('tankCanvas');
const ctx = canvas.getContext('2d');
const fireBtn = document.getElementById('fireBtn');
const angleInput = document.getElementById('angleInput');
const powerInput = document.getElementById('powerInput');

let score = 0;
let isGameOver = false;
let turn = "player"; // "player" oder "bot"

const gravity = 0.15;

const player = { x: 80, y: 350, width: 40, height: 20, hp: 100, color: '#00adb5' };
const bot = { x: 620, y: 350, width: 40, height: 20, hp: 100, color: '#ff2e63' };
let bullet = null;

function fireProjectile(startX, startY, angle, power, isBot = false) {
    if (bullet) return; // Nur ein Schuss gleichzeitig erlaubt

    // Winkel in Bogenmaß umrechnen
    let rad = (angle * Math.PI) / 180;
    
    bullet = {
        x: startX,
        y: startY - 10,
        vx: Math.cos(rad) * power * (isBot ? -1 : 1), // Bot schießt nach links
        vy: -Math.sin(rad) * power,
        radius: 5,
        isBot: isBot
    };
}

fireBtn.addEventListener('click', () => {
    if (turn !== "player" || isGameOver) return;
    let angle = parseFloat(angleInput.value);
    let power = parseFloat(powerInput.value);
    fireProjectile(player.x + 20, player.y, angle, power, false);
    turn = "bot";
});

function botTurn() {
    if (isGameOver) return;
    setTimeout(() => {
        // Der Bot rät einen zufälligen, aber spielbaren Winkel und Kraft
        let randomAngle = 30 + Math.random() * 35;
        let randomPower = 10 + Math.random() * 6;
        fireProjectile(bot.x + 20, bot.y, randomAngle, randomPower, true);
        turn = "player";
    }, 1500);
}

async function sendScoreToServer(finalScore) {
    try {
        await fetch('/api/submit-tank-score', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ score: finalScore })
        });
    } catch (e) { console.error(e); }
}

function checkCollision(b, target) {
    return (b.x > target.x && b.x < target.x + target.width &&
            b.y > target.y && b.y < target.y + target.height);
}

function update() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Boden zeichnen
    ctx.fillStyle = '#222831'; ctx.fillRect(0, 370, canvas.width, 30);

    // Spieler-Panzer
    ctx.fillStyle = player.color; ctx.fillRect(player.x, player.y, player.width, player.height);
    ctx.fillStyle = '#fff'; ctx.font = '12px Arial'; ctx.fillText(`HP: ${player.hp}`, player.x, player.y - 10);

    // Bot-Panzer
    ctx.fillStyle = bot.color; ctx.fillRect(bot.x, bot.y, bot.width, bot.height);
    ctx.fillStyle = '#fff'; ctx.fillText(`HP: ${bot.hp}`, bot.x, bot.y - 10);

    // Projektil-Physik & Bewegung
    if (bullet) {
        bullet.vy += gravity; // Gravitation zieht die Kugel runter
        bullet.x += bullet.vx;
        bullet.y += bullet.vy;

        // Kugel zeichnen
        ctx.fillStyle = '#f9d423';
        ctx.beginPath(); ctx.arc(bullet.x, bullet.y, bullet.radius, 0, Math.PI * 2); ctx.fill();

        // Kollision mit dem Boden oder Spielfeldrand
        if (bullet.y > 370 || bullet.x < 0 || bullet.x > canvas.width) {
            bullet = null;
            if (turn === "bot") botTurn();
        } 
        // Kollision mit Bot (Spieler trifft)
        else if (!bullet.isBot && checkCollision(bullet, bot)) {
            bot.hp -= 35;
            score += 10;
            bullet = null;
            if (bot.hp <= 0) {
                // Bot zerstört -> Spawnt mit vollem Leben neu, Spiel geht weiter für mehr Punkte!
                bot.hp = 100;
                bot.x = 400 + Math.random() * 250; // Neue Zufallsposition für den Bot
            }
            botTurn();
        }
        // Kollision mit Spieler (Bot trifft)
        else if (bullet.isBot && checkCollision(bullet, player)) {
            player.hp -= 35;
            bullet = null;
            if (player.hp <= 0) {
                isGameOver = true;
                sendScoreToServer(score);
            }
        }
    }

    // UI Anzeigen
    ctx.fillStyle = '#fff'; ctx.font = 'bold 20px Arial';
    ctx.fillText(`Score: ${score}`, 20, 35);
    ctx.fillText(turn === "player" ? "Du bist dran!" : "Bot berechnet Schuss...", canvas.width / 2 - 80, 35);

    if (isGameOver) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.85)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#ff2e63'; ctx.font = 'bold 40px Arial'; ctx.fillText('GAME OVER', canvas.width / 2 - 120, canvas.height / 2);
        ctx.fillStyle = '#fff'; ctx.font = '16px Arial'; ctx.fillText('Klicke zum Neustarten', canvas.width / 2 - 80, canvas.height / 2 + 40);
    }

    requestAnimationFrame(update);
}

canvas.addEventListener('click', () => {
    if (isGameOver) {
        player.hp = 100; bot.hp = 100; score = 0; isGameOver = false; turn = "player";
        bullet = null;
    }
});

update();
