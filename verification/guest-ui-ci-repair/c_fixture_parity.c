#define main fixture_smoke_main
#include FIXTURE_SOURCE
#undef main

int main(int argc, char **argv) {
    assert(argc == 2);
    for (unsigned variant = 0; variant < 2; variant++) {
        const Wasm wasm = program(variant);
        char path[4096];
        const int length = snprintf(path, sizeof(path), "%s/c-%u.wasm", argv[1], variant);
        assert(length > 0 && (size_t)length < sizeof(path));
        FILE *output = fopen(path, "wb");
        assert(output != NULL);
        assert(fwrite(wasm.data, 1, wasm.size, output) == wasm.size);
        assert(fclose(output) == 0);
        printf("c-%u %zu\n", variant, wasm.size);
    }
    return 0;
}
