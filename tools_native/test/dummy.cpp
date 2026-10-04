#include <windows.h>
#include <stdio.h>
volatile unsigned char g_state = 0;
volatile unsigned char g_internal = 0;
__declspec(noinline) void Tick(int i) { g_internal = (unsigned char)(i % 4); g_state = g_internal; }
int main() {
    printf("%p\n", (void*)&g_state); fflush(stdout);
    FILE* f = fopen("dummy_addr.txt", "w"); fprintf(f, "%p", (void*)&g_state); fclose(f);
    for (int i = 0; i < 2000; i++) { Tick(i); Sleep(10); }
}
