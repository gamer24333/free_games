const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const pauseBtn = document.getElementById('pauseBtn');
const bgMusic = document.getElementById('gdMusic');

let gameSpeed = 5;
let score = 0;
let level = 1;
let isGameOver = false;
let isPaused = false;      
let gameStarted = false;   
const floorY = 340;
const ceilingY = 60; 

const player = {
    x: 80, y: 300, size: 35, vy: 0,
    gravity: 0.6, jumpForce: -11.5, isGrounded: false, rotation: 0,
    mode: 'cube' 
};

let obstacles = [];
let spawnTimeout;
let reloadTimeout = null;
let runId = 0;

if (bgMusic) {
    bgMusic.volume = 0.2;
}

function doJump() {
    if (isPaused) return; 
    
    if (isGameOver) {
        resetGame();
        return; 
    }

    if (!gameStarted) {
        gameStarted = true;
        if (pauseBtn) pauseBtn.style.display = "inline-block"; 
        
        if (bgMusic && bgMusic.paused) {
            bgMusic.play().catch(e => console.log("Musik-Autoplay blockiert:", e));
        }
    }

    // Sprung direkt ausführen!
    if (player.mode === 'cube') {
        if (player.isGrounded) {
            player.vy = player.jumpForce;
            player.isGrounded = false;
        }
    } else if (player.mode === 'ball') {
        // Beim Ball dreht sich die Schwerkraft um
        player.gravity = -player.gravity;
        player.isGrounded = false;
    }
}

function togglePause() {
    if (!gameStarted || isGameOver) return; 
    isPaused = !isPaused;
    
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
    if (e.code === 'Space' || e.code === 'Enter') { e.preventDefault(); doJump(); } 
    if (e.code === 'Escape' || e.key === 'p' || e.key === 'P') { e.preventDefault(); togglePause(); }
});
canvas.addEventListener('touchstart', (e) => { e.preventDefault(); doJump(); }, { passive: false });
canvas.addEventListener('mousedown', (e) => { e.preventDefault(); doJump(); });

if (pauseBtn) pauseBtn.addEventListener('click', togglePause);

// Musik stoppen, wenn man die Seite verlässt
document.querySelectorAll('.btn-back').forEach(btn => {
    btn.addEventListener('click', () => {
        if (bgMusic) bgMusic.pause();
    });
});

function spawnObstacle() {
    if (isGameOver) return;
    if (isPaused || !gameStarted) {
        spawnTimeout = setTimeout(spawnObstacle, 200);
        return;
    }

    let rand = Math.random();
    
    // --- PORTAL-LOGIK & HINDERNISSE ---
    if (player.mode === 'ball') {
        // Wenn man ein Ball ist, gibt es eine Chance von 30%, dass ein Würfel-Portal kommt
        if (rand < 0.30) {
            obstacles.push({ x: canvas.width, y: floorY - 100, width: 30, height: 100, type: 'portal', targetMode: 'cube' });
        } 
        else if (rand < 0.65) {
            let onCeiling = Math.random() > 0.5;
            obstacles.push({ 
                x: canvas.width, 
                y: onCeiling ? ceilingY : floorY, 
                width: 30, height: 35, 
                type: 'spike',
                ceil: onCeiling
            });
        } 
        else {
            let onCeiling = Math.random() > 0.5;
            obstacles.push({
                x: canvas.width,
                y: onCeiling ? ceilingY + 35 : floorY,
                width: 35, height: 35, type: 'block',
                ceil: onCeiling
            });
        }
    } 
    else {
        // Als WÜRFEL (Cube)
        if (rand < 0.15 && score > 5) {
            // Ball-Portal (Orange) - kommt erst ab Score 5
            obstacles.push({ x: canvas.width, y: floorY - 100, width: 30, height: 100, type: 'portal', targetMode: 'ball' });
        }
        else if (rand < 0.40) {
            // Einzelner Stachel auf dem Boden
            obstacles.push({ x: canvas.width, y: floorY, width: 30, height: 35, type: 'spike', ceil: false });
        } 
        else if (rand < 0.65) {
            // Treppen-Plattformen
            let height1 = floorY - 65;
            let height2 = floorY - 110; 
            
            obstacles.push({ x: canvas.width, y: height1, width: 90, height: 20, type: 'platform', mustTouch: false });
            obstacles.push({ x: canvas.width + 140, y: height2, width: 90, height: 20, type: 'platform', mustTouch: false });
            
            // Stacheln darunter (nur auf dem Boden)
            obstacles.push({ x: canvas.width + 30, y: floorY, width: 30, height: 35, type: 'spike', ceil: false });
            obstacles.push({ x: canvas.width + 90, y: floorY, width: 30, height: 35, type: 'spike', ceil: false });
            obstacles.push({ x: canvas.width + 150, y: floorY, width: 30, height: 35, type: 'spike', ceil: false });
        } 
        else {
            // Einzelner Block auf dem Boden
            obstacles.push({ x: canvas.width, y: floorY, width: 35, height: 35, type: 'block', ceil: false });
        }
    }

    // Wenn ein Cube-Portal spawnt, längere Pause machen, damit man sich vorbereiten kann
    let nextSpawn = (rand >= 0.30 && rand < 0.65 && player.mode === 'cube') ? 2200 : (1000 + Math.random() * 1200);
    spawnTimeout = setTimeout(spawnObstacle, nextSpawn / (gameSpeed / 5));
}

