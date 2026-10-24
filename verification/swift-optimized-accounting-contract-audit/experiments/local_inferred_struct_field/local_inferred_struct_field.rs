struct W { actual: _ }
fn main() { let closure=||1; let _=W {actual:closure}; }
