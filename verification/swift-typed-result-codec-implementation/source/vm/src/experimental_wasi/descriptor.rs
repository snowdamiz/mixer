//! Exact Preview1 vocabulary of the retained Swift reactor. Resolution is not admission.
use crate::Type;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WasiFunction {
    ArgsGet,
    ArgsSizesGet,
    EnvironGet,
    EnvironSizesGet,
    ClockResGet,
    ClockTimeGet,
    FdClose,
    FdFdstatGet,
    FdFdstatSetFlags,
    FdFilestatGet,
    FdFilestatSetSize,
    FdFilestatSetTimes,
    FdPread,
    FdPrestatGet,
    FdPrestatDirName,
    FdRead,
    FdReaddir,
    FdSeek,
    FdSync,
    FdTell,
    FdWrite,
    PathCreateDirectory,
    PathFilestatGet,
    PathFilestatSetTimes,
    PathLink,
    PathOpen,
    PathReadlink,
    PathRemoveDirectory,
    PathRename,
    PathSymlink,
    PathUnlinkFile,
    PollOneoff,
    ProcExit,
    RandomGet,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ResolveError {
    Module,
    Name,
    Signature,
}

impl WasiFunction {
    pub const ALL: [Self; 34] = [
        Self::ArgsGet,
        Self::ArgsSizesGet,
        Self::EnvironGet,
        Self::EnvironSizesGet,
        Self::ClockResGet,
        Self::ClockTimeGet,
        Self::FdClose,
        Self::FdFdstatGet,
        Self::FdFdstatSetFlags,
        Self::FdFilestatGet,
        Self::FdFilestatSetSize,
        Self::FdFilestatSetTimes,
        Self::FdPread,
        Self::FdPrestatGet,
        Self::FdPrestatDirName,
        Self::FdRead,
        Self::FdReaddir,
        Self::FdSeek,
        Self::FdSync,
        Self::FdTell,
        Self::FdWrite,
        Self::PathCreateDirectory,
        Self::PathFilestatGet,
        Self::PathFilestatSetTimes,
        Self::PathLink,
        Self::PathOpen,
        Self::PathReadlink,
        Self::PathRemoveDirectory,
        Self::PathRename,
        Self::PathSymlink,
        Self::PathUnlinkFile,
        Self::PollOneoff,
        Self::ProcExit,
        Self::RandomGet,
    ];

    pub fn name(self) -> &'static [u8] {
        match self {
            Self::ArgsGet => b"args_get",
            Self::ArgsSizesGet => b"args_sizes_get",
            Self::EnvironGet => b"environ_get",
            Self::EnvironSizesGet => b"environ_sizes_get",
            Self::ClockResGet => b"clock_res_get",
            Self::ClockTimeGet => b"clock_time_get",
            Self::FdClose => b"fd_close",
            Self::FdFdstatGet => b"fd_fdstat_get",
            Self::FdFdstatSetFlags => b"fd_fdstat_set_flags",
            Self::FdFilestatGet => b"fd_filestat_get",
            Self::FdFilestatSetSize => b"fd_filestat_set_size",
            Self::FdFilestatSetTimes => b"fd_filestat_set_times",
            Self::FdPread => b"fd_pread",
            Self::FdPrestatGet => b"fd_prestat_get",
            Self::FdPrestatDirName => b"fd_prestat_dir_name",
            Self::FdRead => b"fd_read",
            Self::FdReaddir => b"fd_readdir",
            Self::FdSeek => b"fd_seek",
            Self::FdSync => b"fd_sync",
            Self::FdTell => b"fd_tell",
            Self::FdWrite => b"fd_write",
            Self::PathCreateDirectory => b"path_create_directory",
            Self::PathFilestatGet => b"path_filestat_get",
            Self::PathFilestatSetTimes => b"path_filestat_set_times",
            Self::PathLink => b"path_link",
            Self::PathOpen => b"path_open",
            Self::PathReadlink => b"path_readlink",
            Self::PathRemoveDirectory => b"path_remove_directory",
            Self::PathRename => b"path_rename",
            Self::PathSymlink => b"path_symlink",
            Self::PathUnlinkFile => b"path_unlink_file",
            Self::PollOneoff => b"poll_oneoff",
            Self::ProcExit => b"proc_exit",
            Self::RandomGet => b"random_get",
        }
    }

    pub fn parameters(self) -> &'static [Type] {
        use Type::{I32 as I, I64 as L};
        match self {
            Self::FdClose | Self::FdSync | Self::ProcExit => &[I],
            Self::ClockTimeGet => &[I, L, I],
            Self::FdFilestatSetSize => &[I, L],
            Self::FdFilestatSetTimes => &[I, L, L, I],
            Self::FdPread | Self::FdReaddir => &[I, I, I, L, I],
            Self::FdSeek => &[I, L, I, I],
            Self::FdPrestatDirName
            | Self::PathCreateDirectory
            | Self::PathRemoveDirectory
            | Self::PathUnlinkFile => &[I, I, I],
            Self::FdRead | Self::FdWrite | Self::PollOneoff => &[I, I, I, I],
            Self::PathFilestatGet | Self::PathSymlink => &[I, I, I, I, I],
            Self::PathFilestatSetTimes => &[I, I, I, I, L, L, I],
            Self::PathLink => &[I, I, I, I, I, I, I],
            Self::PathOpen => &[I, I, I, I, I, L, L, I, I],
            Self::PathReadlink | Self::PathRename => &[I, I, I, I, I, I],
            Self::ArgsGet
            | Self::ArgsSizesGet
            | Self::EnvironGet
            | Self::EnvironSizesGet
            | Self::ClockResGet
            | Self::FdFdstatGet
            | Self::FdFdstatSetFlags
            | Self::FdFilestatGet
            | Self::FdPrestatGet
            | Self::FdTell
            | Self::RandomGet => &[I, I],
        }
    }

    pub fn results(self) -> &'static [Type] {
        if self == Self::ProcExit {
            &[]
        } else {
            &[Type::I32]
        }
    }

    pub fn resolve(
        module: &[u8],
        name: &[u8],
        parameters: &[Type],
        results: &[Type],
    ) -> Result<Self, ResolveError> {
        if module != b"wasi_snapshot_preview1" {
            return Err(ResolveError::Module);
        }
        let function = Self::ALL
            .into_iter()
            .find(|f| f.name() == name)
            .ok_or(ResolveError::Name)?;
        if function.parameters() != parameters || function.results() != results {
            return Err(ResolveError::Signature);
        }
        Ok(function)
    }
}
