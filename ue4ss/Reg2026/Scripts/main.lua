-- Reg2026 : Straight Mode pour toute la grille.
--
-- 1. Zones : au chargement d'un circuit, ajoute les zones Straight Mode (zones.lua) aux zones DRS du jeu
--    (début et fin seulement : un point de détection ajouté provoque un drapeau rouge). Le jeu enchaîne
--    sur une zone ajoutée quand aucun point de détection ne la précède.
-- 2. Règlement 2026 dans la simulation : Reg2026Patch.dll (tools_native/reg2026patch.cpp).
--    Straight Mode : toute la grille a le DRS dans les zones dès le 1er tour, ouvert par le jeu lui-même
--    avec son vrai gain de vitesse (blocages restants : voiture de sécurité, drapeaux, pluie).
--    Overtake Mode : à moins d'1 s au point de détection, +12,5 % de batterie ERS (0,5 MJ sur 4 MJ),
--    une fois par tour. Le DRS mod et le bandeau des pilotes suivent l'état du jeu.
-- 3. Mesure : à la sortie de chaque zone, une ligne dans Mods/Reg2026/mesures.csv (vitesses d'entrée et max,
--    Straight Mode actif ou non, état DRS le plus haut avant / dans la zone, « jeu » si le DRS a été ouvert).
-- 4. Les cases STRAIGHT / OVERTAKE sont dans le bandeau des pilotes (pak zzz_Reg2026UI_P, scripts/build_ui.py) ;
--    ici seulement un message temporaire au changement de mode.
--
-- 5. Limite 2026 (plus de déploiement au-delà de 290 km/h, 337 en Overtake Mode) toujours active ; super clipping
--    (optionnel : recharge au-dessus de la limite) : Reg2026Patch.dll lit superclipping.ini (actif=0/1 et seuils) ;
--    F6 bascule actif.
--
-- Touches : F7 règlement 2026 / règle d'origine du jeu (DRS à moins d'1 s) ; F6 super clipping.
local UEHelpers = require("UEHelpers")
local ZONES = require("zones")

local CAR_TICK = "/Game/Cars/BaseCars/BaseCar2022/BP_BaseCar2022_Actor.BP_BaseCar2022_Actor_C:ReceiveTick"
local HUD_REFRESH = 0.2   -- secondes
local TRACK_CHECK = 2.0   -- secondes entre deux recherches du circuit chargé
local TOAST_TIME = 3.0    -- durée du message F7
local HOOK_RETRY = 250    -- ms : s'enregistrer avant le DRS mod
local MOD_DIR = "ue4ss/Mods/Reg2026/"
local OFF_FILE = MOD_DIR .. "straight_off.txt"   -- lu par Reg2026Patch.dll
local CSV_FILE = MOD_DIR .. "mesures.csv"
local CLIP_FILE = MOD_DIR .. "superclipping.ini"  -- lu par Reg2026Patch.dll
local CARSTATS_FILE = MOD_DIR .. "carstats.txt"    -- adresse du CarStatsDataAsset, lu par Reg2026Patch.dll
local CLIP_DEFAULT = "actif=1\nvitesse_max=290\nvitesse_max_overtake=337\nrecharge=0.002\novertake_vitesse_min=250\novertake_distance=2000\novertake_ecart_attaque=0.6\novertake_batterie=1\novertake_batterie_max=0.20\ndeploiement_boost=0.40\ndeploiement_equilibre=0.60\n"

-- EDRSState
local DRS_DISABLED, DRS_DETECTED, DRS_ENABLED, DRS_ACTIVE = 0, 1, 2, 3

local WHITE           = { R = 1, G = 1, B = 1, A = 1 }
local COLOR_ON        = { R = 0.05, G = 0.55, B = 0.15, A = 0.95 }
local COLOR_WARN      = { R = 0.60, G = 0.10, B = 0.10, A = 0.95 }

local function fileExists(path)
    local f = io.open(path, "r")
    if f then f:close() end
    return f ~= nil
end

local straightOn = not fileExists(OFF_FILE)
local hud = nil
local ui = {}            -- éléments du HUD
local toastUntil = 0
local lastHud, lastTrackCheck = 0, -TRACK_CHECK

local track = nil        -- { name, nodes, zones = { {s, e, added, index}, ... } }
local patchedComp = nil  -- adresse du RaceSimTrackComponent déjà complété
local cars = {}          -- [adresse voiture] = état

local function log(msg) print("[Reg2026] " .. msg .. "\n") end

local logged = {}
local function logOnce(msg)
    if logged[msg] then return end
    logged[msg] = true
    log(msg)
