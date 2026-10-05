// Reg2026Patch.dll : règlement 2026 dans la simulation de F1 Manager 2024 (v1.11).
//
// Chargée par le mod UE4SS Reg2026 (package.loadlib). Tout se fait depuis un thread lancé par DllMain,
// sans dépendre de l'ABI C++ d'UE4SS. Journal : patch.log dans le dossier de la DLL.
//
// Machine à états DRS du jeu : exe+0x230C2B0, appelée pour chaque voiture à chaque pas de simulation
// (rdi = objet voiture de la simulation, 0x10D8 octets ; état DRS en +0x86D, tours en +0x7E4).
//
// 1. Straight Mode dès le premier tour. Le jeu n'autorise le DRS qu'à partir d'un tour donné (+0x870 :
//    2 tours après le départ ou une relance) :
//        230C32F  cmp ecx, dword ptr [rdi + 0x870]   ; 3B 8F 70 08 00 00
//        230C335  jl  +5                             ; 7C 05  -> 90 90
//    Les autres blocages restent : voiture de sécurité, drapeaux, piste mouillée.
//
// 2. Straight Mode pour tous + Overtake Mode. Au point de détection, le jeu compare
//    « temps actuel − passage de la voiture devant » à 1,0 s :
//        230C440  movaps xmm0, xmm6                  ; 0F 28 C6
//        230C443  subss  xmm0, dword ptr [rbx]       ; F3 0F 5C 03
//        230C447  comiss xmm0, xmm7                  ; 0F 2F C7
//        230C44A  ja     230C47A                     ; 77 2E  (pas de DRS au-delà d'1 s)
//    Ces 12 octets deviennent « mov rax, cave ; jmp rax » (rax est libre ici). La cave refait le calcul :
//    à moins d'1 s, elle range l'objet voiture dans une file ; dans tous les cas elle revient en 230C44C,
//    où le jeu donne le droit au DRS. Le thread de la DLL vide la file et ajoute OVERTAKE_ENERGY à la
//    batterie (float 0..1 en +0x878), une fois par tour et par voiture : 0,5 MJ sur 4 MJ = 12,5 %.
//
// 3. Overtake Mode utilisé : la voiture qui a reçu le bonus le garde (g_owned) jusqu'à une vraie occasion, la voiture
//    devant à moins de overtake_ecart_attaque (0,6 s ; avant le 2026-10-05, le crédit partait dès 250 km/h après la
//    détection, même loin derrière). Alors seulement (g_cfg.boost, recalculé toutes les 100 ms par UpdateGaps) elle
//    déploie l'ERS à fond, à chaque pas hors freinage, jusqu'à 337 km/h, payé par le crédit de 12,5 % puis, une fois
//    le crédit épuisé (1,4 s), par sa propre batterie jusqu'au freinage de la ligne droite (overtake_batterie=1 : la
//    vraie règle donne la pleine puissance jusqu'à 337 km/h pendant que celle du défenseur baisse dès 290 ; avec le
//    crédit seul, l'effet ne durait que 1,4 s et le dépassement avait du mal), au plus overtake_batterie_max (20 %)
//    de batterie : sans borne, une ligne droite de Monza vidait la batterie (97 % -> 10 %) pour 11 places gagnées
//    contre 13 avec le crédit seul. Crédit perdu s'il n'a pas servi à la fin du tour suivant. Le crédit est de l'énergie en
//    plus de la batterie : la cave de recharge (point 4) annule la baisse de batterie du déploiement forcé et décompte
//    la même quantité dans le crédit, donc le bonus vaut toujours 0,5 MJ même quand la batterie est pleine (avant,
//    il s'ajoutait à la batterie, bornée à 1,0 : la grille arrive à 94-100 %, le bonus était plafonné 3 fois sur 4).
//    Mise à jour ERS du jeu, exe+0x2308250 : la décision de l'IA (230B990) donne [rbp+0x38] = 0 (pas de recharge)
//    / 1 / 2, puis dl = 0 veut dire « déployer » :
//        23084B8  xor dl, dl / jmp / mov dl, 1
//        23084BE  movzx eax, byte ptr [rbp + 0x38]          ; 0F B6 45 38
//        23084C2  movss xmm5, dword ptr [rip + 0x3CA6FCA]    ; F3 0F 10 2D CA 6F CA 03
//    Ces 12 octets deviennent « mov rax, cave ; jmp rax » (rax est écrasé juste après). Quand la voiture (index
//    en +0x710) a le bonus et ne freine pas (accélération +0x19C >= 0), la cave met dl = 0 et [rbp+0x38] = 0,
//    même si l'IA voulait recharger (en Top-Up elle recharge presque toujours). Cette cave n'est atteinte que
//    quand 230B990 répond vrai (voiture proche et budget du tour) : le déploiement forcé de l'Overtake Mode est
//    donc refait dans la cave de recharge (point 4), par laquelle passent tous les chemins. Le code en 230848F,
//    juste avant, est un saut de Denuvo : on n'y touche pas. Ce crochet est posé une fois au chargement (avant
//    toute course) et reste en place ; F7 vide seulement la liste des voitures en Overtake.
//
// 4. Limite de vitesse 2026 et super clipping. Dans la même cave : au-delà de vitesse_max (290 km/h, vitesse en m/s
//    en +0x198 de l'objet voiture), plus de déploiement (dl = 1) ; vitesse_max_overtake (337 km/h) pour une voiture en
//    Overtake Mode. La limite est toujours active avec la règle 2026 : c'est le principal avantage de l'Overtake Mode
//    (sans elle, aucune différence de vitesse de pointe). Le super clipping (optionnel, actif=1 dans superclipping.ini,
//    touche F6 côté Lua) ajoute la recharge au-dessus de la limite. La recharge se fait ailleurs, car la cave ERS n'est atteinte que
//    quand l'IA prend une décision (230B990 vrai). Tous les chemins se rejoignent en 230856D, juste avant
//    le calcul de la nouvelle batterie (230859B : xmm0 = débit * 1/30 + xmm12, bornée à 1 ensuite) :
//        230856D  mov r15, [rsp + 0xE8]          ; 4C 8B BC 24 E8 00 00 00
//        2308575  movaps xmm1, xmm2              ; 0F 28 CA
//        2308578  mulss xmm1, [rip + 0x3CA17C4]  ; F3 0F 59 0D C4 17 CA 03
//    Ces 19 octets deviennent « mov rax, cave ; jmp rax » + 7 nop (rax n'est plus lu avant d'être réécrit,
//    et aucun saut ne vise 2308575 ni 2308578). Au-dessus de la vitesse limite, sans freiner (accélération
//    +0x19C >= 0), la cave ajoute « recharge » à xmm12 (batterie de départ ; 0 sans super clipping). Sous la limite, pour une voiture en
//    Overtake Mode qui ne freine pas, au-dessus de overtake_vitesse_min (250 km/h : le crédit se dépense en bout de
//    ligne droite, là où le jeu évalue les dépassements, et le bonus de probabilité du point 7 dure jusque-là),
//    ERS disponible (dil = 1, encore valide ici) et crédit restant, la cave force
//    le déploiement à pleine puissance : état [rsp+0x60] = 3, débit xmm2 = [rsp+0x68] = ERSAccelDeployBatteryRate
//    (RaceSimDataAsset [[r13+0x18]+0x5D610] +0x144 ; r13 est encore valide, r15 vient d'être restauré), puis
//    xmm12 -= xmm2 × 1/30 (la batterie ne bouge pas) et le crédit baisse d'autant. rdx, xmm0 et xmm1 sont libres
//    ici (réécrits avant d'être lus), xmm6 vaut 0. Mesuré en course à Monza :
//    plus aucun déploiement au-delà de 290 km/h ; la fonction est appelée plusieurs fois par pas de simulation
//    (~30 par seconde de simulation) : à 0,0006 par appel, +1,8 % par pas à fond au-delà de 290 km/h pour
//    un déploiement à −3 % ; 0,0007 donne le rapport réel 250 kW / 350 kW = 0,7. Ramené à 0,00035 le 2026-10-05 :
//    à 0,0007 c'était la principale source d'énergie et la batterie restait pleine (89 % de moyenne à Monza ;
//    80 % avec 0,00035 et la recharge au freinage à 0,0875, mesuré en direct). Puis 0,002 avec le point 10, qui
//    dépense beaucoup plus : le vrai super clipping récupère jusqu'à 250 kW (0,0012 : batteries vides en 2 tours).
//
// 10. Déploiement pour le chrono. L'IA ne déploie que ~10 % du temps (en sortie de virage, dans son plan d'énergie par
//    tour) et, sans déploiement, l'accélération est multipliée par 0,66 : 1:29.0 de médiane à Monza contre 1:23.5 au
//    meilleur tour du vrai GP 2026 (mesuré : 1:20.0 avec le multiplicateur à 1,0). Dans la cave de recharge, une
//    voiture marquée g_cfg.push (+0x10C) déploie à fond sur sa batterie, hors freinage et sous la limite de vitesse ;
//    le thread la marque selon sa stratégie : BOOST jusqu'à deploiement_boost (40 %) de batterie, ÉQUILIBRÉ jusqu'à
//    deploiement_equilibre (60 %), reprise 15 points au-dessus (à 15 % / 40 %, la grille tombait à 35-38 % de batterie
//    en deux tours et passait en RÉSERVE), rien en RÉSERVE ni en LIFT & COAST. La recharge en bout
//    de ligne droite (point 4) paie la ligne droite suivante.
//
// 5. Stratégies ERS 2026 (stratégie de la voiture en +0xEF2 ; l'IA roule surtout en 2, Déploiement, gardée telle quelle) :
//    - 3 Top-Up -> RÉSERVE : jamais de déploiement (le jeu recharge dans cette stratégie), sauf en Overtake Mode
//      ou en bataille, avec une voiture à moins d'1 s devant ou derrière (UpdateGaps : écart en distance +0x194
//      divisé par la vitesse de celle qui suit, positions en +0x7E0).
//    - 1 Récupération -> LIFT & COAST : plus de déploiement au-delà de 250 km/h et recharge au-dessus, même sans
//      super clipping.
//
// 6. Tableaux aéro 2026 du CarStatsDataAsset : AeroSpeedMultipliers et DirtyAirSpeedMultipliers (3 FVector2D en
//    doubles chacun). UE4SS ne sait pas indexer ces tableaux fixes et le pak zzz_Reg2026_P perd face à un mod qui
//    remplace le même asset (RRacingV5). Le script Lua écrit l'adresse de l'objet dans carstats.txt une fois ses
//    propres valeurs en place, et la DLL écrit les tableaux. Mesuré à Monza : DRSTopSpeedMultiplier en +0x80
//    (1,03 / 1,06 écrits par le script : sert de vérification), AeroSpeedMultipliers en +0x1C0,
//    DirtyAirSpeedMultipliers en +0x200.
//
// 7. Probabilité de dépassement. Dans l'évaluation d'un dépassement (fonction exe+0x231F8B0, rdi = OvertakeData du
//    RaceSimDataAsset = asset+0x478), le jeu ajoute [rdi+0x3C] (0,2, champ sans nom dans le JSON) à la probabilité de
//    réussite quand l'attaquant (r14) a le DRS (état +0x86D = 1 ou 3) et pas le défenseur (r15) :
//        231FBFE  movzx eax, byte ptr [r14 + 0x86D] / dec al / test al, 0xFD   ; attaquant
//        231FC0A  movzx eax, byte ptr [r15 + 0x86D] / cvtdq2ps xmm0, xmm0 / sete cl / dec al / test al, 0xFD / sete al
//        231FC2B  test cl, cl / je ; test al, al / jne ; movss xmm1, [rdi + 0x3C]
//    Avec le Straight Mode pour toute la grille, les deux voitures ont le DRS et ce bonus ne s'applique plus jamais :
//    dépasser devenait très difficile. Ces 33 octets deviennent « mov rax, cave ; jmp rax » + 21 nop (rax et rcx sont
//    écrasés avant d'être relus, aucun saut ne vise l'intérieur) ; la cave donne cl = avantage Overtake de l'attaquant
//    (g_cfg.assist : sur overtake_distance mètres après chaque détection à moins d'1 s, 2 km par défaut, indépendant du
//    crédit d'énergie qui ne dure que 1,4 s alors que le jeu évalue le dépassement plus loin dans la ligne droite :
//    mesuré à Monza, 64 évaluations en 2 min, aucune pendant le déploiement) et al = 0 quand la règle 2026 est active,
//    sinon elle refait le test DRS d'origine (F7). Avant, l'avantage s'arrêtait à la fin du tour : sur 20 circuits sur
//    24, une zone passe la ligne d'arrivée (Monza : détection avant la Parabolica, fin de zone au virage 1), et le
//    bonus était perdu avant l'évaluation. Entre une détection et la fin de sa zone il y a au plus 1,8 km (Imola).
//
// 8. État pour l'interface. Toutes les 100 ms, la DLL écrit Content\UIGameface\Reg2026\state.json (fichier libre à
//    côté des paks : l'interface Gameface le lit par XMLHttpRequest à l'adresse relative Reg2026/state.json, les paks
//    gardant la priorité pour tout le reste) : par voiture, index, position, tour, crédit Overtake Mode restant,
//    déploiement forcé actif (b) et avantage au dépassement actif (a). Le bandeau pilote (ui_mod) y lit la jauge
//    OVERTAKE (crédit, barre allumée pendant le déploiement) et la case OVERTAKE (avantage).
//
// Pour mémoire, plan de déploiement ERS de l'IA (rien n'est modifié). La mise à jour ERS ne demande la décision de
// l'IA (230B990) que dans l'état de comportement 2 (+0x200, pied au plancher : 79 % du temps à Monza) ; 0 (freinage),
// 3 et 5 passent par la recharge, 1 et 4 (virage) par le neutre. La décision ne laisse déployer que si l'énergie
// déployée dans le tour (+0x888, plus +0x88C) reste sous un budget cumulé lu au nœud de piste de la voiture :
//     230BA24  mov rax, [rbx + 0x6F8]   ; rbx = [r13 + 8] : TArray de floats, un par nœud (voie des stands comprise)
//     230BA2B  movss xmm6, [rax + rcx*4]
// Mesuré à Monza (2026-10-05) : 115 nœuds, budget de 0 à 1,00 batterie par tour par paliers à chaque ligne droite,
// fixe pendant la course, le même pour toutes les voitures. Multiplié par 1,5 en direct : aucun effet (batterie 89 ->
// 85 %, déploiement 12 -> 13 % du temps), l'IA ne l'atteint pas : elle déploie en sortie de virage (165 km/h en
// moyenne) et la limite de 290 km/h coupe ensuite. Ce qui garde la batterie pleine, c'est la recharge, surtout
// celle du super clipping au-dessus de la limite.
//
// Le fichier straight_off.txt (créé/supprimé par F7 côté Lua) remet le jeu d'origine.
#include <windows.h>
#include <stdio.h>
#include <share.h>
#include <string.h>
#include <math.h>
#include <initializer_list>
#include <stddef.h>

