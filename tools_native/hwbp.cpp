// hwbp.dll : trouve quelles instructions du jeu écrivent à une adresse donnée, ou capture les registres
// quand une instruction s'exécute.
//
// Chargée dans F1Manager24.exe par inject.py. Lit hwbp_target.txt (« adresse [w|x] [taille] », à côté de
// la DLL), pose un point d'arrêt matériel (DR0) sur tous les threads : en écriture (w, 1/2/4/8 octets) ou à
// l'exécution (x). Note chaque instruction concernée pendant DURATION_MS, puis retire le point d'arrêt et écrit
// hwbp_log.txt : adresse de l'instruction, nombre de passages, registres des premiers passages, code autour.
// La DLL se décharge ensuite d'elle-même.
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>

static const DWORD DURATION_MS = 15000;
static const int MAX_SITES = 64;
static const int MAX_CTX = 8;

struct Site {
    DWORD64 rip;
    LONG count;
    CONTEXT ctx[MAX_CTX];  // registres des premiers passages
};

static Site g_sites[MAX_SITES];
static volatile LONG g_siteCount = 0;
static volatile LONG g_lost = 0;
static DWORD64 g_target = 0;
static bool g_exec = false;
static DWORD64 g_len = 1;
static HMODULE g_self = nullptr;
static wchar_t g_dir[MAX_PATH];

static LONG CALLBACK OnException(EXCEPTION_POINTERS* info) {
    if (info->ExceptionRecord->ExceptionCode != EXCEPTION_SINGLE_STEP) return EXCEPTION_CONTINUE_SEARCH;
    CONTEXT* c = info->ContextRecord;
    if (!(c->Dr6 & 1)) return EXCEPTION_CONTINUE_SEARCH;
    c->Dr6 = 0;
    // en écriture, Rip pointe sur l'instruction qui suit ; à l'exécution, sur l'instruction elle-même,
    // qu'il faut laisser passer une fois (Resume Flag)
    if (g_exec) c->EFlags |= 0x10000;
    DWORD64 rip = c->Rip;
    LONG n = g_siteCount;
    for (LONG i = 0; i < n && i < MAX_SITES; i++) {
        if (g_sites[i].rip == rip) {
            LONG k = InterlockedIncrement(&g_sites[i].count) - 1;
            if (k < MAX_CTX) g_sites[i].ctx[k] = *c;
            return EXCEPTION_CONTINUE_EXECUTION;
        }
    }
    LONG slot = InterlockedIncrement(&g_siteCount) - 1;
    if (slot < MAX_SITES) {
        g_sites[slot].ctx[0] = *c;
        g_sites[slot].count = 1;
        MemoryBarrier();
        g_sites[slot].rip = rip;
    } else {
        InterlockedIncrement(&g_lost);
    }
    return EXCEPTION_CONTINUE_EXECUTION;
}

static void SetBreakpointOnAllThreads(bool enable) {
    DWORD pid = GetCurrentProcessId(), self = GetCurrentThreadId();
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (snap == INVALID_HANDLE_VALUE) return;
    THREADENTRY32 te = { sizeof(te) };
    for (BOOL ok = Thread32First(snap, &te); ok; ok = Thread32Next(snap, &te)) {
        if (te.th32OwnerProcessID != pid || te.th32ThreadID == self) continue;
        HANDLE t = OpenThread(THREAD_GET_CONTEXT | THREAD_SET_CONTEXT | THREAD_SUSPEND_RESUME, FALSE, te.th32ThreadID);
        if (!t) continue;
        if (SuspendThread(t) != (DWORD)-1) {
            CONTEXT c = {};
            c.ContextFlags = CONTEXT_DEBUG_REGISTERS;
            if (GetThreadContext(t, &c)) {
                if (enable) {
                    DWORD64 len = g_len == 8 ? 2 : g_len == 4 ? 3 : g_len == 2 ? 1 : 0;
                    DWORD64 rw = g_exec ? 0 : 1;  // 00 exécution, 01 écriture
                    c.Dr0 = g_target;
                    c.Dr7 = (c.Dr7 & ~0xF0003ull) | 1ull | (rw << 16) | ((g_exec ? 0 : len) << 18);
                } else {
                    c.Dr0 = 0;
                    c.Dr7 &= ~0xF0003ull;
                }
                SetThreadContext(t, &c);
            }
            ResumeThread(t);
        }
        CloseHandle(t);
    }
    CloseHandle(snap);
}

