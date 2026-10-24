"""Uncalled production Clippy, formatting and Frozen expansion identity checks."""
import collect as c
from pathlib import Path
import frozen_identity

def main():
 for features in ['swift','all']:
  flags=['--no-default-features']+(['--features','experimental-swift-reactor']if features=='swift'else['--all-features'])
  code,*_=c.run(['cargo','clippy','--lib','--locked','--offline',*flags,'--','-D','warnings'],label='production-clippy-'+features)
  assert code==0
 code,*_=c.run(['/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustfmt','--edition','2021','--check','src/experimental_swift_reactor/lifecycle.rs','src/experimental_swift_reactor/lifecycle_tests.rs'],label='new-source-formatting-check')
 assert code==0
 frozen_identity.main()
if __name__=='__main__':main()