end

---------------------------------------------------------------------------
-- Valeurs 2026 écrites en mémoire dans les data assets chargés
---------------------------------------------------------------------------
-- Le pak zzz_Reg2026_P ne gagne pas toujours : un autre mod qui contient les mêmes assets (RRacingV5 par
-- exemple) peut passer devant, et nos valeurs ne sont alors jamais lues. On les écrit donc aussi directement
-- dans les objets chargés, champ par champ : les autres réglages de l'autre mod restent en place.
-- Mêmes valeurs que scripts/patch_2026.py. Mesuré à Monza : sans RRacingV5, les valeurs sont bien en mémoire.
local VALUES = {
    { "/Game/RaceSim/RaceSimDataAsset.RaceSimDataAsset", {
        { "ERSAccelDeployBatteryRate", -0.10 },
        { "ERSBrakingChargeBatteryRate", 0.0875 },  -- 350 kW (0,12 gardait la batterie pleine)
        { "ERSAccelerationMultiplier_Inactive", 0.75 },  -- temps 2026 à Monza (0,66 : 1:29.0 de médiane, 0,80 : 1:24.9)
        { "ERSWearRate", 15.0 },
        { "SlipstreamAccelerationMultiplier", 1.10 },
        { "DirtyAirMaxDist", 150.0 },
        { "OvertakeData.OvertakeAssistOvertakeDifficultyModifier", 0.25 },
        { "OvertakeData.SlipstreamTimeToOvertake", 1.5 },
        { "OvertakeData.OvertakeMaxStartDistance", 50.0 },
    } },
    { "/Game/RaceSim/DriverTacticsDataAsset.DriverTacticsDataAsset", {
        { "ERSDeployBudget", 0.80 },
    } },
    { "/Game/SharedAssets/DataAssets/CarStatsDataAsset.CarStatsDataAsset", {
        { "CarStatWeights.TopSpeedWeights.PowerWeight", 0.15 },
        { "CarStatWeights.TopSpeedWeights.DragReductionWeight", 0.85 },
        { "CarStatWeights.AccelerationWeights.PowerWeight", 0.6 },
        { "CarStatWeights.AccelerationWeights.DragReductionWeight", 0.4 },
        -- AeroSpeedMultipliers et DirtyAirSpeedMultipliers (tableaux fixes de 3 FVector2D) : UE4SS ne sait pas
        -- les indexer. L'adresse de l'objet est écrite dans carstats.txt et Reg2026Patch.dll les écrit
        -- (mesuré à Monza : +0x1C0 et +0x200 dans l'objet).
        { "CarStatRanges.DRSTopSpeedMultiplier", { 1.03, 1.06 } },
        { "CarStatRanges.DRSAccelerationMultiplier", { 1.05, 1.20 } },
    } },
}

--- renvoie le conteneur et la clé finale d'un chemin « A.B[2].C »
local function resolve(obj, path)
    local parts = {}
    for p in path:gmatch("[^%.]+") do parts[#parts + 1] = p end
    local cur = obj
    for i = 1, #parts - 1 do
        local name, idx = parts[i]:match("^(.-)%[(%d+)%]$")
        if name then cur = cur[name][tonumber(idx)] else cur = cur[parts[i]] end
    end
    local last = parts[#parts]
    local name, idx = last:match("^(.-)%[(%d+)%]$")
    if name then return cur[name], tonumber(idx) end
    return cur, last
end

local valuesState = {}  -- chemin d'asset -> "ok" / "absent"
local carStatsAddr = nil
local function close(a, b) return math.abs((a or 0) - b) < 1e-4 end

local function applyValues()
    for _, entry in ipairs(VALUES) do
        local path, fields = entry[1], entry[2]
        local obj = StaticFindObject(path)
        if obj and obj:IsValid() then
            local done, total, errors = 0, #fields, {}
            for _, f in ipairs(fields) do
                local ok, err = pcall(function()
                    local holder, key = resolve(obj, f[1])
                    if type(f[2]) == "table" then
                        local v = holder[key]
                        v.X = f[2][1]; v.Y = f[2][2]
                        local back = holder[key]
                        if not (close(back.X, f[2][1]) and close(back.Y, f[2][2])) then error("relu " .. tostring(back.X)) end
                    else
                        holder[key] = f[2]
                        if not close(holder[key], f[2]) then error("relu " .. tostring(holder[key])) end
                    end
                end)
                if ok then done = done + 1 else errors[#errors + 1] = f[1] .. " (" .. tostring(err) .. ")" end
            end
            local state = done .. "/" .. total
            if path:find("CarStatsDataAsset") and done == total and obj:GetAddress() ~= carStatsAddr then
                carStatsAddr = obj:GetAddress()
                local f = io.open(CARSTATS_FILE, "w")
                if f then f:write(string.format("%X\n", carStatsAddr)); f:close() end
            end
            if valuesState[path] ~= state then
                valuesState[path] = state
                log(string.format("valeurs 2026 : %s %d/%d (objet %X)", path:match("[^/]+$"), done, total, obj:GetAddress()))
                for _, e in ipairs(errors) do log("  impossible : " .. e) end
            end
        elseif valuesState[path] ~= "absent" then
            valuesState[path] = "absent"
            log("valeurs 2026 : " .. path .. " pas encore chargé")
        end
    end
end

---------------------------------------------------------------------------
-- Zones
---------------------------------------------------------------------------

local function inRange(node, s, e)
    if s <= e then return node >= s and node <= e end
    return node >= s or node <= e -- zone qui passe la ligne d'arrivée
end

--- index de la zone contenant le point, ou nil
local function zoneAt(node)
    if not track or node == nil or node < 0 or node >= track.nodes then return nil end
    for i, z in ipairs(track.zones) do
        if inRange(node, z.s, z.e) then return i end
    end
    return nil
end

local function appendPosition(arr, node, dist)
    arr[#arr + 1] = { m_trackNodeID = node, m_splineDistance = dist, m_offRaceLineDistance = 0.0 }
end

local function patchTrack()
    local comp = FindFirstOf("RaceSimTrackComponent")
    if not comp or not comp:IsValid() then return end
    local addr = comp:GetAddress()
    if addr == patchedComp then return end

    local name = comp:GetFullName():match("/Circuits/([%w_]+)/Lvl_")
    local data = name and ZONES[name]
    patchedComp = addr
    cars = {}
    if not data then
        track = nil
        log("circuit inconnu : " .. tostring(name))
        return
    end
    track = { name = name, nodes = data.nodes, zones = {} }
    for _, z in ipairs(data.existing) do table.insert(track.zones, { s = z.s, e = z.e, added = false }) end
    for _, z in ipairs(data.added) do table.insert(track.zones, { s = z.s, e = z.e, added = true }) end

    local ok, err = pcall(function()
        -- Pas de point de détection pour les zones ajoutées : en ajouter un (2026-10-04, Monza) a provoqué
        -- un drapeau rouge dès que le jeu a activé le DRS. On n'ajoute que le début et la fin.
        local before = #comp.m_DRSZoneStart
        for _, z in ipairs(data.added) do
            appendPosition(comp.m_DRSZoneStart, z.s, z.sd)
            appendPosition(comp.m_DRSZoneEnd, z.e, z.ed)
        end
        log(string.format("%s : zones %d -> %d (détections %d, fins %d)", name, before, #comp.m_DRSZoneStart,
            #comp.m_DRSDetection, #comp.m_DRSZoneEnd))
    end)
    if not ok then log("ajout des zones impossible : " .. tostring(err)) end
end

---------------------------------------------------------------------------
-- Voiture par voiture : Straight / Overtake, mesure
---------------------------------------------------------------------------

local function driverCode(data)
    local raw = data.DriverCode:ToString()
    return raw:match("DriverCode_(%w+)") or raw:match("|(%w+)|") or raw
end

local function writeMeasure(st, z, data)
    local header = not fileExists(CSV_FILE)
    local f = io.open(CSV_FILE, "a")
    if not f then return end
    if header then f:write("date;circuit;zone;type;pilote;v_entree;v_max;forcage;drs_avant;drs_dans;overtake;jeu\n") end
    f:write(string.format("%s;%s;%d;%s;%s;%d;%d;%s;%d;%d;%s;%s\n", os.date("%Y-%m-%d %H:%M:%S"), track.name,
        st.zone, z.added and "ajoutee" or "drs", driverCode(data), st.entrySpeed, st.max,
        st.mode, st.seenBefore, st.seenIn,
        st.overtake and "overtake" or "-", st.gameOpened and "jeu" or "-"))
    f:close()
end

local function updateCar(car)
    local data = car.CarData
    local key = car:GetAddress()
    local st = cars[key]
    if not st then st = { zone = nil, overtake = false, seen = 0 }; cars[key] = st end

    local drs = tonumber(data.DRSState)
    local zone = zoneAt(tonumber(data.CurrentTrackNode))
    local speed = tonumber(data.SpeedKPH) or 0

    local gameActive = drs == DRS_ACTIVE
    local gameDrs = drs

    if zone and zone ~= st.zone then
        -- entrée dans une zone : état du jeu lu avant toute écriture
        st.entry = drs
        st.overtake = (drs == DRS_ENABLED or drs == DRS_ACTIVE)
        st.max, st.entrySpeed, st.gameOpened = speed, speed, gameActive
        st.mode = straightOn and "straight" or "normal"
        st.seenBefore, st.seenIn = math.max(st.seen, gameDrs), math.max(gameDrs, 0)
    elseif zone then
        if speed > st.max then st.max = speed end
        if gameActive then st.gameOpened, st.overtake = true, true end
        if gameDrs > st.seenIn then st.seenIn = gameDrs end
    else
        if st.zone and track then
            local ok, err = pcall(writeMeasure, st, track.zones[st.zone], data)
            if not ok then logOnce("mesure impossible : " .. tostring(err)) end
            st.seen = 0
        end
        if gameDrs > st.seen then st.seen = gameDrs end
        st.overtake = (drs == DRS_DETECTED or drs == DRS_ENABLED)
    end
    st.zone = zone
end

---------------------------------------------------------------------------
-- Message F7 (les cases STRAIGHT / OVERTAKE sont dans le bandeau des pilotes)
---------------------------------------------------------------------------

local function newObj(class, outer, name)
    return StaticConstructObject(StaticFindObject(class), outer, FName(name))
end

local function buildHud()
    local gi = UEHelpers.GetGameInstance()
    local w = newObj("/Script/UMG.UserWidget", gi, "Reg2026HUD")
    w.WidgetTree = newObj("/Script/UMG.WidgetTree", w, "Reg2026Tree")
    local canvas = newObj("/Script/UMG.CanvasPanel", w.WidgetTree, "Reg2026Canvas")
    w.WidgetTree.RootWidget = canvas

    -- message au centre de l'écran
    local toast = newObj("/Script/UMG.Border", canvas, "Reg2026Toast")
    toast:SetPadding({ Left = 24, Top = 12, Right = 24, Bottom = 12 })
    local toastText = newObj("/Script/UMG.TextBlock", toast, "Reg2026ToastText")
    toastText.Font.Size = 22
    toastText:SetColorAndOpacity({ SpecifiedColor = WHITE, ColorUseRule = 0 })
    toast:SetContent(toastText)
    local tslot = canvas:AddChildToCanvas(toast)
    tslot:SetAutoSize(true)
    tslot:SetAnchors({ Minimum = { X = 0.5, Y = 0.4 }, Maximum = { X = 0.5, Y = 0.4 } })
    tslot:SetAlignment({ X = 0.5, Y = 0.5 })
    toast:SetVisibility(2)
    ui = { toast = toast, toastText = toastText }

    w:SetVisibility(3) -- HitTestInvisible : ne bloque pas les clics
    w:AddToViewport(50)
    hud = w
end

local function ensureHud()
    if hud and hud:IsValid() then return true end
    hud = nil
    local ok, err = pcall(buildHud)
    if not ok then logOnce("HUD impossible : " .. tostring(err)) end
    return ok
end

local function refreshHud()
    -- masque le message une fois son temps écoulé ; ne crée rien tant qu'aucun message n'a été demandé
    if hud and hud:IsValid() then
        ui.toast:SetVisibility(os.clock() < toastUntil and 3 or 2)
    end
end

local function showToast(text, color)
    ExecuteInGameThread(function()
        if not ensureHud() then return end
        ui.toastText:SetText(FText(text))
        ui.toast:SetBrushColor(color)
        ui.toast:SetVisibility(3)
        toastUntil = os.clock() + TOAST_TIME
    end)
end

---------------------------------------------------------------------------
-- Touches et boucle
---------------------------------------------------------------------------

-- F11 (recherche) : adresse de chaque voiture et quelques valeurs de CarData, pour retrouver la position
-- de CarData en mémoire (tools_native/inject.py find). Pas de réflexion UE4SS : seulement des lectures simples.
local DEBUG_FILE = "ue4ss/Mods/Reg2026/debug_cars.txt"

local function dumpCars()
    local list = FindAllOf("CarActor") or {}
    local f = io.open(DEBUG_FILE, "w")
    f:write("pilote;adresse;DriverNumber;RacePos;LapCount;Gear;CurrentTrackNode;DRSState;SpeedKPH\n")
    for _, car in ipairs(list) do
        local data = car.CarData
        f:write(string.format("%s;%X;%d;%d;%d;%d;%d;%d;%d\n", driverCode(data), car:GetAddress(),
            tonumber(data.DriverNumber), tonumber(data.RacePos), tonumber(data.LapCount), tonumber(data.Gear),
            tonumber(data.CurrentTrackNode), tonumber(data.DRSState), tonumber(data.SpeedKPH)))
    end
    f:close()
    log(string.format("F11 : %d voitures écrites dans debug_cars.txt", #list))
end

RegisterKeyBind(Key.F11, {}, function()
    ExecuteInGameThread(function()
        local ok, err = pcall(dumpCars)
        if not ok then log("F11 impossible : " .. tostring(err)) end
    end)
end)

RegisterKeyBind(Key.F7, {}, function()
    straightOn = not straightOn
    if straightOn then
        os.remove(OFF_FILE)
    else
        local f = io.open(OFF_FILE, "w")
        if f then f:write("Straight Mode coupé (F7)"); f:close() end
    end
    log("Straight Mode : " .. (straightOn and "toute la grille" or "règle d'origine"))
    showToast(straightOn and "Règlement 2026 : Straight Mode pour tous, Overtake Mode à moins d'1 s"
        or "Règle d'origine du jeu : DRS à moins d'1 s",
        straightOn and COLOR_ON or COLOR_WARN)
end)

--- bascule actif=0/1 dans superclipping.ini en gardant les autres réglages ; renvoie le nouvel état
local function toggleClipping()
    local f = io.open(CLIP_FILE, "r")
    local text = f and f:read("a") or CLIP_DEFAULT
    if f then f:close() end
    local on = text:match("actif%s*=%s*(%d)") == "1"
    on = not on
    if text:match("actif%s*=%s*%d") then
        text = text:gsub("actif%s*=%s*%d", "actif=" .. (on and "1" or "0"), 1)
    else
        text = "actif=" .. (on and "1" or "0") .. "\n" .. text
    end
    f = io.open(CLIP_FILE, "w")
    if f then f:write(text); f:close() end
    return on
end

RegisterKeyBind(Key.F6, {}, function()
    local on = toggleClipping()
    log("super clipping : " .. (on and "actif" or "désactivé"))
    showToast(on and "Super clipping : recharge en bout de ligne droite"
        or "Super clipping désactivé (limite de 290 km/h gardée)",
        on and COLOR_ON or COLOR_WARN)
end)

--- charge Reg2026Patch.dll (le travail se fait depuis son DllMain)
local function loadPatch()
    local dir = debug.getinfo(1, "S").source:match("^@(.*[/\\])Scripts[/\\]")
    for _, path in ipairs({ dir and (dir .. "Reg2026Patch.dll"), MOD_DIR .. "Reg2026Patch.dll" }) do
        if path and fileExists(path) then
            local ok, err = package.loadlib(path, "*")
            if ok then log("Reg2026Patch.dll chargée (journal : patch.log)") return end
            log("Reg2026Patch.dll impossible à charger : " .. tostring(err))
            return
        end
    end
    log("Reg2026Patch.dll introuvable : Straight Mode seulement visuel")
end

local hooked = false
local function tryHook()
    if hooked then return end
    hooked = pcall(function()
        RegisterHook(CAR_TICK, function(self)
            local car = self:get()
            local now = os.clock()
            if now - lastTrackCheck >= TRACK_CHECK then
                lastTrackCheck = now
                local ok, err = pcall(patchTrack)
                if not ok then logOnce("erreur circuit : " .. tostring(err)) end
                local okv, errv = pcall(applyValues)
                if not okv then logOnce("erreur valeurs 2026 : " .. tostring(errv)) end
            end

            local ok, err = pcall(updateCar, car)
            if not ok then logOnce("erreur voiture : " .. tostring(err)) end

            if now - lastHud >= HUD_REFRESH then
                lastHud = now
                local ok2, err2 = pcall(refreshHud)
                if not ok2 then logOnce("erreur HUD : " .. tostring(err2)) end
            end
        end)
    end)
    if hooked then log("prêt (F7 Straight Mode, F6 super clipping)") else ExecuteWithDelay(HOOK_RETRY, tryHook) end
end

loadPatch()
tryHook()

-- Les valeurs 2026 sont appliquées depuis le crochet (toutes les 2 s, dès que des voitures existent : avant le
-- départ, et de nouveau si un asset est rechargé). Pas de LoopAsync + ExecuteInGameThread répétés : le jeu a
-- planté le 2026-10-04 sur une erreur Lua d'UE4SS sans pile (« attempt to call a RemoteUnrealParam value »,
-- qui fait abandonner le jeu) et ces rappels asynchrones répétés en sont le suspect le plus probable.