static const DWORD64 LAP_RVA = 0x230C335;
static const BYTE LAP_CONTEXT[6] = { 0x3B, 0x8F, 0x70, 0x08, 0x00, 0x00 };
static const BYTE LAP_ORIGINAL[2] = { 0x7C, 0x05 };
static const BYTE NOP2[2] = { 0x90, 0x90 };

static const DWORD64 GAP_RVA = 0x230C440;
static const DWORD64 GAP_RETURN_RVA = 0x230C44C;
static const BYTE GAP_ORIGINAL[12] = { 0x0F, 0x28, 0xC6, 0xF3, 0x0F, 0x5C, 0x03, 0x0F, 0x2F, 0xC7, 0x77, 0x2E };
static const BYTE GAP_OLD_PATCH[12] = { 0x0F, 0x28, 0xC6, 0xF3, 0x0F, 0x5C, 0x03, 0x0F, 0x2F, 0xC7, 0x90, 0x90 };
static const BYTE JMP_OVER[2] = { 0xEB, 0x0A };  // saut direct en 230C44C : Straight Mode sans Overtake

static const DWORD64 ERS_RVA = 0x23084BE;
static const DWORD64 ERS_RETURN_RVA = 0x23084CA;
static const BYTE ERS_CONTEXT[6] = { 0x32, 0xD2, 0xEB, 0x02, 0xB2, 0x01 };
static const BYTE ERS_ORIGINAL[12] = { 0x0F, 0xB6, 0x45, 0x38, 0xF3, 0x0F, 0x10, 0x2D, 0xCA, 0x6F, 0xCA, 0x03 };

static const DWORD64 CLIP_RVA = 0x230856D;
static const DWORD64 CLIP_RETURN_RVA = 0x2308580;
static const BYTE CLIP_ORIGINAL[19] = { 0x4C, 0x8B, 0xBC, 0x24, 0xE8, 0x00, 0x00, 0x00, 0x0F, 0x28, 0xCA,
                                        0xF3, 0x0F, 0x59, 0x0D, 0xC4, 0x17, 0xCA, 0x03 };

static const DWORD64 OVT_RVA = 0x231FBFE;
static const DWORD64 OVT_RETURN_RVA = 0x231FC1F;
static const BYTE OVT_ORIGINAL[33] = { 0x41, 0x0F, 0xB6, 0x86, 0x6D, 0x08, 0x00, 0x00, 0xFE, 0xC8, 0xA8, 0xFD,
                                       0x41, 0x0F, 0xB6, 0x87, 0x6D, 0x08, 0x00, 0x00, 0x0F, 0x5B, 0xC0, 0x0F, 0x94, 0xC1,
                                       0xFE, 0xC8, 0xA8, 0xFD, 0x0F, 0x94, 0xC0 };

static const DWORD CAR_LAPS = 0x7E4;
static const DWORD CAR_DRS_LAP = 0x870;  // tour à partir duquel le jeu d'origine autorise le DRS (départ, relance)
static const DWORD CAR_MODE = 0x200;   // état de comportement : 0, 2, 3 ou 4 pendant la course (pas « en course = 2 »)
static const DWORD CAR_INDEX = 0x710;
static const DWORD CAR_POS = 0x7E0;        // position en course, 0 = en tête
static const DWORD CAR_DIST = 0x194;       // distance totale parcourue (m)
static const DWORD CAR_SPEED = 0x198;      // m/s
static const DWORD CAR_ACCEL = 0x19C;      // m/s² (≈ −26 au freinage, mesuré à Monza)
static const DWORD CAR_STRATEGY = 0xEF2;   // stratégie ERS : 0 Neutre, 1 Récupération, 2 Déploiement, 3 Top-Up
static const DWORD CAR_STRIDE = 0x10D8;
static const int GRID = 22;
static const int CARS = 32;
static const DWORD CAR_BATTERY = 0x878;
static const DWORD STATS_DRS_TOP = 0x80;   // CarStatsDataAsset : CarStatRanges.DRSTopSpeedMultiplier (2 doubles)
static const DWORD STATS_AERO = 0x1C0;     // CarStatRanges.AeroSpeedMultipliers[3] (FVector2D en doubles)
static const DWORD STATS_DIRTY = 0x200;    // CarStatRanges.DirtyAirSpeedMultipliers[3]
static const double AERO_2026[6] = { 0.814, 0.945, 0.731, 0.95, 0.767, 0.92 };  // mêmes valeurs que scripts/patch_2026.py
static const double DIRTY_2026[6] = { 0.93, 1.0, 0.93, 1.0, 0.93, 1.0 };
static const float OVERTAKE_ENERGY = 0.125f;
static const DWORD POLL_MS = 100;
static const int RING = 64;

