const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const pauseBtn = document.getElementById('pauseBtn');
const bgMusic = document.getElementById('gdMusic'); // Musik-Element holen

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

// Lautstärke-Einstellung (0.2 = 20%, damit es angenehm im Hintergrund läuft)
if (bgMusic) {
    bgMusic.volume = 0.2;
}

function doJump() {
    if (isPaused) return; 
    
    if (!gameStarted && !isGameOver) {
        gameStarted = true;
        if (pauseBtn) pauseBtn.style.display = "inline-block"; 
        
        // MUSIK-START: Sobald das Spiel beim ersten Klick beginnt
        if (bgMusic && bgMusic.paused) {
            bgMusic.play().catch(e => console.log("Musik-Autoplay blockiert:", e));
        }
    }

    if (!isGameOver) {
        if (player.mode === 'cube') {
            if (player.isGrounded) {
                player.vy = player.jumpForce;
                player.isGrounded = false;
            }
        } else if (player.mode === 'ball') {
            player.gravity = -player.gravity;
            player.isGrounded = false;
        }
    }
    
    if (isGameOver) resetGame();
}

function togglePause() {
    if (!gameStarted || isGameOver) return; 
    isPaused = !isPaused;
    
    // MUSIK PAUSIEREN / WEITERSPIELEN
    if (bgMusic) {
        if (isPaused) {
            bgMusic.pause();
        } else {
            bgMusic.play().catch(e => console.log(e));
        }
    }

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

    let rand = Math.random();
    
    // Erhöhte Schwierigkeit, wenn der Spieler im Ball-Modus ist
    if (player.mode === 'ball') {
        if (rand < 0.40) {
            // Variante 1: Decken- oder Bodenstachel (50/50 Chance)
            let onCeiling = Math.random() > 0.5;
            obstacles.push({ 
                x: canvas.width, 
                y: onCeiling ? ceilingY : floorY, 
                width: 30, height: 35, 
                type: 'spike',
                ceil: onCeiling
            });
        } else if (rand < 0.75) {
            // Variante 2: Mittige GEMEINE grüne Pflicht-Plattform
            let heightLevel = floorY - 110; 
            obstacles.push({
                x: canvas.width,
                y: heightLevel,
                width: 100, height: 20, 
                type: 'platform',
                mustTouch: true, // Markiert als Pflicht-Plattform für den Ball
                touched: false
            });
        } else {
            // Variante 3: Gelbe Blöcke am Boden oder hängend
            let onCeiling = Math.random() > 0.5;
            obstacles.push({
                x: canvas.width,
                y: onCeiling ? ceilingY + 35 : floorY,
                width: 35, height: 35, type: 'block',
                ceil: onCeiling
            });
        }
    } else {
        // Normaler Cube-Modus (unverändert)
        if (rand < 0.35) {
            obstacles.push({ x: canvas.width, y: floorY, width: 30, height: 35, type: 'spike', ceil: false });
        } else if (rand < 0.65) {
            let heightLevel = floorY - 70 - Math.floor(Math.random() * 2) * 50;
            obstacles.push({ x: canvas.width, y: heightLevel, width: 90, height: 20, type: 'platform', mustTouch: false });
        } else if (rand < 0.85) {
            obstacles.push({ x: canvas.width, y: floorY, width: 35, height: 35, type: 'block' });
        } else {
            let nextMode = 'ball';
            obstacles.push({ x: canvas.width, y: floorY - 100, width: 30, height: 100, type: 'portal', targetMode: nextMode });
        }
    }

    let nextSpawn = 900 + Math.random() * 1200; // Etwas schnellerer Spawn für mehr Action
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
    
    if (bgMusic) {
        bgMusic.pause();
        bgMusic.currentTime = 0;
    }

    spawnObstacle();
}

