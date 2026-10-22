mod common;
use common::*;
use mixer_vm::Type;
use std::process::Command;
#[test]
fn machine_readable_cli_contract() {
    let dir = std::env::temp_dir().join(format!("mixer-vm-cli-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("owned-fixture.wasm");
    std::fs::write(&path, single(vec![0x41, 42, 0x0b], Some(Type::I32))).unwrap();
    let cli = env!("CARGO_BIN_EXE_mixer-vm");
    let out = Command::new(cli)
        .arg("validate")
        .arg(&path)
        .output()
        .unwrap();
    assert!(out.status.success());
    let text = String::from_utf8(out.stdout).unwrap();
    assert_eq!(text.lines().count(), 1);
    assert!(text.contains("\"valid\":true"));
    let out = Command::new(cli)
        .arg("invoke")
        .arg(&path)
        .arg("run")
        .output()
        .unwrap();
    assert!(out.status.success());
    assert!(String::from_utf8(out.stdout)
        .unwrap()
        .contains("\"value\":42"));
    let out = Command::new(cli)
        .args(["invoke", "--fuel", "0"])
        .arg(&path)
        .arg("run")
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2));
    assert!(String::from_utf8(out.stdout)
        .unwrap()
        .contains("fuel_exhausted"));
    std::fs::write(&path, single(vec![0x43, 0, 0, 0, 0, 0x1a, 0x0b], None)).unwrap();
    let out = Command::new(cli)
        .arg("inventory")
        .arg(&path)
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2));
    let text = String::from_utf8(out.stdout).unwrap();
    assert!(text.contains("\"inventory_complete\":true"));
    assert!(text.contains("\"valid\":false"));
    assert!(text.contains("0x43"));
    std::fs::remove_dir_all(dir).unwrap();
}