struct OvertakeRing {
    volatile LONG written;
    LONG pad;
    BYTE* cars[RING];
};

static OvertakeRing g_ring;
static wchar_t g_dir[MAX_PATH];
static BYTE* g_exe;
static BYTE* g_cave;
static BYTE g_gapPatch[12];
static BYTE g_ersPatch[12];
static BYTE g_clipPatch[19];
static BYTE g_ovtPatch[33];

// lu par la cave ERS : voitures en Overtake Mode (par index) et réglages du super clipping
struct ErsConfig {
    volatile BYTE boost[CARS];   // +0x00 Overtake Mode
    volatile LONG clipOn;        // +0x20
    float limit;                 // +0x24 m/s
    float limitBoost;            // +0x28 m/s
    float harvest;               // +0x2C batterie par appel
    volatile BYTE defend[CARS];  // +0x30 bataille : voiture à moins d'1 s devant ou derrière (stratégie RÉSERVE)
    float limitLiftCoast;        // +0x50 m/s (stratégie LIFT & COAST)
    float one;                   // +0x54 1.0 : quantité de déploiement pleine
    BYTE* volatile lastCar;      // +0x58 dernier objet voiture vu par la cave (pour trouver le tableau)
    float step;                  // +0x60 1/30 : part du débit appliquée à la batterie à chaque appel (constante du jeu)
    volatile float credit[CARS]; // +0x64 énergie Overtake Mode restante (0..0,125), en plus de la batterie
    volatile LONG rule2026;      // +0xE4 règle 2026 active (0 après F7 : le test DRS d'origine reprend)
    float minSpeedBoost;         // +0xE8 m/s : le crédit Overtake Mode ne se dépense qu'au-dessus (superclipping.ini)
    volatile BYTE assist[CARS];  // +0xEC avantage au dépassement (point 7) : sur overtake_distance après la détection
    volatile BYTE push[CARS];    // +0x10C déploiement pour le chrono (point 10) : à fond sur la batterie en accélération
};
static_assert(offsetof(ErsConfig, defend) == 0x30 && offsetof(ErsConfig, limitLiftCoast) == 0x50 && offsetof(ErsConfig, one) == 0x54 &&
              offsetof(ErsConfig, lastCar) == 0x58 && offsetof(ErsConfig, step) == 0x60 && offsetof(ErsConfig, credit) == 0x64 &&
              offsetof(ErsConfig, rule2026) == 0xE4 && offsetof(ErsConfig, minSpeedBoost) == 0xE8 &&
              offsetof(ErsConfig, assist) == 0xEC && offsetof(ErsConfig, push) == 0x10C, "décalages lus par les caves");
static ErsConfig g_cfg = { {}, 0, 290.0f / 3.6f, 337.0f / 3.6f, 0.002f, {}, 250.0f / 3.6f, 1.0f, nullptr, 1.0f / 30.0f, {}, 0,
                           250.0f / 3.6f, {}, {} };
static float g_pushBoost = 0.40f;     // BOOST : déploiement pour le chrono jusqu'à cette batterie (deploiement_boost)
static float g_pushBalanced = 0.60f;  // ÉQUILIBRÉ : idem (deploiement_equilibre) ; reprise 15 points au-dessus
static BYTE* g_assistCar[CARS];       // objet voiture de l'avantage au dépassement
static float g_assistEnd[CARS];       // distance (+0x194) à laquelle il s'arrête
static float g_assistDist = 2000.0f;  // m après la détection (overtake_distance)
static bool g_harvestOn = false;      // super clipping : recharge au-dessus de la limite
#define g_boost g_cfg.boost           // Overtake Mode utilisé maintenant (crédit et voiture devant proche, UpdateGaps)
static volatile BYTE g_owned[CARS];   // crédit Overtake Mode reçu, pas encore dépensé ni expiré
static BYTE g_using[CARS];            // Overtake Mode utilisé sur cette ligne droite (jusqu'au freinage)
static bool g_onBattery = true;       // crédit épuisé : l'Overtake Mode continue sur la batterie (overtake_batterie)
static float g_batteryBudget = 0.20f; // batterie dépensée au plus après le crédit, par utilisation (overtake_batterie_max)
static float g_batteryStart[CARS];    // batterie quand le crédit s'est épuisé (< 0 : pas encore)
static float g_attackGap = 0.6f;      // s : écart avec la voiture devant sous lequel le crédit sert (overtake_ecart_attaque)
struct Boost { BYTE* car; float stop; int endLap; };  // stop : seuil de batterie, seulement sans cave de recharge
static Boost g_boostInfo[CARS];

static void Log(const char* fmt, ...) {
    wchar_t path[MAX_PATH];
    swprintf_s(path, L"%s\\patch.log", g_dir);
    // _wfsopen partagé : _wfopen_s refuse tout partage, et le journal se perdait dès qu'un autre programme le
    // gardait ouvert (tail -F pendant une mesure)
    FILE* f = _wfsopen(path, L"a", _SH_DENYNO);
    if (!f) return;
    SYSTEMTIME t;
    GetLocalTime(&t);
    fprintf(f, "%04d-%02d-%02d %02d:%02d:%02d ", t.wYear, t.wMonth, t.wDay, t.wHour, t.wMinute, t.wSecond);
    va_list args;
    va_start(args, fmt);
    vfprintf(f, fmt, args);
    va_end(args);
    fprintf(f, "\n");
    fclose(f);
}

/// superclipping.ini : actif=0/1 (super clipping : recharge au-dessus de la limite), vitesse_max=290,
/// vitesse_max_overtake=337 (km/h : limite de déploiement, toujours active avec la règle 2026), recharge=0.002,
/// overtake_vitesse_min=250 (km/h : le crédit Overtake Mode ne se dépense qu'au-dessus, pour que le bonus dure jusqu'au
/// bout de la ligne droite, là où le jeu évalue les dépassements), overtake_distance=2000 (m : durée de l'avantage au
/// dépassement après la détection), overtake_ecart_attaque=0.6 (s : le crédit ne sert qu'avec la voiture devant plus
/// près que ça), overtake_batterie=1 (crédit épuisé : pleine puissance sur la batterie jusqu'au freinage ; 0 : fin
/// avec le crédit), overtake_batterie_max=0.20 (batterie dépensée au plus après le crédit, par utilisation),
/// deploiement_boost=0.40 et deploiement_equilibre=0.60 (déploiement pour le chrono jusqu'à cette batterie). Sans fichier : valeurs par défaut, sans recharge.
static void ReadClipConfig() {
    static bool first = true;
    int on = 0, onBattery = 1;
    float limit = 290.0f, limitBoost = 337.0f, harvest = 0.002f, minBoost = 250.0f, assistDist = 2000.0f, attackGap = 0.6f, batteryBudget = 0.20f, pushBoost = 0.40f, pushBalanced = 0.60f;
    wchar_t path[MAX_PATH];
    swprintf_s(path, L"%s\\superclipping.ini", g_dir);
    FILE* f = nullptr;
    if (_wfopen_s(&f, path, L"r") == 0 && f) {
        char line[128];
        while (fgets(line, sizeof(line), f)) {
            sscanf_s(line, "actif=%d", &on);
            sscanf_s(line, "vitesse_max=%f", &limit);
            sscanf_s(line, "vitesse_max_overtake=%f", &limitBoost);
            sscanf_s(line, "recharge=%f", &harvest);
            sscanf_s(line, "overtake_vitesse_min=%f", &minBoost);
            sscanf_s(line, "overtake_distance=%f", &assistDist);
            sscanf_s(line, "overtake_ecart_attaque=%f", &attackGap);
            sscanf_s(line, "overtake_batterie=%d", &onBattery);
            sscanf_s(line, "overtake_batterie_max=%f", &batteryBudget);
            sscanf_s(line, "deploiement_boost=%f", &pushBoost);
            sscanf_s(line, "deploiement_equilibre=%f", &pushBalanced);
        }
        fclose(f);
    }
    bool limitChanged = first || !g_cfg.clipOn || limit / 3.6f != g_cfg.limit || limitBoost / 3.6f != g_cfg.limitBoost;
    bool harvestChanged = first || (on != 0) != g_harvestOn || (on && harvest != g_cfg.harvest);
    bool minChanged = first || minBoost / 3.6f != g_cfg.minSpeedBoost;
    bool distChanged = first || assistDist != g_assistDist;
    bool gapChanged = first || attackGap != g_attackGap;
    bool pushChanged = first || pushBoost != g_pushBoost || pushBalanced != g_pushBalanced;
    bool batteryChanged = first || (onBattery != 0) != g_onBattery || batteryBudget != g_batteryBudget;
    first = false;
    g_cfg.limit = limit / 3.6f;
    g_cfg.limitBoost = limitBoost / 3.6f;
    g_harvestOn = on != 0;
    g_cfg.harvest = on ? harvest : 0.0f;  // la cave ajoute 0 au-dessus de la limite : limite seule
    g_cfg.minSpeedBoost = minBoost / 3.6f;
    g_assistDist = assistDist;
    g_attackGap = attackGap > 0.05f && attackGap <= 1.0f ? attackGap : 0.6f;
    g_onBattery = onBattery != 0;
    g_pushBoost = pushBoost >= 0.0f && pushBoost <= 1.0f ? pushBoost : 0.40f;
    g_pushBalanced = pushBalanced >= 0.0f && pushBalanced <= 1.0f ? pushBalanced : 0.60f;
    g_batteryBudget = batteryBudget >= 0.0f && batteryBudget <= 1.0f ? batteryBudget : 0.20f;
    g_cfg.clipOn = 1;  // limite de vitesse (caves ERS et de recharge)
    if (limitChanged) Log("limite 2026 : plus de déploiement au-delà de %.0f km/h (%.0f en Overtake Mode)", limit, limitBoost);
    if (harvestChanged) {
        if (on) Log("super clipping : actif, recharge %.4f au-dessus de la limite", harvest);
        else Log("super clipping : désactivé (limite de vitesse gardée, sans recharge)");
    }
    if (minChanged) Log("Overtake Mode : crédit dépensé seulement au-dessus de %.0f km/h", minBoost);
    if (distChanged) Log("Overtake Mode : avantage au dépassement sur %.0f m après la détection", assistDist);
    if (gapChanged) Log("Overtake Mode : crédit utilisé seulement à moins de %.1f s de la voiture devant", attackGap);
    if (pushChanged) Log("déploiement pour le chrono : BOOST jusqu'à %.0f %% de batterie, ÉQUILIBRÉ jusqu'à %.0f %%",
                         g_pushBoost * 100, g_pushBalanced * 100);
    if (batteryChanged) {
        if (onBattery) Log("Overtake Mode : crédit épuisé, pleine puissance sur la batterie jusqu'au freinage (%.0f %% de batterie au plus)",
                           g_batteryBudget * 100);
        else Log("Overtake Mode : fin dès que le crédit est épuisé");
    }
}

