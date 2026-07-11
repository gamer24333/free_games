const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// Spielvariablen
let gameSpeed = 5;
let score = 0;
let isGameOver = false;

// Spieler (Das Viereck)
const player = {
    x: 100,
    y: 300,
    size: 40,
    vy: 0,
    gravity: 0.6,
    jumpForce: -12,
    isGrounded: false,
    rotation: 0
};

// Hindernisse (Die Dreiecke)
let obstacles = [];
const floorY = 340; // Höhe des Bodens

// Steuerung (Leertaste am PC, Klick/Touch auf dem iPad)
function doJump() {
    if (player.isGrounded && !isGameOver) {
        player.vy = player.jumpForce;
        player.isGrounded = false;
    }
    if (isGameOver) {
        resetGame();
    }
}

window.addEventListener('keydown', (e) => {
    if (e.code === 'Space') {
        e.preventDefault(); // Verhindert das Scrollen der Seite beim Springen
        doJump();
    }
});

canvas.addEventListener('touchstart', (e) => {
    e.preventDefault();
    doJump();
});

canvas.addEventListener('mousedown', () => {
    doJump();
});

// Funktion zum Erstellen eines neuen Hindernisses
function spawnObstacle() {
    if (isGameOver) return;
    
    obstacles.push({
        x: canvas.width,
        y: floorY,
        width: 30,
        height: 40
    });

    // Zufälliges Timing für das nächste Hindernis (zwischen 1 und 2.5 Sekunden)
    let nextSpawn = 1000 + Math.random() * 1500;
    setTimeout(spawnObstacle, nextSpawn / (gameSpeed / 5));
}

// Spiel zurücksetzen
function resetGame() {
    obstacles = [];
    score = 0;
    gameSpeed = 5;
    isGameOver = false;
    player.y = floorY - player.size;
    player.vy = 0;
    player.rotation = 0;
}

// Haupt-Gameloop
function update() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 1. Boden zeichnen
    ctx.fillStyle = '#333';
    ctx.fillRect(0, floorY, canvas.width, canvas.height - floorY);
    ctx.strokeStyle = '#00adb5';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(0, floorY);
    ctx.lineTo(canvas.width, floorY);
    ctx.stroke();

    // 2. Spieler-Physik (Schwerkraft)
    player.vy += player.gravity;
    player.y += player.vy;

    // Am Boden stoppen
    if (player.y >= floorY - player.size) {
        player.y = floorY - player.size;
        player.vy = 0;
        player.isGrounded = true;
        // Rotation auf das nächste Vielfache von 90 Grad ausrichten beim Landen
        player.rotation = Math.round(player.rotation / (Math.PI / 2)) * (Math.PI / 2);
    } else {
        // In der Luft rotieren
        player.rotation += 0.08;
    }

    // 3. Spieler zeichnen (mit Rotation)
    ctx.save();
    ctx.translate(player.x + player.size / 2, player.y + player.size / 2);
    ctx.rotate(player.rotation);
    ctx.fillStyle = '#00adb5';
    ctx.fillRect(-player.size / 2, -player.size / 2, player.size, player.size);
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.strokeRect(-player.size / 2, -player.size / 2, player.size, player.size);
    ctx.restore();

    // 4. Hindernisse bewegen und zeichnen
    for (let i = obstacles.length - 1; i >= 0; i--) {
        let obs = obstacles[i];
        if (!isGameOver) {
            obs.x -= gameSpeed;
        }

        // Dreieck zeichnen
        ctx.fillStyle = '#ff2e63';
        ctx.beginPath();
        ctx.moveTo(obs.x, obs.y);
        ctx.lineTo(obs.x + obs.width / 2, obs.y - obs.height);
        ctx.lineTo(obs.x + obs.width, obs.y);
        ctx.closePath();
        ctx.fill();

        // Kollisionserkennung (Hitbox)
        if (
            player.x < obs.x + obs.width &&
            player.x + player.size > obs.x &&
            player.y + player.size > obs.y - obs.height
        ) {
            isGameOver = true;
        }

        // Punkte zählen, wenn das Hindernis hinter dem Spieler ist
        if (obs.x + obs.width < player.x && !obs.passed) {
            obs.passed = true;
            score++;
            // Spiel wird alle 3 Punkte ein bisschen schneller
            if (score % 3 === 0) {
                gameSpeed += 0.8;
            }
        }

        // Aus dem Bildschirm gelaufene Hindernisse löschen
        if (obs.x < -obs.width) {
            obstacles.splice(i, 1);
        }
    }

    // 5. Score anzeigen
    ctx.fillStyle = '#fff';
    ctx.font = '24px Arial';
    ctx.fillText(`Score: ${score}`, 20, 40);

    // Game Over Text anzeigen
    if (isGameOver) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        ctx.fillStyle = '#ff2e63';
        ctx.font = 'bold 40px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('GAME OVER', canvas.width / 2, canvas.height / 2 - 20);
        
        ctx.fillStyle = '#fff';
        ctx.font = '20px Arial';
        ctx.fillText('Tippe oder drücke Leertaste zum Neustarten', canvas.width / 2, canvas.height / 2 + 20);
        ctx.textAlign = 'left'; // Reset für Score-Anzeige
    }

    requestAnimationFrame(update);
}

// Erstes Hindernis triggern und Game-Loop starten
setTimeout(spawnObstacle, 2000);
update();
