use std::mem::{size_of,align_of};
use std::path::{Path,PathBuf};
use std::ffi::OsString;
use std::fs::{File,OpenOptions};
#[allow(dead_code)]
struct PathConstructionValues {
    format_return:String,name:String,
    environment_result:Option<OsString>,environment_value:OsString,from_argument:OsString,
    from_local:PathBuf,from_return:PathBuf,join_return:PathBuf,path:PathBuf,caller_return:PathBuf,
    path_borrows:[&'static Path;4],os_borrows:[&'static std::ffi::OsStr;2],
    scalar_arguments:[usize;8],checked:Option<u64>,
}
fn main(){
    println!("REVIEW_LAYOUT path_buf={} string={} os_string={} option_os_string={} path_ref={} path_buf_align={} file={} file_result={} open_options={} path_construction={}",size_of::<PathBuf>(),size_of::<String>(),size_of::<OsString>(),size_of::<Option<OsString>>(),size_of::<&Path>(),align_of::<PathBuf>(),size_of::<File>(),size_of::<std::io::Result<File>>(),size_of::<OpenOptions>(),size_of::<PathConstructionValues>());
    assert_eq!(size_of::<PathBuf>(),3*size_of::<usize>());
    assert_eq!(size_of::<String>(),3*size_of::<usize>());
    assert_eq!(size_of::<OsString>(),3*size_of::<usize>());
    let name=format!("completion-9.bin");let environment=std::env::var_os("TMPDIR").unwrap();let environment_capacity=environment.capacity();
    let from=PathBuf::from(environment);let from_capacity=from.capacity();let path=from.join(&name);
    println!("REVIEW_PATH_CAP name={} environment={} from={} join={}",name.capacity(),environment_capacity,from_capacity,path.capacity());
    assert!(name.capacity()<=128&&environment_capacity<=512&&from_capacity<=512&&path.capacity()<=512);
    for extension in ["initial.json","final.json","original.txt","details.txt","semantic.txt"]{let p=path.with_extension(extension);println!("REVIEW_EXTENSION {extension}={}",p.capacity());assert!(p.capacity()<=512);}
}
