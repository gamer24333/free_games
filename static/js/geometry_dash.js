const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const pauseBtn = document.getElementById('pauseBtn');

let gameSpeed = 5;
let score = 0;
let level = 1;
let isGameOver = false;
let isPaused = false;      
let gameStarted = false;   
const floorY = 340;
const ceilingY = 60; // Decke für den Ball-Modus

const player = {
    x: 80, y: 300, size: 35, vy: 0,
    gravity: 0.6, jumpForce: -11.5, isGrounded: false, rotation: 0,
    mode: 'cube' // Kann 'cube' oder 'ball' sein
};

let obstacles = [];
let spawnTimeout;

function doJump() {
    if (isPaused) return; 
    
    if (!gameStarted && !isGameOver) {
        gameStarted = true;
        if (pauseBtn) pauseBtn.style.display = "inline-block"; 
    }

    if (!isGameOver) {
        if (player.mode === 'cube') {
            // Normaler Modus: Nur springen, wenn auf dem Boden oder auf einer Plattform
            if (player.isGrounded) {
                player.vy = player.jumpForce;
                player.isGrounded = false;
            }
        } else if (player.mode === 'ball') {
            // Ball-Modus: Gravitation umdrehen bei jedem Klick/Leertaste
            player.gravity = -player.gravity;
            player.isGrounded = false;
        }
    }
    
    if (isGameOver) resetGame();
}

function togglePause() {
    if (!gameStarted || isGameOver) return; 
    isPaused = !isPaused;
    if (pauseBtn) {
        pauseBtn.textContent = isPaused ? "▶️ Weiter" : "⏸️ Pause";
    }
}

// Controls
window.addEventListener('keydown', (e) => { 
    if (e.code === 'Space') { e.preventDefault(); doJump(); } 
    if (e.code === 'Escape') { e.preventDefault(); togglePause(); }
});
canvas.addEventListener('touchstart', (e) => { e.preventDefault(); doJump(); });
canvas.addEventListener('mousedown', doJump);

if (pauseBtn) pauseBtn.addEventListener('click', togglePause);

function spawnObstacle() {
    if (isGameOver) return;
    if (isPaused) {
        spawnTimeout = setTimeout(spawnObstacle, 200);
        return;
    }

    // Zufall zwischen Spike, Block, schwebender Plattform oder einem Modus-Wechsel-Portal
    let rand = Math.random();
    
    if (rand < 0.35) {
        // 1. Spike am Boden oder an der Decke (falls Ball)
        let onCeiling = player.mode === 'ball' && Math.random() > 0.5;
        obstacles.push({ 
            x: canvas.width, 
            y: onCeiling ? ceilingY : floorY, 
            width: 30, height: 35, 
            type: 'spike',
            ceil: onCeiling
        });
    } else if (rand < 0.65) {
        // 2. Schwebende Plattform / Platte zum draufspringen
        let heightLevel = floorY - 70 - Math.floor(Math.random() * 2) * 50;
        obstacles.push({
            x: canvas.width,
            y: heightLevel,
            width: 90, height: 20, 
            type: 'platform'
        });
    } else if (rand < 0.85) {
        // 3. Normaler Block (Hindernis)
        let onFloor = Math.random() > 0.4;
        obstacles.push({
            x: canvas.width,
            y: onFloor ? floorY : floorY - 65,
            width: 35, height: 35, type: 'block'
        });
    } else {
        // 4. Portal (Wechselt den Modus zwischen Cube und Ball)
        let nextMode = player.mode === 'cube' ? 'ball' : 'cube';
        obstacles.push({
            x: canvas.width,
            y: floorY - 100,
            width: 30, height: 100,
            type: 'portal',
            targetMode: nextMode
        });
    }

    // Spawn-Rate zieht mit der Geschwindigkeit an, damit Abstände fair bleiben
    let nextSpawn = 1000 + Math.random() * 1400;
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
    player.mode = 'cube';
    player.gravity = 0.6;
    player.y = floorY - player.size; player.vy = 0; player.rotation = 0;
    isGameOver = false; isPaused = false; gameStarted = false;
    if (pauseBtn) { pauseBtn.style.display = "none"; pauseBtn.textContent = "⏸️ Pause"; }
    spawnObstacle();
}

