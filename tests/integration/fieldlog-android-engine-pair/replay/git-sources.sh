# Source from prepare.sh after creating the private scratch and sanitizing Git.
cache=$scratch/mixer.git
borrowed=$scratch/mixer-borrowed-view.git
git init -q --bare --template= "$cache"
git init -q --bare --template= "$borrowed"
git -C "$cache" remote add origin "$public"
git -C "$cache" config remote.origin.promisor true
git -C "$cache" config remote.origin.partialclonefilter blob:none
git -C "$cache" config http.lowSpeedLimit 1
git -C "$cache" config http.lowSpeedTime 30

# Treat the caller's checkout solely as a read-only source of objects. The
# isolated view has no remotes, local config from the caller, or writable path
# back to the borrowed object store. Skip stores that redirect to other stores.
borrowed_objects=$(GIT_NO_LAZY_FETCH=1 git -C "$repo" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) ||
    borrowed_objects=
if [[ -n "$borrowed_objects" ]]; then
    borrowed_objects=$borrowed_objects/objects
    if [[ ! -d "$borrowed_objects" || -L "$borrowed_objects" ||
          -e "$borrowed_objects/info/alternates" || -L "$borrowed_objects/info/alternates" ||
          "$borrowed_objects" = *:* ]]; then
        borrowed_objects=
    fi
fi

pinned_output() {
    local output=$1 revision=$2 command=$3
    shift 3
    if [[ -n "$borrowed_objects" ]] &&
        GIT_NO_LAZY_FETCH=1 GIT_ALTERNATE_OBJECT_DIRECTORIES="$borrowed_objects" \
            git -C "$borrowed" "$command" "$revision" "$@" > "$output" 2>/dev/null; then
        return
    fi
    local commit=${revision%%:*}
    if ! GIT_NO_LAZY_FETCH=1 git -C "$cache" cat-file -e "$commit^{commit}" 2>/dev/null; then
        git -C "$cache" fetch --quiet --no-tags --filter=blob:none --depth=1 origin "$commit" || return
    fi
    git -C "$cache" "$command" "$revision" "$@" > "$output"
}

archive() {
    local dest=$1 rev=$2
    shift 2
    # Do not extract partial output from a borrowed store with a missing blob.
    local staged=$scratch/pinned-source.tar
    pinned_output "$staged" "$rev" archive "$@" || return
    mkdir -p "$dest"
    tar -xf "$staged" -C "$dest"
    rm "$staged"
}