async function sendScoreToServer(finalScore, currentRunId) {
    try {
        const response = await fetch('/api/submit-score', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ score: finalScore })
        });
        if (response.ok) {
            if (runId === currentRunId && isGameOver) {
                reloadTimeout = setTimeout(() => {
                    if (runId === currentRunId && isGameOver) {
                        window.location.reload();
                    }
                }, 1500);
            }
        }
    } catch (e) { console.error("Score-Übertragungsfehler", e); }
}

function triggerGameOver() {
    if (isGameOver) return;
    isGameOver = true;
    gameStarted = false;
    
    if (pauseBtn) pauseBtn.style.display = "none";
    if (bgMusic) {
        bgMusic.pause();
        bgMusic.currentTime = 0;
    }
    
    runId++;
    sendScoreToServer(score, runId);
}

function resetGame() {
    runId++; 
    if (reloadTimeout) {
        clearTimeout(reloadTimeout);
        reloadTimeout = null;
    }

    clearTimeout(spawnTimeout);
    obstacles = [];
    score = 0; level = 1; gameSpeed = 5;
    player.mode = 'cube';
    player.gravity = 0.6; // Normale Gravitation
    player.y = floorY - player.size; player.vy = 0; player.rotation = 0;
    
    isGameOver = false; 
    isPaused = false; 
    gameStarted = false; 
    
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
        gameSpeed += 0.0018; 

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
        if (!isGameOver && !isPaused && gameStarted) obs.x -= gameSpeed;

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
            ctx.fillStyle = obs.mustTouch ? '#2ecc71' : '#4ee54e'; 
            ctx.fillRect(obs.x, obs.y, obs.width, obs.height);
            ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.strokeRect(obs.x, obs.y, obs.width, obs.height);
            
            if (obs.mustTouch) {
                ctx.fillStyle = '#fff'; ctx.font = '9px Arial';
                ctx.fillText("HIER DRAUF!", obs.x + 18, obs.y + 13);
            }
        } 
        else if (obs.type === 'block') {
            ctx.fillStyle = '#f9d423';
            if (obs.ceil) {
                ctx.fillRect(obs.x, obs.y, obs.width, obs.height);
                ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.strokeRect(obs.x, obs.y, obs.width, obs.height);
            } else {
                ctx.fillRect(obs.x, obs.y - obs.height, obs.width, obs.height);
                ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.strokeRect(obs.x, obs.y - obs.height, obs.width, obs.height);
            }
        } 
        else if (obs.type === 'portal') {
            // Grünes Portal = Cube, Oranges Portal = Ball
            let portalColor = obs.targetMode === 'ball' ? '#ff9f43' : '#39ff14';
            ctx.fillStyle = portalColor; ctx.globalAlpha = 0.3;
            ctx.fillRect(obs.x, obs.y, obs.width, obs.height); ctx.globalAlpha = 1.0;
            ctx.strokeStyle = portalColor; ctx.lineWidth = 4; ctx.strokeRect(obs.x, obs.y, obs.width, obs.height);
            
            ctx.fillStyle = '#fff'; ctx.font = '14px Arial';
            ctx.fillText(obs.targetMode.toUpperCase(), obs.x - 6, obs.y - 10);
        }
        
        // Plattform Kollision (Verbessert: Man prallt seltener unfair ab)
        if (obs.type === 'platform') {
            if (player.x + player.size > obs.x + 5 && player.x < obs.x + obs.width - 5) {
                // Landung von oben
                if (player.y + player.size >= obs.y && player.y + player.size - player.vy <= obs.y + 15) {
                    player.y = obs.y - player.size; player.vy = 0; player.isGrounded = true;
                    onAnyPlatform = true;
                    if (obs.mustTouch) obs.touched = true; 
                }
                // Landung an der Decke (nur als Ball)
                if (player.mode === 'ball' && player.y <= obs.y + obs.height && player.y - player.vy >= obs.y + obs.height - 15) {
                    player.y = obs.y + obs.height; player.vy = 0; player.isGrounded = true;
                    onAnyPlatform = true;
                    if (obs.mustTouch) obs.touched = true; 
                }
            }
        }

        if (obs.type === 'platform' && obs.mustTouch && !isGameOver) {
            if (obs.x + obs.width < player.x && !obs.touched) {
                triggerGameOver();
            }
        }

        // Hitbox Kollision für Tod
        if (obs.type === 'spike' || obs.type === 'block') {
            let collisionMinY, collisionMaxY;
            
            if (obs.type === 'spike') {
                collisionMinY = obs.ceil ? obs.y : obs.y - obs.height + 5; // Hitbox verkleinert für Fairness
                collisionMaxY = obs.ceil ? obs.y + obs.height - 5 : obs.y;
            } else { 
                collisionMinY = obs.ceil ? obs.y : obs.y - obs.height;
                collisionMaxY = obs.ceil ? obs.y + obs.height : obs.y;
            }

            if (
                player.x < obs.x + obs.width - 4 &&
                player.x + player.size > obs.x + 4 &&
                player.y + player.size > collisionMinY &&
                player.y < collisionMaxY
            ) {
                triggerGameOver();
            }
        }

        // Durch Portal fliegen
        if (obs.type === 'portal') {
            if (player.x < obs.x + obs.width && player.x + player.size > obs.x && player.y + player.size > obs.y && player.y < obs.y + obs.height) {
                if (player.mode !== obs.targetMode) {
                    player.mode = obs.targetMode;
                    // Gravitation richtig einstellen (beim Cube immer nach unten)
                    if (player.mode === 'cube') {
                        player.gravity = 0.6;
                        if (player.vy < 0) player.vy = 0; // Kein hochfliegen in die Decke nach Verwandlung
                    } else {
                        player.gravity = 0.5; 
                    }
                }
            }
        }

        if (!isPaused && gameStarted && obs.x + obs.width < player.x && !obs.passed) {
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

    if (!gameStarted && !isGameOver) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.4)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#00adb5'; ctx.font = 'bold 28px Arial'; ctx.textAlign = 'center';
        ctx.fillText('KLICKE ODER LEERTASTE ZUM STARTEN', canvas.width / 2, canvas.height / 2);
        ctx.textAlign = 'left';
    }
    else if (isPaused) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)'; ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#e67e22'; ctx.font = 'bold 36px Arial'; ctx.textAlign = 'center';
        ctx.fillText('PAUSIERT ⏸️', canvas.width / 2, canvas.height / 2 - 10);
        ctx.fillStyle = '#fff'; ctx.font = '16px Arial';
        ctx.fillText('Drücke ESC oder den Button zum Weiterspielen', canvas.width / 2, canvas.height / 2 + 25);
        ctx.textAlign = 'left';
    }
    else if (isGameOver) {
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
