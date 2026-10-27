#![forbid(unsafe_code)]
use std::path::PathBuf;
use std::fs::{self,File,OpenOptions};
use std::io::{self,Write};
struct OwnedDirectory(PathBuf);
impl OwnedDirectory {
    fn new() -> Self {
        use std::sync::atomic::{AtomicU64, Ordering};
        static NEXT: AtomicU64 = AtomicU64::new(0);
        for _ in 0..64 {
            let path = std::env::temp_dir().join(format!(
                "mixer-diagnostic-profile-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            match fs::create_dir(&path) {
                Ok(()) => return Self(path),
                Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
                Err(error) => panic!("create owned diagnostic fixture: {error}"),
            }
        }
        panic!("owned diagnostic fixture names exhausted");
    }
    fn fresh(&self, name: &str) -> File {
        OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .open(self.0.join(name))
            .unwrap()
    }
}
impl Drop for OwnedDirectory {
    fn drop(&mut self) {
        let result = fs::remove_dir_all(&self.0);
        if !std::thread::panicking() {
            result.expect("remove owned diagnostic fixture");
        }
    }
}

#[test]
fn exact_fixture_refuses_collisions_preserves_unowned_and_cleans_normal_and_unwind() {
    let temporary = std::env::temp_dir();
    let collision = temporary.join(format!("mixer-diagnostic-profile-{}-0", std::process::id()));
    fs::create_dir(&collision).unwrap();
    fs::write(collision.join("preserve.bin"), b"collision-sentinel").unwrap();
    let normal;
    {
        let directory = OwnedDirectory::new();
        normal = directory.0.clone();
        assert_ne!(normal,collision);
        assert!(normal.ends_with(format!("mixer-diagnostic-profile-{}-1",std::process::id())));
        let mut file = directory.fresh("normal.bin");
        file.write_all(b"normal-data").unwrap();
        let result = std::panic::catch_unwind(|| directory.fresh("normal.bin"));
        assert!(result.is_err());
        assert_eq!(fs::read(normal.join("normal.bin")).unwrap(),b"normal-data");
        // Normal lexical reverse-drop order closes File before OwnedDirectory.
    }
    assert!(!normal.exists());
    assert_eq!(fs::read(collision.join("preserve.bin")).unwrap(), b"collision-sentinel");
    let unwind = std::cell::RefCell::new(None);
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let directory = OwnedDirectory::new();
        *unwind.borrow_mut() = Some(directory.0.clone());
        let mut file = directory.fresh("unwind.bin");
        file.write_all(b"unwind-data").unwrap();
        panic!("intentional independently checked fixture unwind");
    }));
    assert!(result.is_err());
    assert!(!unwind.borrow().as_ref().unwrap().exists());
    assert_eq!(fs::read(collision.join("preserve.bin")).unwrap(), b"collision-sentinel");
    fs::remove_file(collision.join("preserve.bin")).unwrap();
    fs::remove_dir(collision).unwrap();
    println!("FIXTURE collision_skip=pass create_new_preservation=pass normal_cleanup=pass unwind_cleanup=pass unowned_sentinel_preserved=pass");
}
