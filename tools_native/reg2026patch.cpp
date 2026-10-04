// Reg2026Patch.dll : Straight Mode réel pour F1 Manager 2024 (v1.11).
//
// Chargée par le mod UE4SS Reg2026 (package.loadlib). Tout se fait depuis un thread lancé par DllMain,
// sans dépendre de l'ABI C++ d'UE4SS.
//
// Machine à états DRS du jeu : exe+0x230C2B0, appelée pour chaque voiture à chaque pas de simulation.
// Au passage d'un point de détection, le jeu compare « temps actuel − temps de passage de la voiture devant »
// à 1,0 s et saute la détection si l'écart est plus grand :
//
//     230C447  comiss xmm0, xmm7      ; 0F 2F C7
//     230C44A  ja     +0x2E           ; 77 2E   -> 90 90
//
// Sans ce saut, toute voiture qui passe un point de détection obtient le droit au DRS, et le jeu l'ouvre
// lui-même dans la zone avec son vrai gain de vitesse. Les autres conditions restent : premiers tours,
// voiture de sécurité, drapeaux, piste mouillée.
//
// Le fichier straight_off.txt (dossier de la DLL, créé/supprimé par F7 côté Lua) remet la règle d'origine.
// Journal : patch.log dans le même dossier.
#include <windows.h>
#include <stdio.h>

static const DWORD64 SITE_RVA = 0x230C44A;
static const BYTE CONTEXT_BYTES[3] = { 0x0F, 0x2F, 0xC7 };
static const BYTE ORIGINAL[2] = { 0x77, 0x2E };
static const BYTE PATCHED[2] = { 0x90, 0x90 };
static const DWORD POLL_MS = 500;

static wchar_t g_dir[MAX_PATH];

static void Log(const char* msg) {
    wchar_t path[MAX_PATH];
    swprintf_s(path, L"%s\\patch.log", g_dir);
    FILE* f = nullptr;
    if (_wfopen_s(&f, path, L"a") != 0 || !f) return;
    SYSTEMTIME t;
    GetLocalTime(&t);
    fprintf(f, "%04d-%02d-%02d %02d:%02d:%02d %s\n", t.wYear, t.wMonth, t.wDay, t.wHour, t.wMinute, t.wSecond, msg);
    fclose(f);
}

static bool StraightOff() {
    wchar_t path[MAX_PATH];
    swprintf_s(path, L"%s\\straight_off.txt", g_dir);
    return GetFileAttributesW(path) != INVALID_FILE_ATTRIBUTES;
}

static bool Write2(BYTE* site, const BYTE* bytes) {
    DWORD old;
    if (!VirtualProtect(site, 2, PAGE_EXECUTE_READWRITE, &old)) return false;
    // écriture de 2 octets alignés : atomique pour les threads qui exécutent ce code
    *(volatile WORD*)site = *(const WORD*)bytes;
    VirtualProtect(site, 2, old, &old);
    FlushInstructionCache(GetCurrentProcess(), site, 2);
    return true;
}

static DWORD WINAPI Worker(LPVOID) {
    BYTE* site = (BYTE*)GetModuleHandleW(nullptr) + SITE_RVA;
    MEMORY_BASIC_INFORMATION mbi = {};
    if (!VirtualQuery(site - 3, &mbi, sizeof(mbi)) || mbi.State != MEM_COMMIT ||
        !(mbi.Protect & (PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY))) {
        Log("adresse du patch absente : ce n'est pas F1 Manager 2024 v1.11, patch non appliqué");
        return 0;
    }
    if (memcmp(site - 3, CONTEXT_BYTES, 3) != 0 ||
        (memcmp(site, ORIGINAL, 2) != 0 && memcmp(site, PATCHED, 2) != 0)) {
        char msg[128];
        sprintf_s(msg, "octets inattendus (%02X %02X %02X %02X %02X) : autre version du jeu, patch non appliqué",
                  site[-3], site[-2], site[-1], site[0], site[1]);
        Log(msg);
        return 0;
    }
    int applied = -1;  // -1 inconnu, 0 règle d'origine, 1 Straight Mode
    for (;;) {
        int want = StraightOff() ? 0 : 1;
        if (want != applied) {
            if (Write2(site, want ? PATCHED : ORIGINAL)) {
                Log(want ? "Straight Mode actif (DRS pour toute la grille)" : "règle d'origine (DRS à moins d'1 s)");
                applied = want;
            } else {
                Log("VirtualProtect impossible");
                return 0;
            }
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