static bool StraightOff() {
    wchar_t path[MAX_PATH];
    swprintf_s(path, L"%s\\straight_off.txt", g_dir);
    return GetFileAttributesW(path) != INVALID_FILE_ATTRIBUTES;
}

static bool Readable(const void* p, size_t n) {
    MEMORY_BASIC_INFORMATION mbi = {};
    return VirtualQuery(p, &mbi, sizeof(mbi)) && mbi.State == MEM_COMMIT &&
           (BYTE*)p + n <= (BYTE*)mbi.BaseAddress + mbi.RegionSize &&
           (mbi.Protect & (PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY | PAGE_READWRITE));
}

/// tableaux aéro 2026 dans le CarStatsDataAsset dont le script Lua a noté l'adresse (carstats.txt)
static void ApplyAeroTables() {
    static DWORD64 logged = 0;  // dernier objet signalé, pour ne pas répéter le journal
    wchar_t path[MAX_PATH];
    swprintf_s(path, L"%s\\carstats.txt", g_dir);
    FILE* f = nullptr;
    if (_wfopen_s(&f, path, L"r") != 0 || !f) return;
    DWORD64 addr = 0;
    fscanf_s(f, "%llx", &addr);
    fclose(f);
    if (!addr) return;
    BYTE* obj = (BYTE*)addr;
    bool ok = Readable(obj + STATS_DRS_TOP, 16) && Readable(obj + STATS_AERO, 48) && Readable(obj + STATS_DIRTY, 48);
    double* aero = (double*)(obj + STATS_AERO);
    double* dirty = (double*)(obj + STATS_DIRTY);
    if (ok) {
        const double* drs = (const double*)(obj + STATS_DRS_TOP);
        ok = fabs(drs[0] - 1.03) < 1e-6 && fabs(drs[1] - 1.06) < 1e-6;
        for (int i = 0; ok && i < 6; i++) ok = aero[i] > 0.5 && aero[i] < 1.5 && dirty[i] > 0.5 && dirty[i] < 1.5;
    }
    if (!ok) {
        if (logged != addr) Log("tableaux aéro : CarStatsDataAsset inattendu (objet %llX), rien n'est écrit", addr);
        logged = addr;
        return;
    }
    bool same = true;
    for (int i = 0; i < 6; i++) same = same && aero[i] == AERO_2026[i] && dirty[i] == DIRTY_2026[i];
    if (same) {
        if (logged != addr) Log("tableaux aéro 2026 déjà en place (objet %llX)", addr);
        logged = addr;
        return;
    }
    Log("tableaux aéro 2026 écrits (objet %llX) : aéro %.3f/%.3f %.3f/%.3f %.3f/%.3f, air sale %.2f/%.2f -> 2026",
        addr, aero[0], aero[1], aero[2], aero[3], aero[4], aero[5], dirty[0], dirty[1]);
    for (int i = 0; i < 6; i++) {
        *(volatile double*)(aero + i) = AERO_2026[i];
        *(volatile double*)(dirty + i) = DIRTY_2026[i];
    }
    logged = addr;
}

/// écrit du code du jeu ; une écriture de 2 octets alignés est atomique pour les threads qui l'exécutent
static bool WriteCode(BYTE* site, const BYTE* bytes, size_t n) {
    DWORD old;
    if (!VirtualProtect(site, n, PAGE_EXECUTE_READWRITE, &old)) return false;
    if (n == 2) *(volatile WORD*)site = *(const WORD*)bytes;
    else memcpy(site, bytes, n);
    VirtualProtect(site, n, old, &old);
    FlushInstructionCache(GetCurrentProcess(), site, n);
    return true;
}

/// remplace les 12 octets du test d'1 s sans jamais laisser une instruction à moitié écrite :
/// d'abord un saut court (2 octets), puis la fin, puis le début
static bool SwapGap(const BYTE* bytes) {
    BYTE* site = g_exe + GAP_RVA;
    return WriteCode(site, JMP_OVER, 2) && WriteCode(site + 2, bytes + 2, 10) && WriteCode(site, bytes, 2);
}