function update() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 1. Details & Hintergrund zeichnen
    ctx.fillStyle = '#0f111a'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Raster-Linien im Hintergrund für mehr GD-Vibe
    ctx.strokeStyle = 'rgba(0, 173, 185, 0.05)'; ctx.lineWidth = 2;
    let gridSize = 40;
    let offset = gameStarted && !isPaused && !isGameOver ? (Date.now() / 20) % gridSize : 0;
    for (let x = -offset; x < canvas.width; x += gridSize) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }

    // Boden & Decke zeichnen
    ctx.fillStyle = '#161925'; ctx.fillRect(0, floorY, canvas.width, canvas.height - floorY);
    ctx.strokeStyle = '#00adb5'; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.moveTo(0, floorY); ctx.lineTo(canvas.width, floorY); ctx.stroke();

    if (player.mode === 'ball') {
        ctx.fillStyle = '#161925'; ctx.fillRect(0, 0, canvas.width, ceilingY);
        ctx.beginPath(); ctx.moveTo(0, ceilingY); ctx.lineTo(canvas.width, ceilingY); ctx.stroke();
    }

    // 2. Physik & Bewegung (nur wenn nicht pausiert)
    if (!isPaused && gameStarted && !isGameOver) {
        player.vy += player.gravity;
        player.y += player.vy;

        // Kontinuierlicher Speed-Up (Macht das Spiel am Ende extrem rasant!)
        gameSpeed += 0.0015; 

        // Grenzen am Boden checken
        if (player.y >= floorY - player.size) {
            player.y = floorY - player.size; player.vy = 0; player.isGrounded = true;
            if (player.mode === 'cube') {
                player.rotation = Math.round(player.rotation / (Math.PI / 2)) * (Math.PI / 2);
            }
        } 
        // Grenzen an der Decke checken (wichtig für Ball-Modus)
        else if (player.mode === 'ball' && player.y <= ceilingY) {
            player.y = ceilingY; player.vy = 0; player.isGrounded = true;
        } else {
            player.isGrounded = false;
        }

        // Rotation
        if (!player.isGrounded) {
            player.rotation += (player.gravity > 0 ? 0.09 : -0.09);
        } else if (player.mode === 'ball') {
            player.rotation += 0.05 * (gameSpeed / 5); // Ball rollt optisch auf dem Boden
        }
    }

    // 3. Spieler zeichnen
    ctx.save();
    ctx.translate(player.x + player.size/2, player.y + player.size/2);
    ctx.rotate(player.rotation);
    
    if (player.mode === 'cube') {
        // Würfel-Design
        ctx.fillStyle = '#00adb5'; ctx.fillRect(-player.size/2, -player.size/2, player.size, player.size);
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.strokeRect(-player.size/2, -player.size/2, player.size, player.size);
        // Inneres Auge/Viereck für mehr Details
        ctx.fillStyle = '#222831'; ctx.fillRect(-player.size/4, -player.size/4, player.size/2, player.size/2);
    } else {
        // Ball-Design
        ctx.fillStyle = '#ff9f43'; ctx.beginPath(); ctx.arc(0, 0, player.size/2, 0, Math.PI*2); ctx.fill();
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.stroke();
        // Muster im Ball
        ctx.beginPath(); ctx.moveTo(-player.size/2, 0); ctx.lineTo(player.size/2, 0); ctx.stroke();
    }
    ctx.restore();

    // 4. Hindernisse updaten & kollidieren
    let onAnyPlatform = false;

    for (let i = obstacles.length - 1; i >= 0; i--) {
        let obs = obstacles[i];
        if (!isGameOver && !isPaused) obs.x -= gameSpeed;

        // --- ZEICHNEN DER OBJEKTE ---
        if (obs.type === 'spike') {
            ctx.fillStyle = '#ff2e63';
            ctx.beginPath();
            if (obs.ceil) { // Deckenspike zeigt nach unten
                ctx.moveTo(obs.x, obs.y);
                ctx.lineTo(obs.x + obs.width/2, obs.y + obs.height);
                ctx.lineTo(obs.x + obs.width, obs.y);
            } else { // Bodenspike zeigt nach oben
                ctx.moveTo(obs.x, obs.y);
                ctx.lineTo(obs.x + obs.width/2, obs.y - obs.height);
                ctx.lineTo(obs.x + obs.width, obs.y);
            }
            ctx.closePath(); ctx.fill();
        } 
        else if (obs.type === 'platform') {
            // Plattform zeichnen
            ctx.fillStyle = '#4ee54e'; ctx.fillRect(obs.x, obs.y, obs.width, obs.height);
            ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.strokeRect(obs.x, obs.y, obs.width, obs.height);
        } 
        else if (obs.type === 'block') {
            ctx.fillStyle = '#f9d423';
            ctx.fillRect(obs.x, obs.y - obs.height, obs.width, obs.height);
            ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.strokeRect(obs.x, obs.y - obs.height, obs.width, obs.height);
        } 
        else if (obs.type === 'portal') {
            // Neon-Portal zeichnen
            let portalColor = obs.targetMode === 'ball' ? '#ff9f43' : '#00adb5';
            ctx.fillStyle = portalColor; ctx.globalAlpha = 0.3;
            ctx.fillRect(obs.x, obs.y, obs.width, obs.height); ctx.globalAlpha = 1.0;
            ctx.strokeStyle = portalColor; ctx.lineWidth = 4; ctx.strokeRect(obs.x, obs.y, obs.width, obs.height);
            
            ctx.fillStyle = '#fff'; ctx.font = '12px Arial';
            ctx.fillText(obs.targetMode.toUpperCase(), obs.x - 5, obs.y - 10);
        }

        // --- KOLLISIONS- UND LOGIKPRÜFUNG ---
        
        // Spezielle Plattform-Lande-Logik
        if (obs.type === 'platform') {
            if (player.x + player.size > obs.x && player.x < obs.x + obs.width) {
                // Steht der Spieler kurz über der Plattform und fällt nach unten?
                if (player.gravity > 0 && player.y + player.size >= obs.y && player.y + player.size - player.vy <= obs.y + 10) {
                    player.y = obs.y - player.size; player.vy = 0; player.isGrounded = true;
                    onAnyPlatform = true;
                }
                // Für den Ball an der Decke (umgedrehte Gravitation)
                if (player.gravity < 0 && player.y <= obs.y + obs.height && player.y - player.vy >= obs.y + obs.height - 10) {
                    player.y = obs.y + obs.height; player.vy = 0; player.isGrounded = true;
                    onAnyPlatform = true;
                }
            }
        }

        // Standard Kollision (Game Over) für tödliche Objekte
        if (obs.type === 'spike' || obs.type === 'block') {
            let collisionY = obs.type === 'spike' && obs.ceil ? obs.y : obs.y - obs.height;
            if (
                player.x < obs.x + obs.width &&
                player.x + player.size > obs.x &&
                player.y + player.size > collisionY &&
                player.y < (obs.type === 'spike' && obs.ceil ? obs.y + obs.height : obs.y)
            ) {
                if (!isGameOver) {
                    isGameOver = true;
                    if (pauseBtn) pauseBtn.style.display = "none";
                    sendScoreToServer(score);
                }
            }
        }

        // Portal-Berührung (Modus wechseln)
        if (obs.type === 'portal') {
            if (player.x < obs.x + obs.width && player.x + player.size > obs.x && player.y + player.size > obs.y && player.y < obs.y + obs.height) {
                if (player.mode !== obs.targetMode) {
                    player.mode = obs.targetMode;
                    // Reset der Gravitation in die richtige Richtung beim Wechsel
                    player.gravity = player.mode === 'ball' ? 0.5 : 0.6; 
                }
            }
        }

        // Score & Level-Berechnung
        if (!isPaused && obs.x + obs.width < player.x && !obs.passed) {
            obs.passed = true;
            score++;
            if (score % 5 === 0) {
                level++;
            }
        }

        if (obs.x < -obs.width) obstacles.splice(i, 1);
    }

    if (onAnyPlatform) player.isGrounded = true;

    // 5. UI Texte & Overlays
    ctx.fillStyle = '#fff'; ctx.font = 'bold 20px Arial';
    ctx.fillText(`Score: ${score}`, 20, 35);
    ctx.fillText(`Level: ${level}`, 150, 35);
    ctx.fillStyle = '#ff2e63';
    ctx.fillText(`Speed: ${(gameSpeed * 10).toFixed(0)} km/h`, canvas.width - 180, 35);

    if (isPaused) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#e67e22'; ctx.font = 'bold 36px Arial'; ctx.textAlign = 'center';
        ctx.fillText('PAUSIERT ⏸️', canvas.width / 2, canvas.height / 2 - 10);
        ctx.fillStyle = '#fff'; ctx.font = '16px Arial';
        ctx.fillText('Drücke ESC oder den Button zum Weiterspielen', canvas.width / 2, canvas.height / 2 + 25);
        ctx.textAlign = 'left';
    }

    if (isGameOver) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.8)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#ff2e63'; ctx.font = 'bold 36px Arial'; ctx.textAlign = 'center';
        ctx.fillText('GAME OVER', canvas.width / 2, canvas.height / 2 - 20);
        ctx.fillStyle = '#fff'; ctx.font = '18px Arial';
        ctx.fillText('Klicke hier zum Speichern & Neustarten', canvas.width / 2, canvas.height / 2 + 20);
        ctx.textAlign = 'left';
    }

    requestAnimationFrame(update);
}

spawnObstacle();
update();
