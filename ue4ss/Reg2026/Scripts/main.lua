-- Reg2026 : Straight Mode pour toute la grille.
--
-- 1. Zones : au chargement d'un circuit, ajoute les zones Straight Mode (zones.lua) aux zones DRS du jeu.
-- 2. Straight Mode : dans une zone, l'état DRS de chaque voiture est forcé à Active (si le forçage est actif).
--    L'animation des ailerons reste celle du « DRS mod », qui lit cet état : notre hook est enregistré
--    au plus tôt pour écrire avant sa lecture. Le forçage ne change pas la vitesse calculée par le jeu
--    (mesuré à Monza), seulement l'état affiché.
-- 3. Overtake Mode : disponible si le jeu avait autorisé le DRS (moins d'1 s au point de détection)
--    au moment d'entrer dans la zone, ou s'il l'ouvre lui-même dans la zone.
-- 4. Mesure : à la sortie de chaque zone, une ligne « MESURE; » dans UE4SS.log (vitesse max, forçage,
--    overtake, et « jeu » si le jeu a ouvert le DRS lui-même dans la zone).
-- 5. Les cases STRAIGHT / OVERTAKE sont dans le bandeau des pilotes (pak zzz_Reg2026UI_P, scripts/build_ui.py) ;
--    ici seulement un message temporaire au changement de forçage.
--
-- Touche : F7 activer/désactiver le forçage.
local UEHelpers = require("UEHelpers")
local ZONES = require("zones")

local CAR_TICK = "/Game/Cars/BaseCars/BaseCar2022/BP_BaseCar2022_Actor.BP_BaseCar2022_Actor_C:ReceiveTick"
local HUD_REFRESH = 0.2   -- secondes
local TRACK_CHECK = 2.0   -- secondes entre deux recherches du circuit chargé
local TOAST_TIME = 3.0    -- durée du message F7
local HOOK_RETRY = 250    -- ms : s'enregistrer avant le DRS mod

-- EDRSState
local DRS_DISABLED, DRS_DETECTED, DRS_ENABLED, DRS_ACTIVE = 0, 1, 2, 3

local WHITE           = { R = 1, G = 1, B = 1, A = 1 }
local COLOR_ON        = { R = 0.05, G = 0.55, B = 0.15, A = 0.95 }
local COLOR_WARN      = { R = 0.60, G = 0.10, B = 0.10, A = 0.95 }

local forceStraight = true
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

local function appendPositions(arr, list, field, distField)
    for _, z in ipairs(list) do
        arr[#arr + 1] = { m_trackNodeID = z[field], m_splineDistance = z[distField], m_offRaceLineDistance = 0.0 }
    end
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
        local starts = comp.m_DRSZoneStart
        local before = #starts
        appendPositions(starts, data.added, "s", "sd")
        appendPositions(comp.m_DRSZoneEnd, data.added, "e", "ed")
        log(string.format("%s : zones %d -> %d (fins %d)", name, before, #comp.m_DRSZoneStart, #comp.m_DRSZoneEnd))
    end)
    if not ok then log("ajout des zones impossible : " .. tostring(err)) end
end

---------------------------------------------------------------------------
-- Voiture par voiture : Straight / Overtake, mesure
---------------------------------------------------------------------------

local function updateCar(car)
    local data = car.CarData
    local key = car:GetAddress()
    local st = cars[key]
    if not st then st = { zone = nil, overtake = false, wrote = false }; cars[key] = st end

    local drs = tonumber(data.DRSState)
    local zone = zoneAt(tonumber(data.CurrentTrackNode))
    local speed = tonumber(data.SpeedKPH) or 0

    -- un Active que nous n'avons pas écrit vient du jeu (DRS réel)
    local gameActive = drs == DRS_ACTIVE and not st.wrote

    if zone and zone ~= st.zone then
        -- entrée dans une zone : état du jeu lu avant toute écriture
        st.entry = drs
        st.overtake = (drs == DRS_ENABLED or drs == DRS_ACTIVE)
        st.max, st.forced, st.gameOpened = speed, forceStraight, gameActive
    elseif zone then
        if speed > st.max then st.max = speed end
        if gameActive then st.gameOpened, st.overtake = true, true end
    else
        if st.zone and track then
            local z = track.zones[st.zone]
            print(string.format("MESURE;%s;%d;%s;%s;%d;%s;%s;%s\n", track.name, st.zone,
                z.added and "ajoutee" or "drs", data.DriverCode:ToString(), st.max,
                st.forced and "force" or "normal", st.overtake and "overtake" or "-",
                st.gameOpened and "jeu" or "-"))
        end
        st.overtake = (drs == DRS_DETECTED or drs == DRS_ENABLED)
    end
    st.zone = zone

    if forceStraight and zone then
        if drs ~= DRS_ACTIVE then
            data.DRSState = DRS_ACTIVE
            st.wrote = true
        end
    elseif st.wrote then
        -- forçage coupé (F7) ou sortie de zone : on rend l'état d'origine si c'est encore le nôtre
        if drs == DRS_ACTIVE then
            data.DRSState = zone and st.entry or DRS_DISABLED
        end
        st.wrote = false
    end
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

RegisterKeyBind(Key.F7, {}, function()
    forceStraight = not forceStraight
    log("forçage : " .. (forceStraight and "activé" or "désactivé"))
    print(string.format("MESURE_F7;%s\n", forceStraight and "force" or "normal"))
    showToast(forceStraight and "Straight Mode FORCÉ pour toute la grille"
        or "Straight Mode : règle normale du jeu (DRS à 1 s)",
        forceStraight and COLOR_ON or COLOR_WARN)
end)

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
    if hooked then log("prêt (F7 forçage)") else ExecuteWithDelay(HOOK_RETRY, tryHook) end
end

tryHook() -- au plus tôt : nos écritures doivent passer avant la lecture du DRS mod