static bool BuildCave() {
    g_cave = (BYTE*)VirtualAlloc(nullptr, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!g_cave) return false;
    BYTE* p = g_cave;
    auto put = [&](std::initializer_list<BYTE> b) { for (BYTE x : b) *p++ = x; };
    auto put64 = [&](DWORD64 v) { memcpy(p, &v, 8); p += 8; };
    put({ 0x0F, 0x28, 0xC6 });              // movaps xmm0, xmm6
    put({ 0xF3, 0x0F, 0x5C, 0x03 });        // subss  xmm0, [rbx]
    put({ 0x0F, 0x2F, 0xC7 });              // comiss xmm0, xmm7
    put({ 0x77, 0x00 });                    // ja skip (corrigé plus bas)
    BYTE* ja = p - 1;
    put({ 0x51 });                          // push rcx
    put({ 0x48, 0xB8 }); put64((DWORD64)&g_ring);  // mov rax, &g_ring
    put({ 0x8B, 0x08 });                    // mov ecx, [rax]
    put({ 0x83, 0xE1, RING - 1 });          // and ecx, RING-1
    put({ 0x48, 0x89, 0x7C, 0xC8, 0x08 });  // mov [rax + rcx*8 + 8], rdi
    put({ 0xF0, 0xFF, 0x00 });              // lock inc dword [rax]
    put({ 0x59 });                          // pop rcx
    *ja = (BYTE)(p - (ja + 1));             // skip:
    put({ 0x48, 0xB8 }); put64((DWORD64)(g_exe + GAP_RETURN_RVA));  // mov rax, 230C44C
    put({ 0xFF, 0xE0 });                    // jmp rax
    FlushInstructionCache(GetCurrentProcess(), g_cave, p - g_cave);

    g_gapPatch[0] = 0x48; g_gapPatch[1] = 0xB8;  // mov rax, cave
    DWORD64 cave = (DWORD64)g_cave;
    memcpy(g_gapPatch + 2, &cave, 8);
    g_gapPatch[10] = 0xFF; g_gapPatch[11] = 0xE0;  // jmp rax

    // cave ERS
    BYTE* ers = p = g_cave + 0x100;
    bool jumpsOk = true;  // un saut court qui déborde (> 127 octets) ne doit jamais être posé
    auto jcc = [&](BYTE op) { put({ op, 0x00 }); return p - 1; };
    auto land = [&](BYTE* j) { ptrdiff_t d = p - (j + 1); if (d > 127) jumpsOk = false; *j = (BYTE)d; };
    // sauts longs (rel32) pour les blocs qui dépassent 127 octets
    auto jcc32 = [&](BYTE op) { if (op == 0xEB) put({ 0xE9, 0, 0, 0, 0 }); else put({ 0x0F, (BYTE)(op + 0x10), 0, 0, 0, 0 }); return p - 4; };
    auto land32 = [&](BYTE* j) { INT32 d = (INT32)(p - (j + 4)); memcpy(j, &d, 4); };
    put({ 0x51 });                          // push rcx
    put({ 0x0F, 0xB6, 0x8B }); { DWORD d = CAR_INDEX; memcpy(p, &d, 4); p += 4; }  // movzx ecx, byte [rbx+0x710]
    put({ 0x83, 0xE1, CARS - 1 });          // and ecx, CARS-1
    put({ 0x48, 0xB8 }); put64((DWORD64)&g_cfg);  // mov rax, &g_cfg
    put({ 0x48, 0x89, 0x58, 0x58 });        // mov [rax+0x58], rbx (lastCar)    // RÉSERVE (Top-Up) : pas de déploiement, sauf pour attaquer (Overtake Mode) ou défendre
    put({ 0x80, 0xBB, 0xF2, 0x0E, 0x00, 0x00, 0x03 });  // cmp byte [rbx+0xEF2], 3
    BYTE* notRes = jcc(0x75);               // jnz notRes
    put({ 0x80, 0x3C, 0x08, 0x00 });        // cmp byte [rax+rcx], 0 (Overtake Mode)
    BYTE* r1 = jcc(0x75);                   // jnz attack
    put({ 0x80, 0x7C, 0x08, 0x30, 0x00 });  // cmp byte [rax+rcx+0x30], 0 (défense)
    BYTE* r2 = jcc(0x75);                   // jnz attack
    put({ 0xB2, 0x01 });                    // mov dl, 1 : garder l'énergie
    BYTE* r3 = jcc(0xEB);                   // jmp limits
    land(notRes);
    put({ 0x80, 0x3C, 0x08, 0x00 });        // cmp byte [rax+rcx], 0 (Overtake Mode)
    BYTE* r4 = jcc(0x74);                   // jz limits
    land(r1); land(r2);                     // attack:
    // on déploie même si l'IA voulait recharger (en Top-Up elle recharge presque toujours), mais pas au freinage
    put({ 0x40, 0x84, 0xFF });              // test dil, dil : ERS disponible ?
    BYTE* r5 = jcc(0x74);                   // jz limits
    put({ 0x0F, 0x57, 0xC0 });              // xorps xmm0, xmm0
    put({ 0x0F, 0x2F, 0x83, 0x9C, 0x01, 0x00, 0x00 });  // comiss xmm0, [rbx+0x19C] (accélération)
    BYTE* r6 = jcc(0x77);                   // ja limits (freinage)
    // crédit restant ? (mesuré à Monza : entre l'épuisement du crédit et la fin du bonus par le thread, jusqu'à
    // 100 ms, la voiture dépensait jusqu'à 9 % de vraie batterie) ; la défense RÉSERVE passe par un autre chemin
    put({ 0x80, 0x3C, 0x08, 0x00 });        // cmp byte [rax+rcx], 0 (Overtake Mode ?)
    BYTE* r7 = jcc(0x74);                   // jz deploy (défense : pas de crédit à vérifier)
    put({ 0x0F, 0x2F, 0x44, 0x88, 0x64 });  // comiss xmm0 (0), [rax+rcx*4+0x64] (crédit)
    BYTE* r8 = jcc(0x73);                   // jae limits (crédit épuisé)
    // sous overtake_vitesse_min, le crédit attend la ligne droite : ne pas forcer un déploiement sur la batterie
    put({ 0xF3, 0x0F, 0x10, 0x80, 0xE8, 0x00, 0x00, 0x00 });  // movss xmm0, [rax+0xE8] (vitesse minimale)
    put({ 0x0F, 0x2F, 0x83, 0x98, 0x01, 0x00, 0x00 });  // comiss xmm0, [rbx+0x198] (vitesse)
    BYTE* r9 = jcc(0x77);                   // ja limits (trop lent)
    land(r7);                               // deploy:
    put({ 0xC6, 0x45, 0x38, 0x00 });        // mov byte [rbp+0x38], 0 : pas de recharge
    put({ 0x32, 0xD2 });                    // xor dl, dl : déployer
    // à pleine puissance : la quantité vient de la décision de l'IA ([rbp+0x48] -> xmm4, puis xmm3 = quantité *
    // débit de déploiement [r15+0x144]) ; quand l'IA ne voulait pas déployer elle vaut 0, et le déploiement
    // forcé ne consommait rien et ne donnait rien
    put({ 0xF3, 0x41, 0x0F, 0x10, 0x9F, 0x44, 0x01, 0x00, 0x00 });  // movss xmm3, [r15+0x144]
    put({ 0xF3, 0x0F, 0x10, 0x60, 0x54 });  // movss xmm4, [rax+0x54] (1.0)
    land(r3); land(r4); land(r5); land(r6); land(r8); land(r9);  // limits:
    // vitesse au-delà de laquelle on ne déploie plus : LIFT & COAST toujours, sinon super clipping
    put({ 0x80, 0xBB, 0xF2, 0x0E, 0x00, 0x00, 0x01 });  // cmp byte [rbx+0xEF2], 1
    BYTE* l1 = jcc(0x75);                   // jnz notLnc
    put({ 0xF3, 0x0F, 0x10, 0x40, 0x50 });  // movss xmm0, [rax+0x50]
    BYTE* l2 = jcc(0xEB);                   // jmp have
    land(l1);                               // notLnc:
    put({ 0x83, 0x78, 0x20, 0x00 });        // cmp dword [rax+0x20], 0
    BYTE* l3 = jcc(0x74);                   // jz done
    put({ 0xF3, 0x0F, 0x10, 0x40, 0x24 });  // movss xmm0, [rax+0x24]
    put({ 0x80, 0x3C, 0x08, 0x00 });        // cmp byte [rax+rcx], 0
    BYTE* l4 = jcc(0x74);                   // jz have
    put({ 0xF3, 0x0F, 0x10, 0x40, 0x28 });  // movss xmm0, [rax+0x28] (Overtake Mode)
    land(l2); land(l4);                     // have:
    put({ 0xF3, 0x0F, 0x10, 0x8B, 0x98, 0x01, 0x00, 0x00 });  // movss xmm1, [rbx+0x198] (vitesse)
    put({ 0x0F, 0x2F, 0xC8 });              // comiss xmm1, xmm0
    BYTE* l5 = jcc(0x76);                   // jbe done
    put({ 0xB2, 0x01 });                    // mov dl, 1 : plus de déploiement
    land(l3); land(l5);                     // done:
    put({ 0x59 });                          // pop rcx
    put({ 0x0F, 0xB6, 0x45, 0x38 });        // movzx eax, byte [rbp+0x38]
    put({ 0xF3, 0x0F, 0x10, 0x2D });        // movss xmm5, [rip+k]
    BYTE* disp = p; p += 4;
    put({ 0xFF, 0x25, 0, 0, 0, 0 }); put64((DWORD64)(g_exe + ERS_RETURN_RVA));  // jmp [rip] -> 23084CA
    // constante d'origine lue à l'adresse visée par le movss du jeu
    BYTE* k = p;
    INT32 orig; memcpy(&orig, ERS_ORIGINAL + 8, 4);
    memcpy(k, g_exe + ERS_RVA + 12 + orig, 4); p += 4;
    INT32 rel = (INT32)(k - (disp + 4)); memcpy(disp, &rel, 4);
    FlushInstructionCache(GetCurrentProcess(), g_cave, p - g_cave);

    g_ersPatch[0] = 0x48; g_ersPatch[1] = 0xB8;  // mov rax, cave ERS
    DWORD64 e = (DWORD64)ers;
    memcpy(g_ersPatch + 2, &e, 8);
    g_ersPatch[10] = 0xFF; g_ersPatch[11] = 0xE0;  // jmp rax

    // cave de recharge (super clipping)
    if (p > g_cave + 0x200) jumpsOk = false;
    BYTE* clip = p = g_cave + 0x200;
    put({ 0x4C, 0x8B, 0xBC, 0x24, 0xE8, 0x00, 0x00, 0x00 });  // mov r15, [rsp+0xE8] (d'origine)
    put({ 0x51 });                          // push rcx
    put({ 0x48, 0xB8 }); put64((DWORD64)&g_cfg);  // mov rax, &g_cfg
    put({ 0x0F, 0xB6, 0x8B }); { DWORD d = CAR_INDEX; memcpy(p, &d, 4); p += 4; }  // movzx ecx, byte [rbx+0x710]
    put({ 0x83, 0xE1, CARS - 1 });          // and ecx, CARS-1
    // vitesse limite -> xmm1 : LIFT & COAST toujours, sinon super clipping s'il est actif
    put({ 0x80, 0xBB, 0xF2, 0x0E, 0x00, 0x00, 0x01 });  // cmp byte [rbx+0xEF2], 1 (LIFT & COAST)
    BYTE* c0 = jcc(0x75);                   // jnz notLnc
    put({ 0xF3, 0x0F, 0x10, 0x48, 0x50 });  // movss xmm1, [rax+0x50]
    BYTE* c5 = jcc(0xEB);                   // jmp cmp
    land(c0);                               // notLnc:
    put({ 0x83, 0x78, 0x20, 0x00 });        // cmp dword [rax+0x20], 0
    BYTE* c1 = jcc(0x74);                   // jz force (pas de limite)
    put({ 0xF3, 0x0F, 0x10, 0x48, 0x24 });  // movss xmm1, [rax+0x24]
    put({ 0x80, 0x3C, 0x08, 0x00 });        // cmp byte [rax+rcx], 0
    BYTE* c2 = jcc(0x74);                   // jz cmp
    put({ 0xF3, 0x0F, 0x10, 0x48, 0x28 });  // movss xmm1, [rax+0x28] (Overtake Mode)
    land(c2); land(c5);                     // cmp:
    put({ 0x0F, 0x2F, 0x8B, 0x98, 0x01, 0x00, 0x00 });  // comiss xmm1, [rbx+0x198] (vitesse)
    BYTE* c3 = jcc(0x73);                   // jae force (limite >= vitesse)
    // au-dessus de la limite : recharge, sauf au freinage
    put({ 0x0F, 0x57, 0xC9 });              // xorps xmm1, xmm1
    put({ 0x0F, 0x2F, 0x8B, 0x9C, 0x01, 0x00, 0x00 });  // comiss xmm1, [rbx+0x19C] (accélération)
    BYTE* c4 = jcc32(0x77);                   // ja done (freinage)
    put({ 0xF3, 0x44, 0x0F, 0x58, 0x60, 0x2C });  // addss xmm12, [rax+0x2C] : recharge
    BYTE* c6 = jcc32(0xEB);                   // jmp done
    land(c1); land(c3);                     // force:
    // Overtake Mode : déploiement forcé à pleine puissance, payé par le crédit tant qu'il en reste, puis par la batterie
    // (le thread ne laisse g_cfg.boost allumé sans crédit que jusqu'au freinage de la ligne droite)
    put({ 0x80, 0x3C, 0x08, 0x00 });        // cmp byte [rax+rcx], 0 (Overtake Mode)
    BYTE* f0 = jcc(0x75);                   // jnz overtake
    // déploiement pour le chrono (point 10) : à fond, payé par la batterie, hors freinage, sous la limite de vitesse
    put({ 0x80, 0xBC, 0x08, 0x0C, 0x01, 0x00, 0x00, 0x00 });  // cmp byte [rax+rcx+0x10C], 0 (push)
    BYTE* p1 = jcc32(0x74);                   // jz done
    put({ 0x40, 0x84, 0xFF });              // test dil, dil : ERS disponible ?
    BYTE* p2 = jcc32(0x74);                   // jz done
    put({ 0x0F, 0x57, 0xC9 });              // xorps xmm1, xmm1
    put({ 0x0F, 0x2F, 0x8B, 0x9C, 0x01, 0x00, 0x00 });  // comiss xmm1, [rbx+0x19C] (accélération)
    BYTE* p3 = jcc32(0x77);                   // ja done (freinage)
    put({ 0x49, 0x8B, 0x55, 0x18 });        // mov rdx, [r13+0x18]
    put({ 0x48, 0x8B, 0x92, 0x10, 0xD6, 0x05, 0x00 });  // mov rdx, [rdx+0x5D610] (RaceSimDataAsset)
    put({ 0xF3, 0x0F, 0x10, 0x92, 0x44, 0x01, 0x00, 0x00 });  // movss xmm2, [rdx+0x144] (débit de déploiement, < 0)
    put({ 0xC6, 0x44, 0x24, 0x68, 0x03 });  // mov byte [rsp+0x60 (+8 : push rcx)], 3 : déploie
    put({ 0xF3, 0x0F, 0x11, 0x54, 0x24, 0x70 });  // movss [rsp+0x68 (+8)], xmm2 : débit
    BYTE* p4 = jcc32(0xEB);                   // jmp done
    land(f0);                               // overtake:
    put({ 0x40, 0x84, 0xFF });              // test dil, dil : ERS disponible ?
    BYTE* f2 = jcc32(0x74);                   // jz done
    put({ 0x0F, 0x57, 0xC9 });              // xorps xmm1, xmm1
    put({ 0x0F, 0x2F, 0x8B, 0x9C, 0x01, 0x00, 0x00 });  // comiss xmm1, [rbx+0x19C] (accélération)
    BYTE* f3 = jcc32(0x77);                   // ja done (freinage)
    put({ 0xF3, 0x0F, 0x10, 0x88, 0xE8, 0x00, 0x00, 0x00 });  // movss xmm1, [rax+0xE8] (vitesse minimale)
    put({ 0x0F, 0x2F, 0x8B, 0x98, 0x01, 0x00, 0x00 });  // comiss xmm1, [rbx+0x198] (vitesse)
    BYTE* f5 = jcc32(0x77);                   // ja done (trop lent : le crédit attend la ligne droite)
    put({ 0x49, 0x8B, 0x55, 0x18 });        // mov rdx, [r13+0x18]
    put({ 0x48, 0x8B, 0x92, 0x10, 0xD6, 0x05, 0x00 });  // mov rdx, [rdx+0x5D610] (RaceSimDataAsset)
    put({ 0xF3, 0x0F, 0x10, 0x92, 0x44, 0x01, 0x00, 0x00 });  // movss xmm2, [rdx+0x144] (débit de déploiement, < 0)
    put({ 0xC6, 0x44, 0x24, 0x68, 0x03 });  // mov byte [rsp+0x60 (+8 : push rcx)], 3 : déploie
    put({ 0xF3, 0x0F, 0x11, 0x54, 0x24, 0x70 });  // movss [rsp+0x68 (+8)], xmm2 : débit
    put({ 0xF3, 0x0F, 0x10, 0x4C, 0x88, 0x64 });  // movss xmm1, [rax+rcx*4+0x64] (crédit)
    put({ 0x0F, 0x2F, 0xCE });              // comiss xmm1, xmm6 (0)
    BYTE* f4 = jcc32(0x76);                   // jbe done (crédit épuisé : la batterie paie)
    put({ 0x0F, 0x28, 0xCA });              // movaps xmm1, xmm2
    put({ 0xF3, 0x0F, 0x59, 0x48, 0x60 });  // mulss xmm1, [rax+0x60] : variation de batterie de cet appel (< 0)
    put({ 0xF3, 0x44, 0x0F, 0x5C, 0xE1 });  // subss xmm12, xmm1 : la batterie ne baisse pas
    put({ 0xF3, 0x0F, 0x10, 0x44, 0x88, 0x64 });  // movss xmm0, [rax+rcx*4+0x64]
    put({ 0xF3, 0x0F, 0x58, 0xC1 });        // addss xmm0, xmm1 : le crédit baisse d'autant
    put({ 0xF3, 0x0F, 0x11, 0x44, 0x88, 0x64 });  // movss [rax+rcx*4+0x64], xmm0
    for (BYTE* j : { c4, c6, f2, f3, f4, f5, p1, p2, p3, p4 }) land32(j);  // done:
    put({ 0x59 });                          // pop rcx
    put({ 0x0F, 0x28, 0xCA });              // movaps xmm1, xmm2 (d'origine)
    put({ 0xF3, 0x0F, 0x59, 0x0D });        // mulss xmm1, [rip+k] (d'origine)
    BYTE* disp2 = p; p += 4;
    put({ 0xFF, 0x25, 0, 0, 0, 0 }); put64((DWORD64)(g_exe + CLIP_RETURN_RVA));  // jmp [rip] -> 2308580
    BYTE* k2 = p;
    INT32 orig2; memcpy(&orig2, CLIP_ORIGINAL + 15, 4);
    memcpy(k2, g_exe + CLIP_RETURN_RVA + orig2, 4); p += 4;
    memcpy((void*)&g_cfg.step, k2, 4);  // même constante (1/30) pour le décompte du crédit
    INT32 rel2 = (INT32)(k2 - (disp2 + 4)); memcpy(disp2, &rel2, 4);
    FlushInstructionCache(GetCurrentProcess(), g_cave, p - g_cave);

    g_clipPatch[0] = 0x48; g_clipPatch[1] = 0xB8;  // mov rax, cave de recharge
    DWORD64 c = (DWORD64)clip;
    memcpy(g_clipPatch + 2, &c, 8);
    g_clipPatch[10] = 0xFF; g_clipPatch[11] = 0xE0;  // jmp rax
    memset(g_clipPatch + 12, 0x90, 7);

    // cave de dépassement : bonus de probabilité pour l'attaquant en Overtake Mode
    if (p > g_cave + 0x400) jumpsOk = false;  // la cave de recharge ne doit pas chevaucher la suivante
    BYTE* ovt = p = g_cave + 0x400;
    put({ 0x0F, 0x5B, 0xC0 });              // cvtdq2ps xmm0, xmm0 (d'origine)
    put({ 0x48, 0xB8 }); put64((DWORD64)&g_cfg);  // mov rax, &g_cfg
    put({ 0x83, 0xB8, 0xE4, 0x00, 0x00, 0x00, 0x00 });  // cmp dword [rax+0xE4], 0 (règle 2026 ?)
    BYTE* o1 = jcc(0x74);                   // jz original
    put({ 0x41, 0x0F, 0xB6, 0x8E, 0x10, 0x07, 0x00, 0x00 });  // movzx ecx, byte [r14+0x710] (index de l'attaquant)
    put({ 0x83, 0xE1, CARS - 1 });          // and ecx, CARS-1
    put({ 0x0F, 0xB6, 0x8C, 0x08, 0xEC, 0x00, 0x00, 0x00 });  // movzx ecx, byte [rax+rcx+0xEC] : cl = avantage Overtake
    put({ 0x31, 0xC0 });                    // xor eax, eax : al = 0, le DRS du défenseur ne compte plus
    put({ 0xFF, 0x25, 0, 0, 0, 0 }); put64((DWORD64)(g_exe + OVT_RETURN_RVA));  // jmp [rip] -> 231FC1F
    land(o1);                               // original: test DRS du jeu (règle d'origine, F7)
    for (int i = 0; i < 33; i++) if (i < 20 || i >= 23) *p++ = OVT_ORIGINAL[i];  // sans le cvtdq2ps, déjà fait en tête de cave
    put({ 0xFF, 0x25, 0, 0, 0, 0 }); put64((DWORD64)(g_exe + OVT_RETURN_RVA));  // jmp [rip] -> 231FC1F
    FlushInstructionCache(GetCurrentProcess(), g_cave, p - g_cave);

    g_ovtPatch[0] = 0x48; g_ovtPatch[1] = 0xB8;  // mov rax, cave de dépassement
    DWORD64 o = (DWORD64)ovt;
    memcpy(g_ovtPatch + 2, &o, 8);
    g_ovtPatch[10] = 0xFF; g_ovtPatch[11] = 0xE0;  // jmp rax
    memset(g_ovtPatch + 12, 0x90, 21);
    if (!jumpsOk) {
        Log("caves : un saut court déborde, rien n'est modifié (erreur de construction de la DLL)");
        return false;
    }
    return true;
}