static void WriteHex(FILE* f, const BYTE* p, size_t n) {
    for (size_t i = 0; i < n; i++) fprintf(f, "%02X", p[i]);
}

static void WriteLog() {
    wchar_t path[MAX_PATH];
    swprintf_s(path, L"%s\\hwbp_log.txt", g_dir);
    FILE* f = nullptr;
    if (_wfopen_s(&f, path, L"w") != 0 || !f) return;
    HMODULE exe = GetModuleHandleW(nullptr);
    fprintf(f, "target=%llX exe=%llX sites=%ld lost=%ld\n", g_target, (DWORD64)exe, g_siteCount, g_lost);
    LONG n = min(g_siteCount, (LONG)MAX_SITES);
    for (LONG i = 0; i < n; i++) {
        const Site& s = g_sites[i];
        fprintf(f, "site rip=%llX count=%ld\n", s.rip, s.count);
        for (LONG k = 0; k < min(s.count, (LONG)MAX_CTX); k++) {
            const CONTEXT& c = s.ctx[k];
            fprintf(f, "regs rax=%llX rbx=%llX rcx=%llX rdx=%llX rsi=%llX rdi=%llX rbp=%llX rsp=%llX "
                       "r8=%llX r9=%llX r10=%llX r11=%llX r12=%llX r13=%llX r14=%llX r15=%llX\n",
                    c.Rax, c.Rbx, c.Rcx, c.Rdx, c.Rsi, c.Rdi, c.Rbp, c.Rsp,
                    c.R8, c.R9, c.R10, c.R11, c.R12, c.R13, c.R14, c.R15);
        }
        // octets de code : 0x100 avant et 0x40 après l'instruction
        BYTE code[0x140];
        bool ok = false;
        __try {
            memcpy(code, (const void*)(s.rip - 0x100), sizeof(code));
            ok = true;
        } __except (EXCEPTION_EXECUTE_HANDLER) {}
        if (ok) {
            fprintf(f, "code base=%llX ", s.rip - 0x100);
            WriteHex(f, code, sizeof(code));
            fprintf(f, "\n");
        }
    }
    fclose(f);
}

static DWORD WINAPI Worker(LPVOID) {
    wchar_t path[MAX_PATH];
    swprintf_s(path, L"%s\\hwbp_target.txt", g_dir);
    FILE* f = nullptr;
    if (_wfopen_s(&f, path, L"r") == 0 && f) {
        char mode[4] = "w";
        fscanf_s(f, "%llx %3s %llu", &g_target, mode, (unsigned)sizeof(mode), &g_len);
        g_exec = mode[0] == 'x';
        fclose(f);
    }
    if (g_target) {
        PVOID veh = AddVectoredExceptionHandler(1, OnException);
        SetBreakpointOnAllThreads(true);
        Sleep(DURATION_MS);
        SetBreakpointOnAllThreads(false);
        Sleep(200);
        RemoveVectoredExceptionHandler(veh);
    }
    WriteLog();
    FreeLibraryAndExitThread(g_self, 0);
}

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_self = module;
        DisableThreadLibraryCalls(module);
        GetModuleFileNameW(module, g_dir, MAX_PATH);
        wchar_t* slash = wcsrchr(g_dir, L'\\');
        if (slash) *slash = 0;
        HANDLE t = CreateThread(nullptr, 0, Worker, nullptr, 0, nullptr);
        if (t) CloseHandle(t);
    }
    return TRUE;
}
