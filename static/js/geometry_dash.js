const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

let gameSpeed = 5;
let score = 0;
let level = 1;
let isGameOver = false;
const floorY = 340;

const player = {
    x: 80, y: 300, size: 35, vy: 0,
    gravity: 0.6, jumpForce: -11.5, isGrounded: false, rotation: 0
};

let obstacles = [];
let spawnTimeout;

function doJump() {
    if (player.isGrounded && !isGameOver) {
        player.vy = player.jumpForce;
        player.isGrounded = false;
    }
    if (isGameOver) resetGame();
}

window.addEventListener('keydown', (e) => { if (e.code === 'Space') { e.preventDefault(); doJump(); } });
canvas.addEventListener('touchstart', (e) => { e.preventDefault(); doJump(); });
canvas.addEventListener('mousedown', doJump);

function spawnObstacle() {
    if (isGameOver) return;

    // Unterschiede: Zufall entscheidet zwischen Typ 1 (Dreieck) oder Typ 2 (Block)
    let type = Math.random() > 0.4 ? 'spike' : 'block';
    
    if (type === 'spike') {
        obstacles.push({ x: canvas.width, y: floorY, width: 30, height: 35, type: 'spike' });
    } else {
        // Ein Block, der in der Luft schwebt (man kann drunter durchlaufen) oder auf dem Boden steht
        let onFloor = Math.random() > 0.5;
        obstacles.push({
            x: canvas.width,
            y: onFloor ? floorY : floorY - 65,
            width: 35, height: 35, type: 'block'
        });
    }

    let nextSpawn = 1200 + Math.random() * 1600;
    spawnTimeout = setTimeout(spawnObstacle, nextSpawn / (gameSpeed / 5));
}

async function sendScoreToServer(finalScore) {
    try {
        await fetch('/api/submit-score', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ score: finalScore })
        });
    } catch (e) { console.error("Score-Übertragungsfehler", e); }
}

function resetGame() {
    clearTimeout(spawnTimeout);
    obstacles = [];
    score = 0; level = 1; gameSpeed = 5;
    player.y = floorY - player.size; player.vy = 0; player.rotation = 0;
    isGameOver = false;
    spawnObstacle();
}

function update() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Hintergrund & Boden zeichnen
    ctx.fillStyle = '#181818'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#292929'; ctx.fillRect(0, floorY, canvas.width, canvas.height - floorY);
    ctx.strokeStyle = '#00adb5'; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.moveTo(0, floorY); ctx.lineTo(canvas.width, floorY); ctx.stroke();

    // Physik
    player.vy += player.gravity;
    player.y += player.vy;

    if (player.y >= floorY - player.size) {
        player.y = floorY - player.size; player.vy = 0; player.isGrounded = true;
        player.rotation = Math.round(player.rotation / (Math.PI / 2)) * (Math.PI / 2);
    } else {
        player.rotation += 0.09;
    }

    // Spieler zeichnen
    ctx.save();
    ctx.translate(player.x + player.size/2, player.y + player.size/2);
    ctx.rotate(player.rotation);
    ctx.fillStyle = '#00adb5'; ctx.fillRect(-player.size/2, -player.size/2, player.size, player.size);
    ctx.strokeStyle = '#fff'; ctx.strokeRect(-player.size/2, -player.size/2, player.size, player.size);
    ctx.restore();

    // Hindernisse updaten
    for (let i = obstacles.length - 1; i >= 0; i--) {
        let obs = obstacles[i];
        if (!isGameOver) obs.x -= gameSpeed;

        // Unterschiede beim Zeichnen der Objekte
        if (obs.type === 'spike') {
            ctx.fillStyle = '#ff2e63';
            ctx.beginPath();
            ctx.moveTo(obs.x, obs.y);
            ctx.lineTo(obs.x + obs.width/2, obs.y - obs.height);
            ctx.lineTo(obs.x + obs.width, obs.y);
            ctx.closePath(); ctx.fill();
        } else {
            ctx.fillStyle = '#f9d423'; // Gelbe Blöcke
            ctx.fillRect(obs.x, obs.y - obs.height, obs.width, obs.height);
            ctx.strokeStyle = '#fff'; ctx.strokeRect(obs.x, obs.y - obs.height, obs.width, obs.height);
        }

        // Kollisionsprüfung
        if (
            player.x < obs.x + obs.width &&
            player.x + player.size > obs.x &&
            player.y + player.size > obs.y - obs.height &&
            player.y < obs.y
        ) {
            if (!isGameOver) {
                isGameOver = true;
                sendScoreToServer(score); // Sendet Score live an die Klassenliste!
            }
        }

        // Punkte & Levelaufstieg
        if (obs.x + obs.width < player.x && !obs.passed) {
            obs.passed = true;
            score++;
            if (score % 5 === 0) {
                level++;
                gameSpeed += 1.2; // Wird spürbar schneller pro Level
            }
        }

        if (obs.x < -obs.width) obstacles.splice(i, 1);
    }

    // UI Texte
    ctx.fillStyle = '#fff'; ctx.font = '20px Arial';
    ctx.fillText(`Score: ${score}`, 20, 35);
    ctx.fillText(`Level: ${level}`, 150, 35);

    if (isGameOver) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.75)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#ff2e63'; ctx.font = 'bold 36px Arial'; ctx.textAlign = 'center';
        ctx.fillText('GAME OVER', canvas.width / 2, canvas.height / 2 - 20);
        ctx.fillStyle = '#fff'; ctx.font = '18px Arial';
        ctx.fillText('Tippen zum Speichern & Neustarten', canvas.width / 2, canvas.height / 2 + 20);
        ctx.textAlign = 'left';
    }

    requestAnimationFrame(update);
}

spawnObstacle();
update();
