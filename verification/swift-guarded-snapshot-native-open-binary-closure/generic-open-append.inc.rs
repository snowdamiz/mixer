
// Inert evidence-only retention: no registration, export, execution or fixture.
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static NATIVE_OPEN_READ_PATH_V1: fn(&'static std::path::Path) -> std::io::Result<std::fs::File> = std::fs::File::open::<&'static std::path::Path>;
#[cfg(mixer_bootstrap_one_fixture_v1)]
fn native_open_create_path_v1(path: &std::path::Path) -> std::io::Result<std::fs::File> {
    std::fs::OpenOptions::new().write(true).create_new(true).open(path)
}
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static NATIVE_OPEN_CREATE_PATH_V1: fn(&std::path::Path) -> std::io::Result<std::fs::File> = native_open_create_path_v1;