static bool g_ersOk = false;
static bool g_clipOk = false;
static bool g_ovtOk = false;

static bool CheckGame() {
    BYTE* lap = g_exe + LAP_RVA;
    BYTE* gap = g_exe + GAP_RVA;
    if (!Readable(lap - 6, 8) || !Readable(gap, 12)) {
        Log("adresses absentes : ce n'est pas F1 Manager 2024 v1.11, rien n'est modifié");
        return false;
    }
    bool lapOk = memcmp(lap - 6, LAP_CONTEXT, 6) == 0 &&
                 (memcmp(lap, LAP_ORIGINAL, 2) == 0 || memcmp(lap, NOP2, 2) == 0);
    bool gapOk = memcmp(gap, GAP_ORIGINAL, 12) == 0 || memcmp(gap, GAP_OLD_PATCH, 12) == 0;
    BYTE* ers = g_exe + ERS_RVA;
    bool ersOk = Readable(ers - 6, 18) && memcmp(ers - 6, ERS_CONTEXT, 6) == 0 && memcmp(ers, ERS_ORIGINAL, 12) == 0;
    if (!ersOk) Log("mise à jour ERS inattendue : Overtake Mode ajoutera à la batterie sans forcer le déploiement");
    g_ersOk = ersOk;
    BYTE* clip = g_exe + CLIP_RVA;
    g_clipOk = ersOk && Readable(clip, 19) && memcmp(clip, CLIP_ORIGINAL, 19) == 0;
    if (ersOk && !g_clipOk) Log("calcul de batterie inattendu : super clipping sans recharge, Overtake Mode ajouté à la batterie (borné à 100 %%)");
    BYTE* ovt = g_exe + OVT_RVA;
    g_ovtOk = Readable(ovt, 33) && memcmp(ovt, OVT_ORIGINAL, 33) == 0;
    if (!g_ovtOk) Log("évaluation de dépassement inattendue : pas de bonus de probabilité pour l'Overtake Mode");
    if (!lapOk || !gapOk) {
        Log("octets inattendus (tour %02X %02X, écart %02X %02X %02X) : autre version du jeu ou autre mod, "
            "rien n'est modifié", lap[0], lap[1], gap[0], gap[10], gap[11]);
        return false;
    }
    return true;
}