function update() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = '#0f111a'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.strokeStyle = 'rgba(0, 173, 185, 0.05)'; ctx.lineWidth = 2;
    let gridSize = 40;
    let offset = gameStarted && !isPaused && !isGameOver ? (Date.now() / 20) % gridSize : 0;
    for (let x = -offset; x < canvas.width; x += gridSize) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }

    ctx.fillStyle = '#161925'; ctx.fillRect(0, floorY, canvas.width, canvas.height - floorY);
    ctx.strokeStyle = '#00adb5'; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.moveTo(0, floorY); ctx.lineTo(canvas.width, floorY); ctx.stroke();

    if (player.mode === 'ball') {
        ctx.fillStyle = '#161925'; ctx.fillRect(0, 0, canvas.width, ceilingY);
        ctx.beginPath(); ctx.moveTo(0, ceilingY); ctx.lineTo(canvas.width, ceilingY); ctx.stroke();
    }

    if (!isPaused && gameStarted && !isGameOver) {
        player.vy += player.gravity;
        player.y += player.vy;
        gameSpeed += 0.0018; // Speed zieht minimal schneller an

        if (player.y >= floorY - player.size) {
            player.y = floorY - player.size; player.vy = 0; player.isGrounded = true;
            if (player.mode === 'cube') {
                player.rotation = Math.round(player.rotation / (Math.PI / 2)) * (Math.PI / 2);
            }
        } 
        else if (player.mode === 'ball' && player.y <= ceilingY) {
            player.y = ceilingY; player.vy = 0; player.isGrounded = true;
        } else {
            player.isGrounded = false;
        }

        if (!player.isGrounded) {
            player.rotation += (player.gravity > 0 ? 0.09 : -0.09);
        } else if (player.mode === 'ball') {
            player.rotation += 0.05 * (gameSpeed / 5); 
        }
    }

    ctx.save();
    ctx.translate(player.x + player.size/2, player.y + player.size/2);
    ctx.rotate(player.rotation);
    
    if (player.mode === 'cube') {
        ctx.fillStyle = '#00adb5'; ctx.fillRect(-player.size/2, -player.size/2, player.size, player.size);
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.strokeRect(-player.size/2, -player.size/2, player.size, player.size);
        ctx.fillStyle = '#222831'; ctx.fillRect(-player.size/4, -player.size/4, player.size/2, player.size/2);
    } else {
        ctx.fillStyle = '#ff9f43'; ctx.beginPath(); ctx.arc(0, 0, player.size/2, 0, Math.PI*2); ctx.fill();
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.stroke();
        ctx.beginPath(); ctx.moveTo(-player.size/2, 0); ctx.lineTo(player.size/2, 0); ctx.stroke();
    }
    ctx.restore();

    let onAnyPlatform = false;

    for (let i = obstacles.length - 1; i >= 0; i--) {
        let obs = obstacles[i];
        if (!isGameOver && !isPaused) obs.x -= gameSpeed;

        // --- ZEICHNEN ---
        if (obs.type === 'spike') {
            ctx.fillStyle = '#ff2e63';
            ctx.beginPath();
            if (obs.ceil) { 
                ctx.moveTo(obs.x, obs.y);
                ctx.lineTo(obs.x + obs.width/2, obs.y + obs.height);
                ctx.lineTo(obs.x + obs.width, obs.y);
            } else { 
                ctx.moveTo(obs.x, obs.y);
                ctx.lineTo(obs.x + obs.width/2, obs.y - obs.height);
                ctx.lineTo(obs.x + obs.width, obs.y);
            }
            ctx.closePath(); ctx.fill();
        } 
        else if (obs.type === 'platform') {
            // Zeige Pflicht-Plattformen in hellem Neongrün, normale in Standardgrün
            ctx.fillStyle = obs.mustTouch ? '#2ecc71' : '#4ee54e'; 
            ctx.fillRect(obs.x, obs.y, obs.width, obs.height);
            ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.strokeRect(obs.x, obs.y, obs.width, obs.height);
            
            // Kleiner optischer Indikator für Pflicht-Inseln
            if (obs.mustTouch) {
                ctx.fillStyle = '#fff'; ctx.font = '9px Arial';
                ctx.fillText("HIER DRAUF!", obs.x + 18, obs.y + 13);
            }
        } 
        else if (obs.type === 'block') {
            ctx.fillStyle = '#f9d423';
            let blockY = obs.ceil ? obs.y - obs.height : obs.y - obs.height;
            if (obs.ceil) {
                ctx.fillRect(obs.x, obs.y, obs.width, obs.height);
                ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.strokeRect(obs.x, obs.y, obs.width, obs.height);
            } else {
                ctx.fillRect(obs.x, obs.y - obs.height, obs.width, obs.height);
                ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.strokeRect(obs.x, obs.y - obs.height, obs.width, obs.height);
            }
        } 
        else if (obs.type === 'portal') {
            let portalColor = obs.targetMode === 'ball' ? '#ff9f43' : '#00adb5';
            ctx.fillStyle = portalColor; ctx.globalAlpha = 0.3;
            ctx.fillRect(obs.x, obs.y, obs.width, obs.height); ctx.globalAlpha = 1.0;
            ctx.strokeStyle = portalColor; ctx.lineWidth = 4; ctx.strokeRect(obs.x, obs.y, obs.width, obs.height);
            
            ctx.fillStyle = '#fff'; ctx.font = '12px Arial';
            ctx.fillText(obs.targetMode.toUpperCase(), obs.x - 5, obs.y - 10);
        }
        
        // --- LOGIK & BERÜHRUNGEN DER PLATTFORMEN ---
        if (obs.type === 'platform') {
            if (player.x + player.size > obs.x && player.x < obs.x + obs.width) {
                // Landung von oben (Gravitation normal)
                if (player.y + player.size >= obs.y && player.y + player.size - player.vy <= obs.y + 12) {
                    player.y = obs.y - player.size; player.vy = 0; player.isGrounded = true;
                    onAnyPlatform = true;
                    if (obs.mustTouch) obs.touched = true; // Pflicht erfüllt!
                }
                // Landung von unten (Ball an Decke/Plattform-Unterseite kleben)
                if (player.y <= obs.y + obs.height && player.y - player.vy >= obs.y + obs.height - 12) {
                    player.y = obs.y + obs.height; player.vy = 0; player.isGrounded = true;
                    onAnyPlatform = true;
                    if (obs.mustTouch) obs.touched = true; // Pflicht erfüllt!
                }
            }
        }

        // --- SCHWERE PFLICHT-REGEL: Verpasst man die grüne Plattform im Ball-Modus -> Tod! ---
        if (obs.type === 'platform' && obs.mustTouch && !isGameOver) {
            // Sobald die Plattform am Spieler vorbei gezogen ist
            if (obs.x + obs.width < player.x && !obs.touched) {
                isGameOver = true;
                if (pauseBtn) pauseBtn.style.display = "none";
                if (bgMusic) bgMusic.pause();
                sendScoreToServer(score);
            }
        }

        // --- STANDARD KOLLISIONEN (STACHELN & BLÖCKE) ---
        if (obs.type === 'spike' || obs.type === 'block') {
            let collisionMinY, collisionMaxY;
            
            if (obs.type === 'spike') {
                collisionMinY = obs.ceil ? obs.y : obs.y - obs.height;
                collisionMaxY = obs.ceil ? obs.y + obs.height : obs.y;
            } else { // Block
                collisionMinY = obs.ceil ? obs.y : obs.y - obs.height;
                collisionMaxY = obs.ceil ? obs.y + obs.height : obs.y;
            }

            if (
                player.x < obs.x + obs.width &&
                player.x + player.size > obs.x &&
                player.y + player.size > collisionMinY &&
                player.y < collisionMaxY
            ) {
                if (!isGameOver) {
                    isGameOver = true;
                    if (pauseBtn) pauseBtn.style.display = "none";
                    if (bgMusic) bgMusic.pause();
                    sendScoreToServer(score);
                }
            }
        }

        // --- PORTAL WECHSEL ---
        if (obs.type === 'portal') {
            if (player.x < obs.x + obs.width && player.x + player.size > obs.x && player.y + player.size > obs.y && player.y < obs.y + obs.height) {
                if (player.mode !== obs.targetMode) {
                    player.mode = obs.targetMode;
                    player.gravity = player.mode === 'ball' ? 0.5 : 0.6; 
                }
            }
        }

        // --- SCORE-ZÄHLUNG & LEVEL UP ---
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
