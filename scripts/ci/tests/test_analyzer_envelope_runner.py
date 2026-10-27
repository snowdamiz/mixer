"""Failure controls for the closed envelope runner, independent of product behavior."""
import copy
import gzip
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / 'scripts/ci/check-analyzer-envelope.py'
spec = importlib.util.spec_from_file_location('envelope_runner', RUNNER)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

# Unmodified real Rust 1.99.0 diagnostic streams from the root-selected basis.
# Literal bytes keep the tests portable without a historical runtime dependency.
ACTUAL_DIAGNOSTICS = {
    'private-field': '{"$message_type":"diagnostic","message":"field `envelope_debit` of struct `mixer_absence::FixtureEnvelopeObservationV1` is private","code":{"code":"E0616","explanation":"Attempted to access a private field on a struct.\\n\\nErroneous code example:\\n\\n```compile_fail,E0616\\nmod some_module {\\n    pub struct Foo {\\n        x: u32, // So `x` is private in here.\\n    }\\n\\n    impl Foo {\\n        pub fn new() -> Foo { Foo { x: 0 } }\\n    }\\n}\\n\\nlet f = some_module::Foo::new();\\nprintln!(\\"{}\\", f.x); // error: field `x` of struct `some_module::Foo` is private\\n```\\n\\nIf you want to access this field, you have two options:\\n\\n1) Set the field public:\\n\\n```\\nmod some_module {\\n    pub struct Foo {\\n        pub x: u32, // `x` is now public.\\n    }\\n\\n    impl Foo {\\n        pub fn new() -> Foo { Foo { x: 0 } }\\n    }\\n}\\n\\nlet f = some_module::Foo::new();\\nprintln!(\\"{}\\", f.x); // ok!\\n```\\n\\n2) Add a getter function:\\n\\n```\\nmod some_module {\\n    pub struct Foo {\\n        x: u32, // So `x` is still private in here.\\n    }\\n\\n    impl Foo {\\n        pub fn new() -> Foo { Foo { x: 0 } }\\n\\n        // We create the getter function here:\\n        pub fn get_x(&self) -> &u32 { &self.x }\\n    }\\n}\\n\\nlet f = some_module::Foo::new();\\nprintln!(\\"{}\\", f.get_x()); // ok!\\n```\\n"},"level":"error","spans":[{"file_name":"api/private-field.rs","byte_start":69,"byte_end":83,"line_start":1,"line_end":1,"column_start":70,"column_end":84,"is_primary":true,"text":[{"text":"use mixer_absence::*;pub fn f(x:&mut FixtureEnvelopeObservationV1){x.envelope_debit=0;}fn main(){}","highlight_start":70,"highlight_end":84}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null}],"children":[],"rendered":"error[E0616]: field `envelope_debit` of struct `mixer_absence::FixtureEnvelopeObservationV1` is private\\n --> api/private-field.rs:1:70\\n  |\\n1 | use mixer_absence::*;pub fn f(x:&mut FixtureEnvelopeObservationV1){x.envelope_debit=0;}fn main(){}\\n  |                                                                      ^^^^^^^^^^^^^^ private field\\n\\n"}\n{"$message_type":"diagnostic","message":"aborting due to 1 previous error","code":null,"level":"error","spans":[],"children":[],"rendered":"error: aborting due to 1 previous error\\n\\n"}\n{"$message_type":"diagnostic","message":"For more information about this error, try `rustc --explain E0616`.","code":null,"level":"failure-note","spans":[],"children":[],"rendered":"For more information about this error, try `rustc --explain E0616`.\\n"}\n',
    'no-clone': '{"$message_type":"diagnostic","message":"the trait bound `mixer_absence::FixtureEnvelopeObservationV1: Clone` is not satisfied","code":{"code":"E0277","explanation":"You tried to use a type which doesn\'t implement some trait in a place which\\nexpected that trait.\\n\\nErroneous code example:\\n\\n```compile_fail,E0277\\n// here we declare the Foo trait with a bar method\\ntrait Foo {\\n    fn bar(&self);\\n}\\n\\n// we now declare a function which takes an object implementing the Foo trait\\nfn some_func<T: Foo>(foo: T) {\\n    foo.bar();\\n}\\n\\nfn main() {\\n    // we now call the method with the i32 type, which doesn\'t implement\\n    // the Foo trait\\n    some_func(5i32); // error: the trait bound `i32 : Foo` is not satisfied\\n}\\n```\\n\\nIn order to fix this error, verify that the type you\'re using does implement\\nthe trait. Example:\\n\\n```\\ntrait Foo {\\n    fn bar(&self);\\n}\\n\\n// we implement the trait on the i32 type\\nimpl Foo for i32 {\\n    fn bar(&self) {}\\n}\\n\\nfn some_func<T: Foo>(foo: T) {\\n    foo.bar(); // we can now use this method since i32 implements the\\n               // Foo trait\\n}\\n\\nfn main() {\\n    some_func(5i32); // ok!\\n}\\n```\\n\\nOr in a generic context, an erroneous code example would look like:\\n\\n```compile_fail,E0277\\nfn some_func<T>(foo: T) {\\n    println!(\\"{:?}\\", foo); // error: the trait `core::fmt::Debug` is not\\n                           //        implemented for the type `T`\\n}\\n\\nfn main() {\\n    // We now call the method with the i32 type,\\n    // which *does* implement the Debug trait.\\n    some_func(5i32);\\n}\\n```\\n\\nNote that the error here is in the definition of the generic function. Although\\nwe only call it with a parameter that does implement `Debug`, the compiler\\nstill rejects the function. It must work with all possible input types. In\\norder to make this example compile, we need to restrict the generic type we\'re\\naccepting:\\n\\n```\\nuse std::fmt;\\n\\n// Restrict the input type to types that implement Debug.\\nfn some_func<T: fmt::Debug>(foo: T) {\\n    println!(\\"{:?}\\", foo);\\n}\\n\\nfn main() {\\n    // Calling the method is still fine, as i32 implements Debug.\\n    some_func(5i32);\\n\\n    // This would fail to compile now:\\n    // struct WithoutDebug;\\n    // some_func(WithoutDebug);\\n}\\n```\\n\\nRust only looks at the signature of the called function, as such it must\\nalready specify all requirements that will be used for every type parameter.\\n"},"level":"error","spans":[{"file_name":"api/no-clone.rs","byte_start":58,"byte_end":86,"line_start":1,"line_end":1,"column_start":59,"column_end":87,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn need<T:Clone>(){}fn main(){need::<FixtureEnvelopeObservationV1>();}","highlight_start":59,"highlight_end":87}],"label":"the trait `Clone` is not implemented for `mixer_absence::FixtureEnvelopeObservationV1`","suggested_replacement":null,"suggestion_applicability":null,"expansion":null}],"children":[{"message":"required by a bound in `need`","code":null,"level":"note","spans":[{"file_name":"api/no-clone.rs","byte_start":31,"byte_end":36,"line_start":1,"line_end":1,"column_start":32,"column_end":37,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn need<T:Clone>(){}fn main(){need::<FixtureEnvelopeObservationV1>();}","highlight_start":32,"highlight_end":37}],"label":"required by this bound in `need`","suggested_replacement":null,"suggestion_applicability":null,"expansion":null}],"children":[],"rendered":null}],"rendered":"error[E0277]: the trait bound `mixer_absence::FixtureEnvelopeObservationV1: Clone` is not satisfied\\n --> api/no-clone.rs:1:59\\n  |\\n1 | use mixer_absence::*;fn need<T:Clone>(){}fn main(){need::<FixtureEnvelopeObservationV1>();}\\n  |                                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ the trait `Clone` is not implemented for `mixer_absence::FixtureEnvelopeObservationV1`\\n  |\\nnote: required by a bound in `need`\\n --> api/no-clone.rs:1:32\\n  |\\n1 | use mixer_absence::*;fn need<T:Clone>(){}fn main(){need::<FixtureEnvelopeObservationV1>();}\\n  |                                ^^^^^ required by this bound in `need`\\n\\n"}\n{"$message_type":"diagnostic","message":"aborting due to 1 previous error","code":null,"level":"error","spans":[],"children":[],"rendered":"error: aborting due to 1 previous error\\n\\n"}\n{"$message_type":"diagnostic","message":"For more information about this error, try `rustc --explain E0277`.","code":null,"level":"failure-note","spans":[],"children":[],"rendered":"For more information about this error, try `rustc --explain E0277`.\\n"}\n',
    'no-copy': '{"$message_type":"diagnostic","message":"the trait bound `mixer_absence::FixtureEnvelopeOutcomeV1: Copy` is not satisfied","code":{"code":"E0277","explanation":"You tried to use a type which doesn\'t implement some trait in a place which\\nexpected that trait.\\n\\nErroneous code example:\\n\\n```compile_fail,E0277\\n// here we declare the Foo trait with a bar method\\ntrait Foo {\\n    fn bar(&self);\\n}\\n\\n// we now declare a function which takes an object implementing the Foo trait\\nfn some_func<T: Foo>(foo: T) {\\n    foo.bar();\\n}\\n\\nfn main() {\\n    // we now call the method with the i32 type, which doesn\'t implement\\n    // the Foo trait\\n    some_func(5i32); // error: the trait bound `i32 : Foo` is not satisfied\\n}\\n```\\n\\nIn order to fix this error, verify that the type you\'re using does implement\\nthe trait. Example:\\n\\n```\\ntrait Foo {\\n    fn bar(&self);\\n}\\n\\n// we implement the trait on the i32 type\\nimpl Foo for i32 {\\n    fn bar(&self) {}\\n}\\n\\nfn some_func<T: Foo>(foo: T) {\\n    foo.bar(); // we can now use this method since i32 implements the\\n               // Foo trait\\n}\\n\\nfn main() {\\n    some_func(5i32); // ok!\\n}\\n```\\n\\nOr in a generic context, an erroneous code example would look like:\\n\\n```compile_fail,E0277\\nfn some_func<T>(foo: T) {\\n    println!(\\"{:?}\\", foo); // error: the trait `core::fmt::Debug` is not\\n                           //        implemented for the type `T`\\n}\\n\\nfn main() {\\n    // We now call the method with the i32 type,\\n    // which *does* implement the Debug trait.\\n    some_func(5i32);\\n}\\n```\\n\\nNote that the error here is in the definition of the generic function. Although\\nwe only call it with a parameter that does implement `Debug`, the compiler\\nstill rejects the function. It must work with all possible input types. In\\norder to make this example compile, we need to restrict the generic type we\'re\\naccepting:\\n\\n```\\nuse std::fmt;\\n\\n// Restrict the input type to types that implement Debug.\\nfn some_func<T: fmt::Debug>(foo: T) {\\n    println!(\\"{:?}\\", foo);\\n}\\n\\nfn main() {\\n    // Calling the method is still fine, as i32 implements Debug.\\n    some_func(5i32);\\n\\n    // This would fail to compile now:\\n    // struct WithoutDebug;\\n    // some_func(WithoutDebug);\\n}\\n```\\n\\nRust only looks at the signature of the called function, as such it must\\nalready specify all requirements that will be used for every type parameter.\\n"},"level":"error","spans":[{"file_name":"api/no-copy.rs","byte_start":57,"byte_end":81,"line_start":1,"line_end":1,"column_start":58,"column_end":82,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn need<T:Copy>(){}fn main(){need::<FixtureEnvelopeOutcomeV1>();}","highlight_start":58,"highlight_end":82}],"label":"the trait `Copy` is not implemented for `mixer_absence::FixtureEnvelopeOutcomeV1`","suggested_replacement":null,"suggestion_applicability":null,"expansion":null}],"children":[{"message":"required by a bound in `need`","code":null,"level":"note","spans":[{"file_name":"api/no-copy.rs","byte_start":31,"byte_end":35,"line_start":1,"line_end":1,"column_start":32,"column_end":36,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn need<T:Copy>(){}fn main(){need::<FixtureEnvelopeOutcomeV1>();}","highlight_start":32,"highlight_end":36}],"label":"required by this bound in `need`","suggested_replacement":null,"suggestion_applicability":null,"expansion":null}],"children":[],"rendered":null}],"rendered":"error[E0277]: the trait bound `mixer_absence::FixtureEnvelopeOutcomeV1: Copy` is not satisfied\\n --> api/no-copy.rs:1:58\\n  |\\n1 | use mixer_absence::*;fn need<T:Copy>(){}fn main(){need::<FixtureEnvelopeOutcomeV1>();}\\n  |                                                          ^^^^^^^^^^^^^^^^^^^^^^^^ the trait `Copy` is not implemented for `mixer_absence::FixtureEnvelopeOutcomeV1`\\n  |\\nnote: required by a bound in `need`\\n --> api/no-copy.rs:1:32\\n  |\\n1 | use mixer_absence::*;fn need<T:Copy>(){}fn main(){need::<FixtureEnvelopeOutcomeV1>();}\\n  |                                ^^^^ required by this bound in `need`\\n\\n"}\n{"$message_type":"diagnostic","message":"aborting due to 1 previous error","code":null,"level":"error","spans":[],"children":[],"rendered":"error: aborting due to 1 previous error\\n\\n"}\n{"$message_type":"diagnostic","message":"For more information about this error, try `rustc --explain E0277`.","code":null,"level":"failure-note","spans":[],"children":[],"rendered":"For more information about this error, try `rustc --explain E0277`.\\n"}\n',
    'no-record-constructor': '{"$message_type":"diagnostic","message":"unresolved import `mixer_absence::FixtureDecodedRecordV1`","code":{"code":"E0432","explanation":"An import was unresolved.\\n\\nErroneous code example:\\n\\n```compile_fail,E0432\\nuse something::Foo; // error: unresolved import `something::Foo`.\\n```\\n\\nIn Rust 2015, paths in `use` statements are relative to the crate root. To\\nimport items relative to the current and parent modules, use the `self::` and\\n`super::` prefixes, respectively.\\n\\nIn Rust 2018 or later, paths in `use` statements are relative to the current\\nmodule unless they begin with the name of a crate or a literal `crate::`, in\\nwhich case they start from the crate root. As in Rust 2015 code, the `self::`\\nand `super::` prefixes refer to the current and parent modules respectively.\\n\\nAlso verify that you didn\'t misspell the import name and that the import exists\\nin the module from where you tried to import it. Example:\\n\\n```\\nuse self::something::Foo; // Ok.\\n\\nmod something {\\n    pub struct Foo;\\n}\\n# fn main() {}\\n```\\n\\nIf you tried to use a module from an external crate and are using Rust 2015,\\nyou may have missed the `extern crate` declaration (which is usually placed in\\nthe crate root):\\n\\n```edition2015\\nextern crate core; // Required to use the `core` crate in Rust 2015.\\n\\nuse core::any;\\n# fn main() {}\\n```\\n\\nSince Rust 2018 the `extern crate` declaration is not required and\\nyou can instead just `use` it:\\n\\n```edition2018\\nuse core::any; // No extern crate required in Rust 2018.\\n# fn main() {}\\n```\\n"},"level":"error","spans":[{"file_name":"api/no-record-constructor.rs","byte_start":19,"byte_end":41,"line_start":1,"line_end":1,"column_start":20,"column_end":42,"is_primary":false,"text":[{"text":"use mixer_absence::FixtureDecodedRecordV1;fn main(){}","highlight_start":20,"highlight_end":42}],"label":"no `FixtureDecodedRecordV1` in the root","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-record-constructor.rs","byte_start":4,"byte_end":41,"line_start":1,"line_end":1,"column_start":5,"column_end":42,"is_primary":true,"text":[{"text":"use mixer_absence::FixtureDecodedRecordV1;fn main(){}","highlight_start":5,"highlight_end":42}],"label":null,"suggested_replacement":null,"suggestion_applicability":null,"expansion":null}],"children":[],"rendered":"error[E0432]: unresolved import `mixer_absence::FixtureDecodedRecordV1`\\n --> api/no-record-constructor.rs:1:5\\n  |\\n1 | use mixer_absence::FixtureDecodedRecordV1;fn main(){}\\n  |     ^^^^^^^^^^^^^^^----------------------\\n  |                    |\\n  |                    no `FixtureDecodedRecordV1` in the root\\n\\n"}\n{"$message_type":"diagnostic","message":"aborting due to 1 previous error","code":null,"level":"error","spans":[],"children":[],"rendered":"error: aborting due to 1 previous error\\n\\n"}\n{"$message_type":"diagnostic","message":"For more information about this error, try `rustc --explain E0432`.","code":null,"level":"failure-note","spans":[],"children":[],"rendered":"For more information about this error, try `rustc --explain E0432`.\\n"}\n',
    'no-word-or-boolean-entry': '{"$message_type":"diagnostic","message":"this function takes 4 arguments but 2 arguments were supplied","code":{"code":"E0061","explanation":"An invalid number of arguments was passed when calling a function.\\n\\nErroneous code example:\\n\\n```compile_fail,E0061\\nfn f(u: i32) {}\\n\\nf(); // error!\\n```\\n\\nThe number of arguments passed to a function must match the number of arguments\\nspecified in the function signature.\\n\\nFor example, a function like:\\n\\n```\\nfn f(a: u16, b: &str) {}\\n```\\n\\nMust always be called with exactly two arguments, e.g., `f(2, \\"test\\")`.\\n\\nNote that Rust does not have a notion of optional function arguments or\\nvariadic functions (except for its C-FFI).\\n"},"level":"error","spans":[{"file_name":"api/no-word-or-boolean-entry.rs","byte_start":89,"byte_end":99,"line_start":1,"line_end":1,"column_start":90,"column_end":100,"is_primary":false,"text":[{"text":"use mixer_absence::*;fn main(){let mut words=[0u64;16];let _=analyze_fixture_envelope_v1(&mut words,true);}","highlight_start":90,"highlight_end":100}],"label":"expected `&mut File`, found `&mut [u64; 16]`","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-word-or-boolean-entry.rs","byte_start":100,"byte_end":104,"line_start":1,"line_end":1,"column_start":101,"column_end":105,"is_primary":false,"text":[{"text":"use mixer_absence::*;fn main(){let mut words=[0u64;16];let _=analyze_fixture_envelope_v1(&mut words,true);}","highlight_start":101,"highlight_end":105}],"label":"expected `&mut File`, found `bool`","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-word-or-boolean-entry.rs","byte_start":88,"byte_end":105,"line_start":1,"line_end":1,"column_start":89,"column_end":106,"is_primary":false,"text":[{"text":"use mixer_absence::*;fn main(){let mut words=[0u64;16];let _=analyze_fixture_envelope_v1(&mut words,true);}","highlight_start":89,"highlight_end":106}],"label":"two arguments of type `&mut File` and `&mut File` are missing","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-word-or-boolean-entry.rs","byte_start":61,"byte_end":88,"line_start":1,"line_end":1,"column_start":62,"column_end":89,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let mut words=[0u64;16];let _=analyze_fixture_envelope_v1(&mut words,true);}","highlight_start":62,"highlight_end":89}],"label":null,"suggested_replacement":null,"suggestion_applicability":null,"expansion":null}],"children":[{"message":"expected mutable reference `&mut File`\\n   found mutable reference `&mut [u64; 16]`","code":null,"level":"note","spans":[],"children":[],"rendered":null},{"message":"function defined here","code":null,"level":"note","spans":[{"file_name":"source/library/envelope.rs","byte_start":24414,"byte_end":24441,"line_start":386,"line_end":386,"column_start":8,"column_end":35,"is_primary":true,"text":[{"text":"pub fn analyze_fixture_envelope_v1(stream: &mut File, profile_file: &mut File, context: &mut File, output: &mut File) -> Result<FixtureEnvelopeOutcomeV1, AnalyzerError> {","highlight_start":8,"highlight_end":35}],"label":null,"suggested_replacement":null,"suggestion_applicability":null,"expansion":null}],"children":[],"rendered":null},{"message":"provide the arguments","code":null,"level":"help","spans":[{"file_name":"api/no-word-or-boolean-entry.rs","byte_start":88,"byte_end":105,"line_start":1,"line_end":1,"column_start":89,"column_end":106,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let mut words=[0u64;16];let _=analyze_fixture_envelope_v1(&mut words,true);}","highlight_start":89,"highlight_end":106}],"label":null,"suggested_replacement":"(/* &mut File */, /* &mut File */, /* &mut File */, /* &mut File */)","suggestion_applicability":"HasPlaceholders","expansion":null}],"children":[],"rendered":null}],"rendered":"error[E0061]: this function takes 4 arguments but 2 arguments were supplied\\n   --> api/no-word-or-boolean-entry.rs:1:62\\n    |\\n  1 | use mixer_absence::*;fn main(){let mut words=[0u64;16];let _=analyze_fixture_envelope_v1(&mut words,true);}\\n    |                                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^-----------------\\n    |                                                                                         ||          |\\n    |                                                                                         ||          expected `&mut File`, found `bool`\\n    |                                                                                         |expected `&mut File`, found `&mut [u64; 16]`\\n    |                                                                                         two arguments of type `&mut File` and `&mut File` are missing\\n    |\\n    = note: expected mutable reference `&mut File`\\n               found mutable reference `&mut [u64; 16]`\\nnote: function defined here\\n   --> source/library/envelope.rs:386:8\\n    |\\n386 | pub fn analyze_fixture_envelope_v1(stream: &mut File, profile_file: &mut File, context: &mut File, output: &mut File) -> Result<Fix...\\n    |        ^^^^^^^^^^^^^^^^^^^^^^^^^^^\\nhelp: provide the arguments\\n    |\\n  1 - use mixer_absence::*;fn main(){let mut words=[0u64;16];let _=analyze_fixture_envelope_v1(&mut words,true);}\\n  1 + use mixer_absence::*;fn main(){let mut words=[0u64;16];let _=analyze_fixture_envelope_v1(/* &mut File */, /* &mut File */, /* &mut File */, /* &mut File */);}\\n    |\\n\\n"}\n{"$message_type":"diagnostic","message":"aborting due to 1 previous error","code":null,"level":"error","spans":[],"children":[],"rendered":"error: aborting due to 1 previous error\\n\\n"}\n{"$message_type":"diagnostic","message":"For more information about this error, try `rustc --explain E0061`.","code":null,"level":"failure-note","spans":[],"children":[],"rendered":"For more information about this error, try `rustc --explain E0061`.\\n"}\n',
    'no-private-reply': '{"$message_type":"diagnostic","message":"unresolved import `mixer_absence::FixtureEnvelopeReplyV1`","code":{"code":"E0432","explanation":"An import was unresolved.\\n\\nErroneous code example:\\n\\n```compile_fail,E0432\\nuse something::Foo; // error: unresolved import `something::Foo`.\\n```\\n\\nIn Rust 2015, paths in `use` statements are relative to the crate root. To\\nimport items relative to the current and parent modules, use the `self::` and\\n`super::` prefixes, respectively.\\n\\nIn Rust 2018 or later, paths in `use` statements are relative to the current\\nmodule unless they begin with the name of a crate or a literal `crate::`, in\\nwhich case they start from the crate root. As in Rust 2015 code, the `self::`\\nand `super::` prefixes refer to the current and parent modules respectively.\\n\\nAlso verify that you didn\'t misspell the import name and that the import exists\\nin the module from where you tried to import it. Example:\\n\\n```\\nuse self::something::Foo; // Ok.\\n\\nmod something {\\n    pub struct Foo;\\n}\\n# fn main() {}\\n```\\n\\nIf you tried to use a module from an external crate and are using Rust 2015,\\nyou may have missed the `extern crate` declaration (which is usually placed in\\nthe crate root):\\n\\n```edition2015\\nextern crate core; // Required to use the `core` crate in Rust 2015.\\n\\nuse core::any;\\n# fn main() {}\\n```\\n\\nSince Rust 2018 the `extern crate` declaration is not required and\\nyou can instead just `use` it:\\n\\n```edition2018\\nuse core::any; // No extern crate required in Rust 2018.\\n# fn main() {}\\n```\\n"},"level":"error","spans":[{"file_name":"api/no-private-reply.rs","byte_start":19,"byte_end":41,"line_start":1,"line_end":1,"column_start":20,"column_end":42,"is_primary":false,"text":[{"text":"use mixer_absence::FixtureEnvelopeReplyV1;fn main(){}","highlight_start":20,"highlight_end":42}],"label":"no `FixtureEnvelopeReplyV1` in the root","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-private-reply.rs","byte_start":4,"byte_end":41,"line_start":1,"line_end":1,"column_start":5,"column_end":42,"is_primary":true,"text":[{"text":"use mixer_absence::FixtureEnvelopeReplyV1;fn main(){}","highlight_start":5,"highlight_end":42}],"label":null,"suggested_replacement":null,"suggestion_applicability":null,"expansion":null}],"children":[{"message":"a similar name exists in the module","code":null,"level":"help","spans":[{"file_name":"api/no-private-reply.rs","byte_start":19,"byte_end":41,"line_start":1,"line_end":1,"column_start":20,"column_end":42,"is_primary":true,"text":[{"text":"use mixer_absence::FixtureEnvelopeReplyV1;fn main(){}","highlight_start":20,"highlight_end":42}],"label":null,"suggested_replacement":"FixtureEnvelopeReasonV1","suggestion_applicability":"MaybeIncorrect","expansion":null}],"children":[],"rendered":null}],"rendered":"error[E0432]: unresolved import `mixer_absence::FixtureEnvelopeReplyV1`\\n --> api/no-private-reply.rs:1:5\\n  |\\n1 | use mixer_absence::FixtureEnvelopeReplyV1;fn main(){}\\n  |     ^^^^^^^^^^^^^^^----------------------\\n  |                    |\\n  |                    no `FixtureEnvelopeReplyV1` in the root\\n  |\\nhelp: a similar name exists in the module\\n  |\\n1 - use mixer_absence::FixtureEnvelopeReplyV1;fn main(){}\\n1 + use mixer_absence::FixtureEnvelopeReasonV1;fn main(){}\\n  |\\n\\n"}\n{"$message_type":"diagnostic","message":"aborting due to 1 previous error","code":null,"level":"error","spans":[],"children":[],"rendered":"error: aborting due to 1 previous error\\n\\n"}\n{"$message_type":"diagnostic","message":"For more information about this error, try `rustc --explain E0432`.","code":null,"level":"failure-note","spans":[],"children":[],"rendered":"For more information about this error, try `rustc --explain E0432`.\\n"}\n',
    'no-observation-constructor': '{"$message_type":"diagnostic","message":"fields `boundary`, `reason`, `observed_records`, `state`, `phase`, `mask`, `last_operation`, `active_operation`, `requested_function`, `pin_failure`, `terminal_failure`, `last_work`, `last_instructions`, `envelope_debit`, `full_replay_accepted` and `stored_prefix_validated` of struct `mixer_absence::FixtureEnvelopeObservationV1` are private","code":{"code":"E0451","explanation":"A struct constructor with private fields was invoked.\\n\\nErroneous code example:\\n\\n```compile_fail,E0451\\nmod bar {\\n    pub struct Foo {\\n        pub a: isize,\\n        b: isize,\\n    }\\n}\\n\\nlet f = bar::Foo{ a: 0, b: 0 }; // error: field `b` of struct `bar::Foo`\\n                                //        is private\\n```\\n\\nTo fix this error, please ensure that all the fields of the struct are public,\\nor implement a function for easy instantiation. Examples:\\n\\n```\\nmod bar {\\n    pub struct Foo {\\n        pub a: isize,\\n        pub b: isize, // we set `b` field public\\n    }\\n}\\n\\nlet f = bar::Foo{ a: 0, b: 0 }; // ok!\\n```\\n\\nOr:\\n\\n```\\nmod bar {\\n    pub struct Foo {\\n        pub a: isize,\\n        b: isize, // still private\\n    }\\n\\n    impl Foo {\\n        pub fn new() -> Foo { // we create a method to instantiate `Foo`\\n            Foo { a: 0, b: 0 }\\n        }\\n    }\\n}\\n\\nlet f = bar::Foo::new(); // ok!\\n```\\n"},"level":"error","spans":[{"file_name":"api/no-observation-constructor.rs","byte_start":66,"byte_end":74,"line_start":1,"line_end":1,"column_start":67,"column_end":75,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":67,"highlight_end":75}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":114,"byte_end":120,"line_start":1,"line_end":1,"column_start":115,"column_end":121,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":115,"highlight_end":121}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":166,"byte_end":182,"line_start":1,"line_end":1,"column_start":167,"column_end":183,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":167,"highlight_end":183}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":185,"byte_end":190,"line_start":1,"line_end":1,"column_start":186,"column_end":191,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":186,"highlight_end":191}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":193,"byte_end":198,"line_start":1,"line_end":1,"column_start":194,"column_end":199,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":194,"highlight_end":199}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":201,"byte_end":205,"line_start":1,"line_end":1,"column_start":202,"column_end":206,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":202,"highlight_end":206}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":208,"byte_end":222,"line_start":1,"line_end":1,"column_start":209,"column_end":223,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":209,"highlight_end":223}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":225,"byte_end":241,"line_start":1,"line_end":1,"column_start":226,"column_end":242,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":226,"highlight_end":242}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":244,"byte_end":262,"line_start":1,"line_end":1,"column_start":245,"column_end":263,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":245,"highlight_end":263}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":265,"byte_end":276,"line_start":1,"line_end":1,"column_start":266,"column_end":277,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":266,"highlight_end":277}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":279,"byte_end":295,"line_start":1,"line_end":1,"column_start":280,"column_end":296,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":280,"highlight_end":296}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":298,"byte_end":307,"line_start":1,"line_end":1,"column_start":299,"column_end":308,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":299,"highlight_end":308}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":310,"byte_end":327,"line_start":1,"line_end":1,"column_start":311,"column_end":328,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":311,"highlight_end":328}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":330,"byte_end":344,"line_start":1,"line_end":1,"column_start":331,"column_end":345,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":331,"highlight_end":345}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":347,"byte_end":367,"line_start":1,"line_end":1,"column_start":348,"column_end":368,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":348,"highlight_end":368}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null},{"file_name":"api/no-observation-constructor.rs","byte_start":370,"byte_end":393,"line_start":1,"line_end":1,"column_start":371,"column_end":394,"is_primary":true,"text":[{"text":"use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","highlight_start":371,"highlight_end":394}],"label":"private field","suggested_replacement":null,"suggestion_applicability":null,"expansion":null}],"children":[],"rendered":"error[E0451]: fields `boundary`, `reason`, `observed_records`, `state`, `phase`, `mask`, `last_operation`, `active_operation`, `requested_function`, `pin_failure`, `terminal_failure`, `last_work`, `last_instructions`, `envelope_debit`, `full_replay_accepted` and `stored_prefix_validated` of struct `mixer_absence::FixtureEnvelopeObservationV1` are private\\n --> api/no-observation-constructor.rs:1:67\\n  |\\n1 | ...V1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}\\n  |       ^^^^^^^^                                        ^^^^^^                                              ^^^^^^^^^^^^^^^^   ^^^^^   ^^^^^   ^^^^   ^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^   ^^^^^^^^^^^^^^^^   ^^^^^^^^^   ^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^ private field\\n  |       |                                               |                                                   |                  |       |       |      |                |                  |                    |             |                  |           |                   |                |\\n  |       |                                               |                                                   |                  |       |       |      |                |                  |                    |             |                  |           |                   |                private field\\n  |       |                                               |                                                   |                  |       |       |      |                |                  |                    |             |                  |           |                   private field\\n  |       |                                               |                                                   |                  |       |       |      |                |                  |                    |             |                  |           private field\\n  |       |                                               |                                                   |                  |       |       |      |                |                  |                    |             |                  private field\\n  |       |                                               |                                                   |                  |       |       |      |                |                  |                    |             private field\\n  |       |                                               |                                                   |                  |       |       |      |                |                  |                    private field\\n  |       |                                               |                                                   |                  |       |       |      |                |                  private field\\n  |       |                                               |                                                   |                  |       |       |      |                private field\\n  |       |                                               |                                                   |                  |       |       |      private field\\n  |       |                                               |                                                   |                  |       |       private field\\n  |       |                                               |                                                   |                  |       private field\\n  |       |                                               |                                                   |                  private field\\n  |       private field                                   private field                                       private field\\n\\n"}\n{"$message_type":"diagnostic","message":"aborting due to 1 previous error","code":null,"level":"error","spans":[],"children":[],"rendered":"error: aborting due to 1 previous error\\n\\n"}\n{"$message_type":"diagnostic","message":"For more information about this error, try `rustc --explain E0451`.","code":null,"level":"failure-note","spans":[],"children":[],"rendered":"For more information about this error, try `rustc --explain E0451`.\\n"}\n',
    'no-raw-serializer': '{"$message_type":"diagnostic","message":"no method named `to_bytes` found for reference `&mixer_absence::FixtureEnvelopeObservationV1` in the current scope","code":{"code":"E0599","explanation":"This error occurs when a method is used on a type which doesn\'t implement it:\\n\\nErroneous code example:\\n\\n```compile_fail,E0599\\nstruct Mouth;\\n\\nlet x = Mouth;\\nx.chocolate(); // error: no method named `chocolate` found for type `Mouth`\\n               //        in the current scope\\n```\\n\\nIn this case, you need to implement the `chocolate` method to fix the error:\\n\\n```\\nstruct Mouth;\\n\\nimpl Mouth {\\n    fn chocolate(&self) { // We implement the `chocolate` method here.\\n        println!(\\"Hmmm! I love chocolate!\\");\\n    }\\n}\\n\\nlet x = Mouth;\\nx.chocolate(); // ok!\\n```\\n"},"level":"error","spans":[{"file_name":"api/no-raw-serializer.rs","byte_start":71,"byte_end":79,"line_start":1,"line_end":1,"column_start":72,"column_end":80,"is_primary":true,"text":[{"text":"use mixer_absence::*;pub fn f(x:&FixtureEnvelopeObservationV1){let _=x.to_bytes();}fn main(){}","highlight_start":72,"highlight_end":80}],"label":"method not found in `&mixer_absence::FixtureEnvelopeObservationV1`","suggested_replacement":null,"suggestion_applicability":null,"expansion":null}],"children":[],"rendered":"error[E0599]: no method named `to_bytes` found for reference `&mixer_absence::FixtureEnvelopeObservationV1` in the current scope\\n --> api/no-raw-serializer.rs:1:72\\n  |\\n1 | use mixer_absence::*;pub fn f(x:&FixtureEnvelopeObservationV1){let _=x.to_bytes();}fn main(){}\\n  |                                                                        ^^^^^^^^ method not found in `&mixer_absence::FixtureEnvelopeObservationV1`\\n\\n"}\n{"$message_type":"diagnostic","message":"aborting due to 1 previous error","code":null,"level":"error","spans":[],"children":[],"rendered":"error: aborting due to 1 previous error\\n\\n"}\n{"$message_type":"diagnostic","message":"For more information about this error, try `rustc --explain E0599`.","code":null,"level":"failure-note","spans":[],"children":[],"rendered":"For more information about this error, try `rustc --explain E0599`.\\n"}\n',
}


class RunnerControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mixer-envelope-runner-controls-')
        self.base = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def raises(self, function, *args, **kwargs):
        with self.assertRaises((RuntimeError, OSError, ValueError)):
            function(*args, **kwargs)

    def compiler_identity(self, release='1.99.0'):
        return ('rustc ' + release + ' (b940084d7 2026-09-28)\n'
                'binary: rustc\ncommit-hash: b940084d7eb6a299eb4bfeb8e34901bc051e7ac4\n'
                'commit-date: 2026-09-28\nhost: aarch64-apple-darwin\nrelease: ' + release +
                '\nLLVM version: 23.1.1\n')

    def commands(self, suffix='commands', deadline=30):
        out = self.base / suffix
        out.mkdir()
        receipt = {'commands': []}
        return r.Commands(out, receipt, time.monotonic() + deadline)

    def ready_timeout(self, commands, name, code, popen=None):
        # Readiness belongs to this control, not the production timeout policy.
        # Wait for the real child to establish the condition being tested before
        # starting its short timed wait. A startup failure still fails the test,
        # and Commands.run's finally block reaps its exact owned process group.
        ready = self.base / (name + '.ready')
        popen = popen or subprocess.Popen

        def spawn(*args, **kwargs):
            process = popen(*args, **kwargs)
            wait = process.wait
            first_wait = True

            def wait_ready(timeout=None):
                nonlocal first_wait
                if first_wait:
                    first_wait = False
                    until = time.monotonic() + 10
                    while not ready.is_file():
                        if process.poll() is not None or time.monotonic() >= until:
                            self.fail('Owned timeout-control child did not become ready')
                        time.sleep(.01)
                return wait(timeout=timeout)

            process.wait = wait_ready
            return process

        with mock.patch.object(r.subprocess, 'Popen', spawn):
            self.raises(commands.run, name, [sys.executable, '-c', code, str(ready)],
                        cwd=self.base, timeout=.2)
        self.assertEqual(ready.read_text(), 'ready')

    def pack(self):
        p = self.base / 'pack'
        shutil.copytree(ROOT / r.PACK, p)
        return p

    def scratch(self):
        out = self.base / 'out'; out.mkdir()
        c = r.Commands(out, {'commands': []}, time.monotonic()+30)
        scratch = out/'scratch'; scratch.mkdir()
        marker = {'token': 'test-owned-marker'}
        (scratch/'ownership.json').write_text(json.dumps(marker))
        return out, scratch, r.scratch_identity(scratch), marker, c

    def test_closed_pack_and_exact_relative_augmentations(self):
        m = r.verify_pack(ROOT/r.PACK)
        self.assertEqual(m['member_count'], 86)
        self.assertEqual(m['selected_original_count'], 60)
        self.assertEqual(m['selected_original_bytes'], 7957311)
        out = self.base/'snapshot'; out.mkdir()
        copied = r.copy_pack(ROOT/r.PACK, out, m)
        self.assertEqual(r.verify_pack(copied), m)
        self.assertEqual(r.sha(copied/'source/library/envelope.rs'), r.ENVELOPE_SHA256)

    def test_manifest_and_unexpected_member_mutations_fail(self):
        p = self.pack()
        (p/'unexpected').write_bytes(b'extra')
        self.raises(r.verify_pack, p)
        (p/'unexpected').unlink()
        (p/'manifest.json').write_text('{}')
        self.raises(r.verify_pack, p)

    def test_missing_source_or_mutated_overlay_fail(self):
        p = self.pack()
        source = p/'source/producer/inputs/framing.rs'
        data = source.read_bytes(); source.write_bytes(data+b'\n')
        self.raises(r.verify_pack, p)
        self.raises(r.verify_sources, p)
        source.unlink()
        self.raises(r.verify_pack, p)

    def test_symlink_ancestor_and_member_nonregular_refusal(self):
        p = self.pack(); source = p/'api/no-clone.rs'
        source.unlink(); source.symlink_to(p/'api/no-copy.rs')
        self.raises(r.verify_pack, p)
        alias = self.base/'alias'; alias.symlink_to(p, target_is_directory=True)
        self.raises(r.verify_pack, alias)
        source.unlink(); os.mkfifo(source)
        self.raises(r.verify_pack, p)

    def test_member_traversal_alias_and_git_paths_refused(self):
        for name in ('', '.', '../x', 'a/../b', '/x', 'a//b', './x', 'a/./b', '.git/x', 'a\\b', 'x\x00'):
            self.raises(r.member_path, name)
        self.assertEqual(r.member_path('a/b'), Path('a/b'))

    def test_output_existing_symlink_and_historical_refused(self):
        existing = self.base/'existing'; existing.mkdir()
        self.raises(r.fresh_output, existing)
        alias = self.base/'alias'; alias.symlink_to(existing, target_is_directory=True)
        self.raises(r.fresh_output, alias/'new')
        self.raises(r.fresh_output, self.base/'a/../new')
        self.raises(r.fresh_output, ROOT/r.PACK/'new')
        self.raises(r.fresh_output, ROOT/'verification/swift-envelope-ci-contract/new')
        out = r.fresh_output(self.base/'fresh')
        self.assertTrue((out/'output-ownership.json').is_file())

    def test_checks_remain_active_under_python_optimization(self):
        code = "import importlib.util; s=importlib.util.spec_from_file_location('r',%r);r=importlib.util.module_from_spec(s);s.loader.exec_module(r);r.member_path('../escape')" % str(RUNNER)
        p = subprocess.run([sys.executable, '-O', '-B', '-c', code], capture_output=True, timeout=15)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn(b'Noncanonical member path', p.stderr)

    def test_exact_listing_and_execution_reject_empty_ignored_substitution(self):
        names = ['a', 'b']
        listing = 'a: test\nb: test\n\n2 tests, 0 benchmarks\n'
        self.assertEqual(r.verify_methods(listing, names), names)
        good = 'running 2 tests\ntest a ... hello\nok\ntest b ... ok\n\ntest result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.1s\n'
        self.assertEqual(r.verify_methods(good, names, True), names)
        for bad in ('', listing.replace('b:', 'c:'), listing.replace('b: test', 'a: test')):
            self.raises(r.verify_methods, bad, names)
        for bad in (good.replace('0 ignored', '1 ignored'), good.replace('test b', 'test c'), good.replace('2 passed', '1 passed'), good.replace('test b ... ok', 'test b ... ignored')):
            self.raises(r.verify_methods, bad, names, True)

    def test_independent_lint_allowance_is_fixed_and_cannot_leak(self):
        producer = r.test_compile_argv(Path('/selected/rustc'), 'producer', Path('/owned/producer'))
        independent = r.test_compile_argv(Path('/selected/rustc'), 'independent', Path('/owned/independent'))
        self.assertEqual(producer, [Path('/selected/rustc'), '--edition=2024', '-Dwarnings', '--test',
                                  'source/producer/independent_tests.rs', '-o', Path('/owned/producer')])
        self.assertEqual(independent, [Path('/selected/rustc'), '--edition=2024', '-Dwarnings', '-A',
                                     'non_snake_case', '--test', 'source/independent/source/analyzer.rs',
                                     '-o', Path('/owned/independent')])
        self.raises(r.test_compile_argv, Path('/selected/rustc'), 'api', Path('/owned/api'))
        self.raises(r.test_compile_argv, Path('/selected/rustc'), 'library', Path('/owned/library'))
        self.assertNotIn('-A', producer)

    def test_only_exact_selected_compiler_targets_without_override(self):
        historical = {'host': 'aarch64-apple-darwin', 'rust': '1.99.0'}
        for release in ('1.99.0', '1.98.1'):
            identity = r.rustc_identity(self.compiler_identity(release))
            selected = r.select_host_target(identity, historical)
            self.assertEqual(selected['actual_release'], release)
            self.assertEqual(selected['historical_layout_inventory_release'], '1.99.0')
            self.assertFalse(selected['other_target_qualification_inferred'])
        for identity in (None, {}, {'host':'x86_64-apple-darwin','release':'1.98.1'},
                         {'host':'aarch64-unknown-linux-gnu','release':'1.99.0'},
                         {'host':'aarch64-apple-darwin','release':'1.98.2'},
                         {'host':'aarch64-apple-darwin','release':'1.99'},
                         {'host':'aarch64-apple-darwin','release':['1.99.0']},
                         {'host':'aarch64-apple-darwin','release':'1.99.0-nightly'}):
            self.raises(r.select_host_target, identity, historical)

    def test_complete_layout_mapping_requires_fresh_complete_values(self):
        expected = json.loads((ROOT/r.PACK/'inventories/expected-host-layouts.json').read_bytes())
        text = 'CORRECTED_ACTUAL_COMPLETE_LAYOUTS='+json.dumps([x['bytes'] for x in expected['layouts']])
        observed = r.verify_layouts(text, expected)
        self.assertEqual(observed[-2:], [{'type':'std::fs::Metadata','bytes':144},{'type':'io::Result<std::fs::Metadata>','bytes':152}])
        self.raises(r.verify_layouts, text.replace('152', '151'), expected)
        self.raises(r.verify_layouts, text+'\n'+text, expected)

    def test_missing_and_failed_compiler_preserve_command_receipt(self):
        c = self.commands()
        self.raises(r.select_compiler, self.base/'missing-rustc', c, ROOT, c.out)
        self.raises(c.run, 'missing', [self.base/'missing-command'], cwd=self.base)
        self.assertIn('spawn_error', c.receipt['commands'][-1])
        self.raises(c.run, 'failed', [sys.executable,'-c','import sys;print("partial");sys.exit(7)'], cwd=self.base)
        self.assertEqual((c.out/'commands/failed.stdout').read_text(), 'partial\n')
        self.assertEqual(c.receipt['commands'][-1]['exit'], 7)
        self.assertTrue(c.receipt['commands'][-1]['owned_group_gone'])

    def test_explicit_launcher_queries_original_then_direct_sysroot(self):
        c = self.commands()
        toolchain = self.base/'toolchain'; (toolchain/'bin').mkdir(parents=True)
        compiler = toolchain/'bin/rustc'
        compiler.write_text("#!/bin/sh\ncat <<'MIXER_IDENTITY'\n" + self.compiler_identity() + "MIXER_IDENTITY\n")
        compiler.chmod(0o755)
        target = self.base/'rustup-init'
        target.write_text('#!/bin/sh\ncase "$0" in *rustc) test "$RUSTUP_AUTO_INSTALL" = 0 || exit 8; echo "'+str(toolchain)+'";; *) echo rustup-init; exit 9;; esac\n')
        target.chmod(0o755)
        launcher = self.base/'rustc'; launcher.symlink_to(target)
        with mock.patch.dict(os.environ, {'RUSTFLAGS':'malicious','RUSTC_WRAPPER':'malicious','DYLD_INSERT_LIBRARIES':'malicious'}):
            selected, identity = r.select_compiler(launcher, c, ROOT, c.out)
        self.assertEqual(selected, compiler)
        self.assertEqual(c.receipt['commands'][0]['argv'][0], str(launcher))
        self.assertEqual(c.receipt['commands'][1]['argv'][0], str(compiler))
        self.assertNotIn('RUSTFLAGS', c.receipt['commands'][0]['environment'])
        self.assertNotIn('DYLD_INSERT_LIBRARIES', c.receipt['commands'][0]['environment'])
        self.assertEqual(identity['identity']['release'], '1.99.0')

    def test_noncompiler_and_missing_sysroot_refused(self):
        self.raises(r.rustc_identity, 'rustup-init 1.99.0\n')
        self.raises(r.rustc_identity, 'rustc 1.99.0\nbinary: rustc\nrelease: 1.99.1\nhost: x\n')
        c = self.commands(); launcher = self.base/'rustc'
        launcher.write_text('#!/bin/sh\necho /nonexistent-mixer-toolchain\n'); launcher.chmod(0o755)
        self.raises(r.select_compiler, launcher, c, ROOT, c.out)

    def test_timeout_reaps_owned_group_retains_partial_logs(self):
        c = self.commands()
        # Deliberately exceed the short timed wait during startup. The parent
        # reaps its first child, flushes output and signals readiness before the
        # runner's real timed wait and process-group termination are exercised.
        code = 'import subprocess,sys,time;from pathlib import Path;time.sleep(.3);p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(.05)"]);p.wait();print("partial-before-timeout",flush=True);Path(sys.argv[1]).write_text("ready");time.sleep(20)'
        self.ready_timeout(c, 'timeout', code)
        row = c.receipt['commands'][-1]
        self.assertTrue(row['timed_out']); self.assertTrue(row['child_returned']); self.assertTrue(row['owned_group_gone'])
        self.assertIn('partial-before-timeout', (c.out/'commands/timeout.stdout').read_text())

    def test_timeout_kills_all_owned_group_members_and_returns_children(self):
        c = self.commands()
        member_ready = self.base / 'group-member.ready'
        children = []
        popen = subprocess.Popen

        def cleanup():
            for child in children:
                if child.poll() is None:
                    child.kill()
            for child in reversed(children):
                child.wait(timeout=5)

        self.addCleanup(cleanup)

        def spawn_group(*args, **kwargs):
            # Group signaling depends on membership, not ancestry. Keep both
            # real children directly waitable instead of making an orphan whose
            # disappearance depends on the host's init reaping it. The runner
            # must still request isolation; only this test factory substitutes
            # a fresh group in our session so the second owned child can join.
            self.assertIs(kwargs.pop('start_new_session'), True)
            process = popen(*args, **kwargs, process_group=0)
            children.append(process)
            member = popen([sys.executable, '-c',
                            'import json,os,sys,time;from pathlib import Path;'
                            'Path(sys.argv[1]).write_text(json.dumps({"pid":os.getpid(),"pgid":os.getpgrp()}));'
                            'time.sleep(20)', str(member_ready)],
                           cwd=kwargs['cwd'], env=kwargs['env'],
                           stdout=kwargs['stdout'], stderr=kwargs['stderr'],
                           process_group=process.pid)
            children.append(member)
            wait = process.wait

            def wait_group(timeout=None):
                result = wait(timeout=timeout)
                member.wait(timeout=5)
                return result

            process.wait = wait_group
            return process

        code = ('import sys,time;from pathlib import Path;'
                'member=Path(' + repr(str(member_ready)) + ');'
                '\nwhile not member.is_file(): time.sleep(.01)\n'
                'print("group-member-started",flush=True);'
                'Path(sys.argv[1]).write_text("ready");time.sleep(20)')
        self.ready_timeout(c, 'group', code, popen=spawn_group)
        row = c.receipt['commands'][-1]
        self.assertTrue(row['timed_out']); self.assertTrue(row['child_returned']); self.assertTrue(row['owned_group_gone'])
        self.assertEqual(row['pid'], row['owned_pgid'])
        self.assertEqual(row['timeout_seconds'], .2)
        self.assertTrue(row['owned_group_killed'])
        self.assertEqual([child.returncode for child in children], [-signal.SIGKILL, -signal.SIGKILL])
        self.assertEqual(json.loads(member_ready.read_text()), {'pid': children[1].pid, 'pgid': row['pid']})
        self.assertIsNone(c.active)
        self.assertIn('group-member-started', (c.out/'commands/group.stdout').read_text())

    def test_unconfirmed_group_disappearance_is_refused_after_clean_child_exit(self):
        c = self.commands()
        killpg, monotonic = os.killpg, time.monotonic
        offset = 0

        def group_still_visible(pgid, sig):
            if sig:
                return killpg(pgid, sig)
            # Deterministically model a killed but still visible orphan group.
            return None

        def advance_poll(_):
            nonlocal offset
            offset += 6

        clock = mock.Mock(monotonic=lambda: monotonic() + offset, sleep=advance_poll)
        with mock.patch.object(r.os, 'killpg', group_still_visible), mock.patch.object(r, 'time', clock):
            with self.assertRaisesRegex(RuntimeError, 'Command failed: unconfirmed'):
                c.run('unconfirmed', [sys.executable, '-c', 'pass'], cwd=self.base)
        row = c.receipt['commands'][-1]
        self.assertEqual(row['exit'], 0)
        self.assertTrue(row['child_returned'])
        self.assertFalse(row['timed_out'])
        self.assertFalse(row['owned_group_gone'])
        self.assertTrue(row['descendants_outlived_direct_child'])
        self.assertIsNone(c.active)

    def test_overall_deadline_refuses_spawn(self):
        c = self.commands(deadline=-1)
        self.raises(c.run, 'expired', [sys.executable,'--version'], cwd=self.base)
        self.assertEqual(c.receipt['commands'], [])

    def diagnostic(self, name):
        source = self.base/'api'/(name+'.rs'); source.parent.mkdir(exist_ok=True)
        source.write_bytes((ROOT/r.PACK/'api'/(name+'.rs')).read_bytes())
        target = self.base/'executable'
        diagnostics = [json.loads(line) for line in ACTUAL_DIAGNOSTICS[name].splitlines()]
        diag = next(d for d in diagnostics if d.get('level') == 'error' and d.get('code'))
        row = {'exit':1,'timed_out':False,'child_returned':True,'owned_group_gone':True}
        return source,target,diag,row

    def test_complete_compiler_identity_and_all_required_fields_unique(self):
        valid = self.compiler_identity()
        actual = r.rustc_identity(valid)
        self.assertEqual(actual, {'binary':'rustc', 'release':'1.99.0', 'host':'aarch64-apple-darwin',
            'commit_hash':'b940084d7eb6a299eb4bfeb8e34901bc051e7ac4', 'commit_date':'2026-09-28',
            'llvm_version':'23.1.1'})
        for line in valid.splitlines()[1:]:
            key, value = line.split(': ', 1)
            for replacement in ('', key+': ', line+'\n'+line, line+'\n'+key+': contradictory'):
                with self.subTest(field=key, replacement=replacement):
                    self.raises(r.rustc_identity, valid.replace(line+'\n', replacement+'\n' if replacement else ''))
        for line in ('malformed', 'host:aarch64-apple-darwin', 'extra: value', ' host: value', ''):
            self.raises(r.rustc_identity, valid+line+'\n')

    def test_compiler_identity_hash_date_header_coherence(self):
        valid = self.compiler_identity()
        substitutions = [
            ('rustc 1.99.0', 'rustc 1.98.1'), ('(b940084d7 ', '(a940084d7 '),
            ('(b940084d7 2026-09-28)', '(b940084d7 2026-09-27)'),
            ('b940084d7eb6a299eb4bfeb8e34901bc051e7ac4', 'b940084d7'),
            ('b940084d7eb6a299eb4bfeb8e34901bc051e7ac4', 'g940084d7eb6a299eb4bfeb8e34901bc051e7ac4'),
            ('b940084d7eb6a299eb4bfeb8e34901bc051e7ac4', 'b940084d7eb6a299eb4bfeb8e34901bc051e7ac40'),
            ('2026-09-28', '2026-02-30'), ('2026-09-28', '2026-9-28'),
            ('LLVM version: 23.1.1', 'LLVM version: invalid'), ('binary: rustc', 'binary: rustup-init')]
        for before, after in substitutions:
            with self.subTest(after=after):
                self.raises(r.rustc_identity, valid.replace(before, after))
        self.raises(r.rustc_identity, valid.replace('commit-date: 2026-09-28', 'commit-date: 2024-02-29'))
        self.raises(r.rustc_identity, valid.replace('release: 1.99.0', 'release: 1.99.0 '))
        self.assertEqual(r.rustc_identity(valid.replace('2026-09-28', '2024-02-29'))['commit_date'], '2024-02-29')

    def test_negative_api_accepts_all_eight_unmodified_actual_diagnostics_and_23_spans(self):
        count = 0
        for name, stderr in ACTUAL_DIAGNOSTICS.items():
            source,target,diag,row = self.diagnostic(name)
            count += len(r.verify_negative(name,stderr,source,target,row))
        self.assertEqual(count, 23)

    def test_negative_api_requires_intended_code_target_and_primary_probe_span(self):
        for name in ACTUAL_DIAGNOSTICS:
            source,target,diag,row = self.diagnostic(name)
            self.assertTrue(r.verify_negative(name,json.dumps(diag),source,target,row))
            for change in ({'code':{'code':'E0463'}}, {'message':'missing dependency'}, {'spans':[]},
                           {'spans':[{'file_name':'api/different.rs','is_primary':True,'byte_start':0,'byte_end':1}]}):
                bad = copy.deepcopy(diag); bad.update(change)
                self.raises(r.verify_negative,name,json.dumps(bad),source,target,row)
            target.write_text('unexpected executable')
            self.raises(r.verify_negative,name,json.dumps(diag),source,target,row); target.unlink()

    def test_negative_all_eight_unrelated_leading_shifted_and_mixed_primary_spans_fail(self):
        for name in ACTUAL_DIAGNOSTICS:
            source,target,diag,row = self.diagnostic(name)
            primary = next(s for s in diag['spans'] if s['is_primary'])
            for start,end in ((0,1),(1,2),(primary['byte_start']+1,primary['byte_end']),(-1,1),(0,9999)):
                bad = copy.deepcopy(diag)
                for span in bad['spans']:
                    if span['is_primary']:
                        span.update(byte_start=start,byte_end=end)
                with self.subTest(probe=name, start=start, end=end):
                    self.raises(r.verify_negative,name,json.dumps(bad),source,target,row)
            bad = copy.deepcopy(diag)
            wrong = copy.deepcopy(primary); wrong.update(byte_start=0,byte_end=1)
            bad['spans'].append(wrong)
            self.raises(r.verify_negative,name,json.dumps(bad),source,target,row)
            wrongdiag=copy.deepcopy(diag);wrongdiag['spans']=[wrong]
            self.raises(r.verify_negative,name,json.dumps(diag)+'\n'+json.dumps(wrongdiag),source,target,row)
            source.write_bytes(source.read_bytes()+b'\n')
            self.raises(r.verify_negative,name,json.dumps(diag),source,target,row)

    def test_negative_every_coded_error_requires_intended_message_and_correct_primary(self):
        name='no-clone';source,target,diag,row=self.diagnostic(name)
        for change in ({'code':{'code':'E0463'}}, {'message':'unrelated error'},
                       {'message':'unrelated Clone FixtureEnvelopeObservationV1 problem'}, {'spans':[]},
                       {'spans':[{'file_name':'api/no-copy.rs','is_primary':True,'byte_start':58,'byte_end':86}]}):
            wrong=copy.deepcopy(diag);wrong.update(change)
            self.raises(r.verify_negative,name,json.dumps(diag)+'\n'+json.dumps(wrong),source,target,row)
        self.raises(r.verify_negative,name,json.dumps(diag)+'\n'+json.dumps(diag),source,target,row)
        wrong=copy.deepcopy(diag);wrong['code']={'code':'E0463'}
        outer=copy.deepcopy(diag);outer['children']=[wrong]
        self.raises(r.verify_negative,name,json.dumps(outer),source,target,row)
        name='no-observation-constructor';source,target,diag,row=self.diagnostic(name)
        diag['spans'].pop()
        self.raises(r.verify_negative,name,json.dumps(diag),source,target,row)
        name='no-word-or-boolean-entry';source,target,diag,row=self.diagnostic(name)
        diag['message']='unrelated 42 argument problem'
        self.raises(r.verify_negative,name,json.dumps(diag),source,target,row)

    def test_negative_json_duplicate_keys_at_every_relevant_level_fail(self):
        name='no-clone';source,target,diag,row=self.diagnostic(name)
        text=json.dumps(diag)
        for key, old in (('level','"error"'), ('message',json.dumps(diag['message'])),
                         ('code','"E0277"'), ('file_name','"api/no-clone.rs"'),
                         ('is_primary','true'), ('byte_start','58'), ('byte_end','86')):
            token=json.dumps(key)+': '+old
            self.assertIn(token,text)
            for value in (old,'null'):
                bad=text.replace(token,token+', '+json.dumps(key)+': '+value,1)
                self.raises(r.verify_negative,name,bad,source,target,row)
        # Duplicate structured keys are also refused, including an identical object.
        self.raises(r.verify_negative,name,text[:-1]+', "spans": '+json.dumps(diag['spans'])+'}',source,target,row)
        self.raises(r.verify_negative,name,text[:-1]+', "code": '+json.dumps(diag['code'])+'}',source,target,row)

    def test_negative_json_types_boolean_offsets_and_primary_flags_fail(self):
        name='no-clone';source,target,diag,row=self.diagnostic(name)
        for key in ('byte_start','byte_end'):
            for value in (True,False,None,58.0,'58',[],{}):
                bad=copy.deepcopy(diag);bad['spans'][0][key]=value
                self.raises(r.verify_negative,name,json.dumps(bad),source,target,row)
        for value in (1,0,'true',None):
            bad=copy.deepcopy(diag);bad['spans'][0]['is_primary']=value
            self.raises(r.verify_negative,name,json.dumps(bad),source,target,row)
        for key, value in (('message',None),('level',[]),('code','E0277'),('code',{}),('spans',{}),('spans',[None]),('children',{}),('children',[None])):
            bad=copy.deepcopy(diag);bad[key]=value
            self.raises(r.verify_negative,name,json.dumps(bad),source,target,row)
        for text in ('[]','null','true','42','"diagnostic"','not JSON', '{"level": NaN}'):
            self.raises(r.verify_negative,name,text,source,target,row)

    def test_negative_api_abnormal_failure_and_extra_error_never_pass(self):
        name='no-clone'; source,target,diag,row = self.diagnostic(name)
        for change in ({'exit':-9},{'exit':0},{'exit':101},{'timed_out':True},{'child_returned':False},
                       {'owned_group_gone':False},{'descendants_outlived_direct_child':True}):
            bad=dict(row);bad.update(change)
            self.raises(r.verify_negative,name,json.dumps(diag),source,target,bad)
        self.raises(r.verify_negative,name,json.dumps(diag)+'\n'+json.dumps({'level':'error','message':'compiler crash'}),source,target,row)
        self.raises(r.verify_negative,name,'not JSON',source,target,row)

    def test_postflight_pack_failure_does_not_suppress_tool_and_partial_snapshot_checks(self):
        root = self.base/'root'; (root/r.PACK).mkdir(parents=True)
        (root/r.PACK/'manifest.json').write_text('{}')
        out = self.base/'out'; (out/'pack').mkdir(parents=True)
        (out/'pack/partial.rs').write_text('partial retained snapshot')
        runner = out/'runner.py'; runner.write_text('runner bytes')
        receipt = {'errors': [], 'runner': {'sha256': r.sha(runner)}, 'python': {
            'path': sys.executable, 'resolved_path': str(Path(sys.executable).resolve()),
            'sha256': r.sha(Path(sys.executable).resolve())}}
        result = r.postflight_checks(root,out,runner,receipt,None,time.monotonic()+10)
        self.assertFalse(result['pack']['passed']); self.assertFalse(result['snapshot']['passed'])
        self.assertTrue(result['runner']['passed']); self.assertTrue(result['python']['passed'])
        self.assertEqual(result['snapshot-observed']['observed'][0]['path'], 'partial.rs')
        self.assertEqual(len(receipt['errors']), 2)

    def test_postflight_detects_retargeted_compiler_launcher(self):
        out = self.base/'out'; out.mkdir()
        tool = out/'rustc'; tool.write_bytes(b'compiler')
        launcher = out/'launcher'; launcher.symlink_to(tool)
        other = out/'different'; other.write_bytes(b'different compiler')
        runner = out/'runner.py'; runner.write_bytes(b'runner')
        receipt = {'errors': [], 'runner': {'sha256':r.sha(runner)}, 'python': {
            'path':sys.executable,'resolved_path':str(Path(sys.executable).resolve()),
            'sha256':r.sha(Path(sys.executable).resolve())}, 'rustc': {
            'launcher':str(launcher),'launcher_target':str(tool),
            'launcher_sha256':r.sha(tool),'sha256':r.sha(tool)}}
        launcher.unlink();launcher.symlink_to(other)
        result=r.postflight_checks(ROOT,out,runner,receipt,tool,time.monotonic()+10)
        self.assertTrue(result['compiler']['passed']);self.assertFalse(result['launcher']['passed'])

    def test_retains_independent_reports_input_and_product_hashes(self):
        out,scratch,identity,marker,c = self.scratch()
        (scratch/'independent-files').mkdir()
        (scratch/'independent-files/report').write_bytes(b'actual File report\x00')
        (scratch/'independent-files/input').write_bytes(b'input')
        (scratch/'producer-tests').write_bytes(b'compiler-product')
        result = r.preserve_and_cleanup(out,scratch,identity,marker,{'producer-tests'},c)
        self.assertTrue(result['removed']); self.assertFalse(scratch.exists())
        self.assertEqual((out/'retained/independent-files/report').read_bytes(),b'actual File report\x00')
        self.assertIn('producer-tests',result['compiler_products'])
        self.assertFalse((out/'retained/producer-tests').exists())

    def test_sparse_failure_lossless_streaming_compression(self):
        out,scratch,identity,marker,c = self.scratch()
        source=scratch/'sparse-input'
        with source.open('wb') as f:
            f.write(b'first');f.seek(20*1024*1024);f.write(b'last')
        expected=r.sha(source)
        result=r.preserve_and_cleanup(out,scratch,identity,marker,set(),c)
        record=result['test_files']['sparse-input']
        self.assertEqual(record['encoding'],'gzip');self.assertEqual(record['original_sha256'],expected)
        self.assertEqual(record['original_bytes'],20*1024*1024+4)
        self.assertLess(record['bytes'],100000)
        with gzip.open(out/record['path'],'rb') as f:
            self.assertEqual(f.read(5),b'first');f.seek(20*1024*1024);self.assertEqual(f.read(),b'last')

    def test_changed_scratch_inode_marker_symlink_special_or_live_child_preserved(self):
        out,scratch,identity,marker,c = self.scratch()
        self.raises(r.preserve_and_cleanup,out,scratch,[identity[0],identity[1]+1,identity[2]],marker,set(),c)
        self.assertTrue(scratch.exists())
        (scratch/'ownership.json').write_text('{}')
        self.raises(r.preserve_and_cleanup,out,scratch,identity,marker,set(),c)
        (scratch/'ownership.json').write_text(json.dumps(marker))
        (scratch/'link').symlink_to(scratch/'ownership.json')
        self.raises(r.preserve_and_cleanup,out,scratch,identity,marker,set(),c);(scratch/'link').unlink()
        os.mkfifo(scratch/'pipe')
        self.raises(r.preserve_and_cleanup,out,scratch,identity,marker,set(),c);(scratch/'pipe').unlink()
        c.receipt['commands'].append({'pid':123,'owned_group_gone':False})
        self.raises(r.preserve_and_cleanup,out,scratch,identity,marker,set(),c)
        self.assertTrue(scratch.exists())

    def test_retention_interruption_keeps_source_recoverable(self):
        out,scratch,identity,marker,c = self.scratch()
        (scratch/'input').write_bytes(b'recover-me')
        with mock.patch.object(r.shutil,'copyfileobj',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                r.preserve_and_cleanup(out,scratch,identity,marker,set(),c)
        self.assertEqual((scratch/'input').read_bytes(),b'recover-me')


if __name__ == '__main__':
    unittest.main()