static bool Apply(bool on) {
    BYTE* lap = g_exe + LAP_RVA;
    if (!WriteCode(lap, on ? NOP2 : LAP_ORIGINAL, 2)) return false;
    return SwapGap(on ? g_gapPatch : GAP_ORIGINAL);
}

/// vide la file des voitures à moins d'1 s : crédit de 12,5 % d'énergie, une fois par tour (ajouté à la batterie,
/// bornée à 1,0, seulement si la cave de recharge n'a pas pu être posée)
static void GrantOvertake(LONG& read) {
    static BYTE* lastCar[RING];
    static int lastLap[RING];
    LONG written = g_ring.written;
    if (written - read > RING) read = written - RING;
    for (; read < written; read++) {
        BYTE* car = g_ring.cars[read & (RING - 1)];
        if (!Readable(car + CAR_LAPS, 4) || !Readable(car + CAR_BATTERY, 4) || !Readable(car + CAR_DIST, 4)) continue;
        int lap = *(int*)(car + CAR_LAPS);
        // pas d'Overtake Mode dans les 2 tours qui suivent le départ ou une relance : toute la grille
        // est à moins d'1 s et le déploiement forcé provoquait des accrochages (drapeaux rouges)
        if (!Readable(car + CAR_DRS_LAP, 4) || lap < *(int*)(car + CAR_DRS_LAP)) continue;
        int idx = car[CAR_INDEX] & (CARS - 1);
        // avantage au dépassement : à chaque détection à moins d'1 s, sur g_assistDist mètres ; le crédit d'énergie
        // reste limité à un par tour (les 0,5 MJ du règlement)
        float dist = *(float*)(car + CAR_DIST);
        bool seen = g_cfg.assist[idx] && g_assistCar[idx] == car && dist < g_assistEnd[idx] - g_assistDist + 100.0f;
        if (!seen) g_assistEnd[idx] = dist + g_assistDist;  // même détection vue deux fois : on garde la première
        g_assistCar[idx] = car;
        g_cfg.assist[idx] = 1;
        int slot = -1;
        for (int i = 0; i < RING; i++) {
            if (lastCar[i] == car) { slot = i; break; }
            if (slot < 0 && !lastCar[i]) slot = i;
        }
        if (slot < 0) slot = 0;
        if (lastCar[slot] == car && lastLap[slot] == lap) {  // crédit déjà reçu ce tour-ci
            if (!seen) Log("Overtake Mode : voiture %d, tour %d, avantage au dépassement renouvelé (crédit déjà reçu ce tour)", idx, lap);
            continue;
        }
        lastCar[slot] = car;
        lastLap[slot] = lap;
        float* battery = (float*)(car + CAR_BATTERY);
        if (g_clipOk) {
            g_cfg.credit[idx] = OVERTAKE_ENERGY;
            g_boostInfo[idx] = { car, 0.0f, lap + 1 };
            g_owned[idx] = 1;
            g_batteryStart[idx] = -1.0f;
            Log("Overtake Mode : voiture %d, tour %d, crédit 12,5 %% (batterie %.0f%%), utilisé à moins de %.1f s de la voiture devant", idx, lap, *battery * 100, g_attackGap);
            continue;
        }
        float before = *battery;
        float after = before + OVERTAKE_ENERGY;
        if (after > 1.0f) after = 1.0f;
        *battery = after;
        float stop = after - OVERTAKE_ENERGY;
        g_cfg.credit[idx] = OVERTAKE_ENERGY;  // jamais décompté sans cave de recharge : la cave ERS le voit > 0
        g_boostInfo[idx] = { car, stop > 0.0f ? stop : 0.0f, lap + 1 };
        g_owned[idx] = 1;
        g_batteryStart[idx] = -1.0f;
        Log("Overtake Mode : voiture %d, tour %d, batterie %.0f%% -> %.0f%%", idx, lap, before * 100, after * 100);
    }
}

/// tableau des voitures de la simulation, retrouvé depuis le dernier objet voiture vu par la cave ERS ;
/// cars[i] = objet d'index i, ou nullptr (emplacements vides en fin de grille, index 0) ; faux si rien de lisible
static bool FindCars(BYTE* cars[GRID]) {
    for (int i = 0; i < GRID; i++) cars[i] = nullptr;
    BYTE* last = g_cfg.lastCar;
    if (!last || !Readable(last + CAR_INDEX, 1)) return false;
    int idx = last[CAR_INDEX];
    if (idx >= GRID) return false;
    BYTE* base = last - (DWORD64)idx * CAR_STRIDE;
    for (int i = 0; i < GRID; i++) {
        BYTE* c = base + (DWORD64)i * CAR_STRIDE;
        if (!Readable(c, CAR_STRIDE)) return false;
        if (c[CAR_INDEX] == i) cars[i] = c;
    }
    return true;
}

/// état pour l'interface (point 8 de l'en-tête) : écrit dans un fichier temporaire puis remplacé d'un coup
static void WriteState(bool rule2026) {
    static bool dirOk = false;
    wchar_t dir[MAX_PATH], tmp[MAX_PATH], path[MAX_PATH];
    swprintf_s(dir, L"%s\\..\\..\\..\\..\\..\\Content\\UIGameface", g_dir);
    if (!dirOk) {
        CreateDirectoryW(dir, nullptr);
        swprintf_s(path, L"%s\\Reg2026", dir);
        dirOk = CreateDirectoryW(path, nullptr) || GetLastError() == ERROR_ALREADY_EXISTS;
        if (!dirOk) { Log("état interface : dossier Content\\UIGameface\\Reg2026 impossible (%lu)", GetLastError()); dirOk = true; return; }
    }
    swprintf_s(tmp, L"%s\\Reg2026\\state.tmp", dir);
    swprintf_s(path, L"%s\\Reg2026\\state.json", dir);
    static char buf[4096];
    static unsigned tick = 0;
    int n = sprintf_s(buf, sizeof(buf), "{\"t\":%u,\"rule\":%d,\"cars\":[", ++tick, rule2026 ? 1 : 0);
    BYTE* cars[GRID];
    bool first = true;
    if (rule2026 && FindCars(cars)) {
        for (int i = 0; i < GRID; i++) {
            BYTE* c = cars[i];
            if (!c) continue;
            int pos = *(int*)(c + CAR_POS);
            int lap = *(int*)(c + CAR_LAPS);
            float credit = g_cfg.credit[i];
            n += sprintf_s(buf + n, sizeof(buf) - n, "%s{\"i\":%d,\"p\":%d,\"l\":%d,\"c\":%.4f,\"b\":%d,\"a\":%d}",
                           first ? "" : ",", i, pos, lap, credit > 0.0f ? credit : 0.0f, g_boost[i] ? 1 : 0, g_cfg.assist[i] ? 1 : 0);
            first = false;
        }
    }
    n += sprintf_s(buf + n, sizeof(buf) - n, "]}");
    FILE* f = nullptr;
    if (_wfopen_s(&f, tmp, L"wb") != 0 || !f) return;
    fwrite(buf, 1, n, f);
    fclose(f);
    MoveFileExW(tmp, path, MOVEFILE_REPLACE_EXISTING);
}

