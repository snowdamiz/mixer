# Source with sources set to an absolute directory produced by fetch.sh.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0
export GIT_ALLOW_PROTOCOL=file GIT_NO_LAZY_FETCH=1 GIT_NO_REPLACE_OBJECTS=1
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0="url.$sources/swift-crypto.git.insteadOf"
export GIT_CONFIG_VALUE_0=https://github.com/apple/swift-crypto.git
export GIT_CONFIG_KEY_1="url.$sources/swift-asn1.git.insteadOf"
export GIT_CONFIG_VALUE_1=https://github.com/apple/swift-asn1.git
