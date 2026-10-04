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
// 3. Overtake Mode utilisé : la voiture qui a reçu le bonus déploie l'ERS à fond tant qu'elle n'a pas dépensé
//    ces 12,5 % (au plus jusqu'à la fin du tour suivant). Mise à jour ERS du jeu, exe+0x2308250 : la décision
//    de l'IA (230B990) donne [rbp+0x38] = 0 (pas de recharge) / 1 / 2, puis dl = 0 veut dire « déployer » :
//        23084B8  xor dl, dl / jmp / mov dl, 1
//        23084BE  movzx eax, byte ptr [rbp + 0x38]          ; 0F B6 45 38
//        23084C2  movss xmm5, dword ptr [rip + 0x3CA6FCA]    ; F3 0F 10 2D CA 6F CA 03
//    Ces 12 octets deviennent « mov rax, cave ; jmp rax » (rax est écrasé juste après). Quand l'IA ne recharge
//    pas et que la voiture (index en +0x710) a le bonus, la cave met dl = 0. Le code en 230848F, juste avant,
//    est un saut de Denuvo : on n'y touche pas. Ce crochet est posé une fois au chargement (avant toute
//    course) et reste en place ; F7 vide seulement la liste des voitures en Overtake.
//
// Le fichier straight_off.txt (créé/supprimé par F7 côté Lua) remet le jeu d'origine.
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <initializer_list>

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

static const DWORD CAR_LAPS = 0x7E4;
static const DWORD CAR_MODE = 0x200;   // 2 = en course
static const DWORD CAR_INDEX = 0x710;
static const int CARS = 32;
static const DWORD CAR_BATTERY = 0x878;
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

// voitures en Overtake Mode, par index ; lu par la cave ERS
static volatile BYTE g_boost[CARS];
struct Boost { BYTE* car; float stop; int endLap; };
static Boost g_boostInfo[CARS];

static void Log(const char* fmt, ...) {
    wchar_t path[MAX_PATH];
    swprintf_s(path, L"%s\\patch.log", g_dir);
    FILE* f = nullptr;
    if (_wfopen_s(&f, path, L"a") != 0 || !f) return;
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
    put({ 0x0F, 0xB6, 0x45, 0x38 });        // movzx eax, byte [rbp+0x38]
    put({ 0x84, 0xC0 });                    // test al, al
    put({ 0x75, 0x00 });                    // jnz done (l'IA recharge)
    BYTE* jnz = p - 1;
    put({ 0x40, 0x84, 0xFF });              // test dil, dil
    put({ 0x74, 0x00 });                    // jz done (ERS indisponible)
    BYTE* jz = p - 1;
    put({ 0x51 });                          // push rcx
    put({ 0x0F, 0xB6, 0x8B }); { DWORD d = CAR_INDEX; memcpy(p, &d, 4); p += 4; }  // movzx ecx, byte [rbx+0x710]
    put({ 0x83, 0xE1, CARS - 1 });          // and ecx, CARS-1
    put({ 0x48, 0xB8 }); put64((DWORD64)g_boost);  // mov rax, g_boost
    put({ 0x80, 0x3C, 0x08, 0x00 });        // cmp byte [rax+rcx], 0
    put({ 0x59 });                          // pop rcx
    put({ 0x74, 0x02 });                    // je +2
    put({ 0x32, 0xD2 });                    // xor dl, dl : déployer
    put({ 0x31, 0xC0 });                    // xor eax, eax (al valait 0)
    *jnz = (BYTE)(p - (jnz + 1));           // done:
    *jz = (BYTE)(p - (jz + 1));
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
    return true;
}

static bool g_ersOk = false;

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
    if (!ersOk) Log("mise à jour ERS inattendue : Overtake Mode donnera la batterie sans forcer le déploiement");
    g_ersOk = ersOk;
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

/// vide la file des voitures à moins d'1 s : +12,5 % de batterie, une fois par tour
static void GrantOvertake(LONG& read) {
    static BYTE* lastCar[RING];
    static int lastLap[RING];
    LONG written = g_ring.written;
    if (written - read > RING) read = written - RING;
    for (; read < written; read++) {
        BYTE* car = g_ring.cars[read & (RING - 1)];
        if (!Readable(car + CAR_LAPS, 4) || !Readable(car + CAR_BATTERY, 4)) continue;
        int lap = *(int*)(car + CAR_LAPS);
        int slot = -1;
        for (int i = 0; i < RING; i++) {
            if (lastCar[i] == car) { slot = i; break; }
            if (slot < 0 && !lastCar[i]) slot = i;
        }
        if (slot < 0) slot = 0;
        if (lastCar[slot] == car && lastLap[slot] == lap) continue;  // déjà reçu ce tour-ci
        lastCar[slot] = car;
        lastLap[slot] = lap;
        float* battery = (float*)(car + CAR_BATTERY);
        float before = *battery;
        float after = before + OVERTAKE_ENERGY;
        if (after > 1.0f) after = 1.0f;
        *battery = after;
        int idx = car[CAR_INDEX] & (CARS - 1);
        float stop = after - OVERTAKE_ENERGY;
        g_boostInfo[idx] = { car, stop > 0.0f ? stop : 0.0f, lap + 1 };
        g_boost[idx] = 1;
        Log("Overtake Mode : voiture %d, tour %d, batterie %.0f%% -> %.0f%%", idx, lap, before * 100, after * 100);
    }
}

/// fin du déploiement forcé : bonus dépensé, tour suivant terminé, ou voiture plus en course
static void UpdateBoosts(bool clearAll) {
    for (int i = 0; i < CARS; i++) {
        if (!g_boost[i]) continue;
        Boost& b = g_boostInfo[i];
        bool end = clearAll || !Readable(b.car + CAR_MODE, 1) || !Readable(b.car + CAR_BATTERY, 4);
        if (!end) {
            float battery = *(float*)(b.car + CAR_BATTERY);
            int lap = *(int*)(b.car + CAR_LAPS);
            end = battery <= b.stop || lap > b.endLap || b.car[CAR_MODE] != 2;
        }
        if (end) g_boost[i] = 0;
    }
}

static DWORD WINAPI Worker(LPVOID) {
    g_exe = (BYTE*)GetModuleHandleW(nullptr);
    if (!CheckGame() || !BuildCave()) return 0;
    if (g_ersOk) {
        if (WriteCode(g_exe + ERS_RVA, g_ersPatch, 12)) Log("Overtake Mode : déploiement ERS forcé tant que le bonus n'est pas dépensé");
        else g_ersOk = false;
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
            read = g_ring.written;
            UpdateBoosts(true);
        }
        if (applied == 1) GrantOvertake(read);
        UpdateBoosts(false);
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