/// Écarts entre voitures qui se suivent (distance divisée par la vitesse de celle qui suit), toutes les 100 ms :
/// - RÉSERVE : marque les voitures en bataille, à moins d'1 s d'une autre devant ou derrière (g_cfg.defend) ;
/// - Overtake Mode : une voiture qui a un crédit (g_owned) ne l'utilise (g_boost, lu par les caves : déploiement forcé
///   payé par le crédit, limite 337 km/h) que quand la voiture devant est à moins de g_attackGap ; sinon elle le garde
///   pour une meilleure occasion, jusqu'à la fin du tour suivant. Pendant l'utilisation, l'avantage au dépassement est
///   prolongé jusqu'à 300 m plus loin, pour couvrir l'évaluation en bout de ligne droite.
static void UpdateGaps() {
    BYTE def[CARS] = {};
    BYTE use[CARS] = {};
    BYTE* byPos[GRID] = {};
    BYTE* cars[GRID];
    if (FindCars(cars)) {
        for (int i = 0; i < GRID; i++) {
            BYTE* c = cars[i];
            if (!c) continue;
            int pos = *(int*)(c + CAR_POS);
            if (pos >= 0 && pos < GRID) byPos[pos] = c;  // +0x200 n'est pas « en course » (voir UpdateBoosts)
        }
        for (int pos = 0; pos + 1 < GRID; pos++) {
            BYTE* a = byPos[pos];
            BYTE* b = byPos[pos + 1];
            if (!a || !b) continue;
            float gap = *(float*)(a + CAR_DIST) - *(float*)(b + CAR_DIST);
            float v = *(float*)(b + CAR_SPEED);
            if (!(gap > 0.0f && v > 1.0f)) continue;
            float t = gap / v;
            int ib = b[CAR_INDEX] & (CARS - 1);
            // une fois lancé sur une ligne droite, il continue jusqu'à 1 s d'écart (sinon il se coupe et repart d'un
            // relevé à l'autre quand l'écart oscille autour du seuil)
            // sans crédit, pas sous 15 % de batterie (MinimumBattery de la spec : la voiture ne se vide pas pour attaquer)
            bool energy = g_cfg.credit[ib] > 0.0f || *(float*)(b + CAR_BATTERY) > 0.15f;
            if (g_owned[ib] && energy && t < (g_using[ib] ? 1.0f : g_attackGap)) {
                use[ib] = 1;
                g_using[ib] = 1;
                float dist = *(float*)(b + CAR_DIST);
                g_assistCar[ib] = b;
                if (!g_cfg.assist[ib] || g_assistEnd[ib] < dist + 300.0f) g_assistEnd[ib] = dist + 300.0f;
                g_cfg.assist[ib] = 1;
            }
            int lap = *(int*)(a + CAR_LAPS);
            if (lap < *(int*)(a + CAR_DRS_LAP)) continue;  // comme Overtake Mode : pas au départ ni aux relances
            // RÉSERVE : bataille à moins d'1 s, dans les deux sens. Avant le 2026-10-05, seule la voiture devant avait
            // le droit de déployer (défense) : l'attaquant en RÉSERVE sans Overtake Mode ne déployait plus du tout et
            // décrochait (vu en course : de 0,5 s à 2 s derrière, la grille passe 56 % du temps en Top-Up)
            if (t < 1.0f) {
                def[a[CAR_INDEX] & (CARS - 1)] = 1;
                def[ib] = 1;
            }
        }
    }
    for (int i = 0; i < CARS; i++) {
        g_cfg.defend[i] = def[i];
        g_boost[i] = use[i];
    }
    // déploiement pour le chrono (point 10) : BOOST jusqu'à g_pushBoost de batterie, ÉQUILIBRÉ jusqu'à g_pushBalanced,
    // reprise 15 points au-dessus ; ni en RÉSERVE ni en LIFT & COAST, ni avant le tour d'ouverture du DRS du jeu
    // (départ, relances : le déploiement forcé au départ provoquait des accrochages)
    static BYTE pushing[CARS];
    BYTE push[CARS] = {};
    for (int i = 0; g_cfg.rule2026 && i < GRID; i++) {
        BYTE* c = cars[i];
        if (!c) { pushing[i] = 0; continue; }
        BYTE strat = c[CAR_STRATEGY];
        float floor = strat == 2 ? g_pushBoost : strat == 0 ? g_pushBalanced : -1.0f;
        float battery = *(float*)(c + CAR_BATTERY);
        bool race = *(int*)(c + CAR_LAPS) >= *(int*)(c + CAR_DRS_LAP);
        if (floor < 0.0f || !race) pushing[i] = 0;
        else pushing[i] = battery > (pushing[i] ? floor : floor + 0.15f);
        push[i] = pushing[i];
    }
    for (int i = 0; i < CARS; i++) g_cfg.push[i] = push[i];
}

/// fin du crédit Overtake Mode : dépensé (ou batterie au seuil sans cave de recharge) ou tour suivant terminé
static void UpdateBoosts(bool clearAll) {
    for (int i = 0; i < CARS; i++) {
        if (!g_owned[i]) continue;
        Boost& b = g_boostInfo[i];
        bool end = clearAll || !Readable(b.car + CAR_MODE, 1) || !Readable(b.car + CAR_BATTERY, 4);
        if (!end) {
            int lap = *(int*)(b.car + CAR_LAPS);
            bool spent = g_clipOk ? g_cfg.credit[i] <= 0.0f : *(float*)(b.car + CAR_BATTERY) <= b.stop;
            // crédit épuisé : l'Overtake Mode continue sur la batterie jusqu'au freinage de la ligne droite (la vraie
            // règle donne la pleine puissance jusqu'à 337 km/h, les 0,5 MJ ne sont que l'énergie en plus)
            // freinage avec du crédit restant : il reste pour la ligne droite suivante, au seuil d'écart normal
            if (!spent && g_using[i] && Readable(b.car + CAR_ACCEL, 4) && *(float*)(b.car + CAR_ACCEL) < -10.0f)
                g_using[i] = 0;
            // borné à g_batteryBudget de batterie par utilisation : à pleine puissance, une ligne droite de Monza
            // (10 à 13 s) vidait plus d'une batterie (97 % -> 10 %, mesuré le 2026-10-05)
            if (spent && g_clipOk && g_onBattery && g_using[i] && Readable(b.car + CAR_ACCEL, 4)) {
                float battery = *(float*)(b.car + CAR_BATTERY);
                if (g_batteryStart[i] < 0.0f) g_batteryStart[i] = battery;
                bool braking = *(float*)(b.car + CAR_ACCEL) < -10.0f;
                bool budget = battery < g_batteryStart[i] - g_batteryBudget;
                spent = braking || budget;
                if (spent) Log("Overtake Mode : voiture %d, fin %s (batterie %.0f%% -> %.0f%%)", i,
                               braking ? "au freinage" : "du budget batterie", g_batteryStart[i] * 100, battery * 100);
            }
            // pas de test sur +0x200 : il vaut 0, 3 ou 4 dès que la voiture attaque ou défend (mesuré à Monza le
            // 2026-10-04), et le bonus se coupait au premier pas
            end = spent || lap > b.endLap;
        }
        if (end) {
            if (!clearAll && g_clipOk && g_cfg.credit[i] > 0.0f)
                Log("Overtake Mode : voiture %d, crédit non utilisé perdu (%.1f %%)", i, g_cfg.credit[i] * 100);
            g_owned[i] = 0;
            g_using[i] = 0;
            g_batteryStart[i] = -1.0f;
            g_boost[i] = 0;
            g_cfg.credit[i] = 0.0f;
        }
    }
    // avantage au dépassement : sur g_assistDist mètres après la détection (fin aussi si la distance revient en
    // arrière : nouvelle séance)
    for (int i = 0; i < CARS; i++) {
        if (!g_cfg.assist[i]) continue;
        BYTE* car = g_assistCar[i];
        bool end = clearAll || !car || !Readable(car + CAR_DIST, 4);
        if (!end) {
            float dist = *(float*)(car + CAR_DIST);
            end = dist > g_assistEnd[i] || dist < g_assistEnd[i] - g_assistDist - 100.0f;
        }
        if (end) g_cfg.assist[i] = 0;
    }
}

static DWORD WINAPI Worker(LPVOID) {
    g_exe = (BYTE*)GetModuleHandleW(nullptr);
    if (!CheckGame() || !BuildCave()) return 0;
    if (g_ersOk) {
        if (WriteCode(g_exe + ERS_RVA, g_ersPatch, 12)) Log("Overtake Mode : déploiement ERS forcé tant que le bonus n'est pas dépensé");
        else g_ersOk = false;
        if (g_clipOk && !WriteCode(g_exe + CLIP_RVA, g_clipPatch, 19)) g_clipOk = false;
        if (g_clipOk) Log("Overtake Mode : 12,5 %% d'énergie en crédit, déploiement forcé à chaque pas hors freinage");
    }
    if (g_ovtOk) {
        if (WriteCode(g_exe + OVT_RVA, g_ovtPatch, 33)) Log("Overtake Mode : bonus de probabilité de dépassement (celui du DRS d'origine) pour l'attaquant en Overtake Mode");
        else g_ovtOk = false;
    }
    int applied = -1;
    LONG read = 0;
    for (;;) {
        int want = StraightOff() ? 0 : 1;
        if (want != applied) {
            if (!Apply(want != 0)) {
                Log("VirtualProtect impossible");
                return 0;
            }
            Log(want ? "Straight Mode actif dès le 1er tour, Overtake Mode +12,5 %% de batterie à moins d'1 s"
                     : "règle d'origine (DRS à moins d'1 s, après 2 tours)");
            applied = want;
            g_cfg.rule2026 = want;
            read = g_ring.written;
            UpdateBoosts(true);
        }
        if (applied == 1) GrantOvertake(read);
        UpdateBoosts(false);
        UpdateGaps();
        WriteState(applied == 1);
        static int tick = 0;
        if (tick++ % 10 == 0) {
            if (applied == 1) ReadClipConfig();
            else g_cfg.clipOn = 0;
            ApplyAeroTables();
        }
        Sleep(POLL_MS);
    }
}

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(module);
        GetModuleFileNameW(module, g_dir, MAX_PATH);
        wchar_t* slash = wcsrchr(g_dir, L'\\');
        if (slash) *slash = 0;
        HANDLE t = CreateThread(nullptr, 0, Worker, nullptr, 0, nullptr);
        if (t) CloseHandle(t);
    }
    return TRUE;
}
