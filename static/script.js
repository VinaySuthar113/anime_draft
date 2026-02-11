let state = {
    username: "",
    mode: null,
    room: null,
    team: null,
    currentTurn: false,
    drawnCard: null
};

const roles = ["Captain","Vice","Tank","Healer","Support1","Support2"];

let gameInterval = null;
let resultShown = false;
let swapPopupShown = false;
let swapSelection = [];


/* =======================================================
   SCREEN CONTROL
======================================================= */

function showScreen(id){
    document.querySelectorAll(".screen")
        .forEach(s => s.classList.remove("active"));
    document.getElementById(id).classList.add("active");
}


/* =======================================================
   USERNAME
======================================================= */

function enterUsername(){
    const name = document.getElementById("usernameInput").value.trim();
    if(!name) return;
    state.username = name;
    showScreen("modeScreen");
}


/* =======================================================
   MODE
======================================================= */

function selectMode(mode){
    state.mode = mode;
    if(mode === "2p"){
        document.getElementById("displayName").innerText = state.username;
        showScreen("roomScreen");
    }
}


/* =======================================================
   ROOM
======================================================= */

async function createRoom(){
    const res = await fetch("/api/create",{method:"POST"});
    const data = await res.json();
    if(data.error) return alert(data.error);

    state.room = data.room;
    state.team = data.team;

    document.getElementById("roomCodeDisplay").innerText = state.room;
    pollRoom();
}

async function joinRoom(){
    const code = document.getElementById("roomInput").value.trim();
    if(!code) return;

    const res = await fetch("/api/join",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ room:code, username:state.username })
    });

    const data = await res.json();
    if(data.error) return alert(data.error);

    state.room = data.room;
    state.team = data.team;

    pollRoom();
}

async function pollRoom(){
    const interval = setInterval(async ()=>{
        const res = await fetch(`/api/state/${state.room}/${state.team}`);
        const data = await res.json();

        if(data.opponent_joined){
            clearInterval(interval);
            startCountdown();
        }
    },1000);
}

function startCountdown(){
    let seconds = 5;
    const el = document.getElementById("countdown");

    const timer = setInterval(()=>{
        el.innerText = "Starting in: " + seconds;
        seconds--;
        if(seconds < 0){
            clearInterval(timer);
            startGame();
        }
    },1000);
}


/* =======================================================
   GAME
======================================================= */

function startGame(){
    showScreen("gameScreen");
    pollGameState();
}

async function pollGameState(){

    if(gameInterval) clearInterval(gameInterval);

    gameInterval = setInterval(async ()=>{

        const res = await fetch(`/api/state/${state.room}/${state.team}`);
        const data = await res.json();

        state.currentTurn = data.your_turn;

        const indicator = document.getElementById("turnIndicator");

        if(state.currentTurn){
            indicator.innerText="Your Turn - Draw a Card";
            indicator.className="your-turn";
        } else {
            indicator.innerText="Opponent's Turn";
            indicator.className="opponent-turn";
        }

        renderSlots(data.your_team);

        /* -------- SWAP PHASE -------- */

        if(data.phase === "SWAP_OPTIONAL" && !swapPopupShown){
            swapPopupShown = true;

            if(data.skip_available){
                showSwapPopup(data.your_team);
            } else {
                // player has no swap → auto mark decision
                await fetch(`/api/swap/${state.room}`,{
                    method:"POST",
                    headers:{"Content-Type":"application/json"},
                    body:JSON.stringify({
                        team:state.team,
                        skip:true
                    })
                });
            }
        }

        /* -------- RESULT PHASE -------- */

        if(data.phase === "RESULT" && !resultShown){
            resultShown = true;
            clearInterval(gameInterval);
            showResult();
        }

    },1000);
}


/* =======================================================
   DRAW
======================================================= */

async function drawCard(){

    if(!state.currentTurn) return;

    const res = await fetch(`/api/draw/${state.room}/${state.team}`);
    const data = await res.json();
    if(data.error) return alert(data.error);

    state.drawnCard = data;

    const card = document.getElementById("drawnCard");
    card.style.backgroundImage = `url(${data.image})`;
    card.innerHTML = `<div class="card-name">${data.name}</div>`;
    card.classList.remove("hidden");
}


/* =======================================================
   RENDER TEAM
======================================================= */

function renderSlots(team){

    const row = document.getElementById("myTeam");
    row.innerHTML = "";

    roles.forEach((role,i)=>{

        const slot = document.createElement("div");
        slot.className = "card slot";

        if(team[i]){
            slot.style.backgroundImage = `url(${team[i].image})`;
            slot.innerHTML = `<div class="card-name">${team[i].name}</div>`;
        }
        else{
            slot.innerHTML = `<div class="role-label">${role}</div>`;

            if(state.drawnCard && state.currentTurn){
                slot.classList.add("assignable");
                slot.onclick = ()=>assignToSlot(i);
            }
        }

        row.appendChild(slot);
    });
}


/* =======================================================
   ASSIGN
======================================================= */

async function assignToSlot(index){

    if(!state.drawnCard) return;

    const res = await fetch(`/api/assign/${state.room}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ team:state.team, slot:index })
    });

    const data = await res.json();
    if(data.error) return alert(data.error);

    state.drawnCard = null;

    const card = document.getElementById("drawnCard");
    card.classList.add("hidden");
    card.innerHTML = "";
}


/* =======================================================
   SWAP
======================================================= */

function showSwapPopup(team){

    const popup = document.getElementById("swapPopup");
    const container = document.getElementById("swapOptions");

    container.innerHTML = "";
    swapSelection = [];

    roles.forEach((role,i)=>{
        const div = document.createElement("div");
        div.className="card slot";
        div.style.backgroundImage = `url(${team[i].image})`;
        div.innerHTML = `<div class="card-name">${team[i].name}</div>`;

        div.onclick = ()=>{
            if(swapSelection.includes(i)) return;

            if(swapSelection.length < 2){
                swapSelection.push(i);
                div.style.outline="3px solid #ff00ff";
            }
        };

        container.appendChild(div);
    });

    popup.classList.remove("hidden");
}

async function confirmSwap(){

    if(swapSelection.length !== 2){
        alert("Select two cards to swap");
        return;
    }

    await fetch(`/api/swap/${state.room}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            team:state.team,
            slot1:swapSelection[0],
            slot2:swapSelection[1]
        })
    });

    document.getElementById("swapPopup").classList.add("hidden");
}

async function skipSwap(){

    await fetch(`/api/swap/${state.room}`,{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            team:state.team,
            skip:true
        })
    });

    document.getElementById("swapPopup").classList.add("hidden");
}


/* =======================================================
   RESULT
======================================================= */

async function showResult(){

    const res = await fetch(`/api/result/${state.room}`);
    const data = await res.json();

    const box = document.getElementById("resultContent");
    box.innerHTML = "";

    for(let r of data.rounds){

        box.innerHTML += `
            <div style="margin-bottom:20px;">
                <strong>${r.role}</strong><br>
                ${r.A_name} (${r.A_power}) vs 
                ${r.B_name} (${r.B_power})<br>
                Winner: <b>${r.winner}</b>
            </div>
        `;
    }

    box.innerHTML += `<h2>🏆 Final Winner: ${data.final_winner}</h2>`;

    document.getElementById("resultPopup").classList.remove("hidden");
}


/* =======================================================
   RESTART
======================================================= */

function restartGame(){
    location.reload();
}