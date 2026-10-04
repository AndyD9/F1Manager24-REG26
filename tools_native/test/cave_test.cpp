// construit les caves de reg2026patch.cpp sur une fausse image d'exe et les écrit dans cave.bin
#include "../reg2026patch.cpp"
int main() {
    g_exe = (BYTE*)VirtualAlloc(nullptr, 0x6000000, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    memcpy(g_exe + ERS_RVA, ERS_ORIGINAL, 12);
    INT32 orig; memcpy(&orig, ERS_ORIGINAL + 8, 4);
    float k = 1234.5f; memcpy(g_exe + ERS_RVA + 12 + orig, &k, 4);
    if (!BuildCave()) return 1;
    FILE* f = fopen("cave.bin", "wb");
    DWORD64 base = (DWORD64)g_cave, exe = (DWORD64)g_exe, boost = (DWORD64)g_boost;
    fwrite(&base, 8, 1, f); fwrite(&exe, 8, 1, f); fwrite(&boost, 8, 1, f);
    fwrite(g_cave, 1, 0x200, f);
    fclose(f);
    return 0;
}
