import CryptoKit
import Foundation

// Synthetic host verification only. Product encryption never accepts an IV.
func bytes(_ count: Int, _ value: UInt8) -> Data { Data(repeating: value, count: count) }
func token(_ value: UInt8) -> Data {
    Data(bytes(32, value).base64EncodedString().replacingOccurrences(of: "=", with: "")
        .replacingOccurrences(of: "+", with: "-").replacingOccurrences(of: "/", with: "_").utf8)
}
func text(_ value: String) -> Data { Data(value.utf8) }
func u64(_ value: UInt64) -> Data {
    var value = value.bigEndian
    return withUnsafeBytes(of: &value) { Data($0) }
}
func lp(_ value: Data) -> Data {
    var length = UInt32(value.count).bigEndian
    return withUnsafeBytes(of: &length) { Data($0) } + value
}
func hex(_ value: Substring) -> Data {
    precondition(value.count.isMultiple(of: 2))
    let chars = Array(value)
    return Data(stride(from: 0, to: chars.count, by: 2).map { UInt8(String(chars[$0...$0+1]), radix: 16)! })
}
let csrf = token(11)
let generation = token(13)
let prefix = [Data([1]), text("session-key-v1")]
let session = [bytes(16, 1), bytes(32, 2), Data(SHA256.hash(data: csrf)), u64(1), u64(2), generation,
               u64(3), bytes(32, 4), text("human-main"), u64(7)]
let attempt = [bytes(32, 5), bytes(16, 1), bytes(32, 2), u64(1), u64(2), generation, bytes(32, 4),
               text("human-main"), u64(7), text("https://id.example.test"), text("console-client"),
               text("https://console.example.test/auth/callback"), u64(123456)]
let lines = try String(contentsOfFile: CommandLine.arguments[1], encoding: .utf8).split(separator: "\n")
precondition(lines.count == 3)
for line in lines {
    let parts = line.split(separator: "|", omittingEmptySubsequences: false)
    precondition(parts.count == 6)
    let purpose = String(parts[0])
    let kind: UInt8 = purpose == "preauth" ? 1 : (purpose == "active" ? 2 : 3)
    let fields: [Data]
    if purpose == "attempt" {
        fields = prefix + [Data([kind])] + attempt
    } else {
        let linkage = kind == 1 ? [Data([0])] : [Data([1]), text("person-1"), text("browser_") + generation,
                       text("external-jti-1"), u64(5)]
        fields = prefix + [Data([kind])] + session + linkage
    }
    let domain = purpose == "attempt" ? "mixer.browser.attempt.v1\0" : "mixer.browser.vault.v1\0"
    let aad = text(domain) + fields.reduce(Data()) { $0 + lp($1) }
    precondition(aad == hex(parts[3]))
    let payload = Data([kind]) + (kind == 3 ? lp(token(12)) : lp(csrf)) + (kind == 2 ? lp(text("header.payload.signature")) : Data())
    let key = SymmetricKey(data: hex(parts[1]))
    let nonce = try AES.GCM.Nonce(data: hex(parts[2]))
    let sealed = try AES.GCM.SealedBox(nonce: nonce, ciphertext: hex(parts[4]), tag: hex(parts[5]))
    let recovered = try AES.GCM.open(sealed, using: key, authenticating: aad)
    precondition(recovered == payload)
    let repeated = try AES.GCM.seal(payload, using: key, nonce: nonce, authenticating: aad)
    precondition(repeated.ciphertext == sealed.ciphertext && repeated.tag == sealed.tag)
    print("CryptoKit independently derived AAD, opened and reproduced " + purpose + " envelope")
}
let zeroKey = SymmetricKey(data: bytes(32, 0))
let known = try AES.GCM.seal(bytes(16, 0), using: zeroKey, nonce: AES.GCM.Nonce(data: bytes(12, 0)))
precondition(known.ciphertext == hex("cea7403d4d606b6e074ec5d3baf39d18"))
precondition(known.tag == hex("d0d1c8a799996bf0265b98b5d48ab919"))
print("CryptoKit AES-256-GCM known-answer vector passed")

// NIST GCM-AES256 Example #4, official AES_GCM.pdf, pages 25-26.
let nist_key = hex("feffe9928665731c6d6a8f9467308308feffe9928665731c6d6a8f9467308308")
let nist_iv = hex("cafebabefacedbaddecaf888")
let nist_aad = hex("3ad77bb40d7a3660a89ecaf32466ef97f5d3d58503b9699de785895a96fdbaaf43b1cd7f598ece23881b00e3ed0306887b0c785e27e8ad3f8223207104725dd4")
let nist_plaintext = hex("d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a721c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b391aafd255")
let nist_ciphertext = hex("522dc1f099567d07f47f37a32a84427d643a8cdcbfe5c0c97598a2bd2555d1aa8cb08e48590dbb3da7b08b1056828838c5f61e6393ba7a0abcc9f662898015ad")
let nist_tag = hex("c06d76f31930fef37acae23ed465ae62")
let nistSealed = try AES.GCM.seal(nist_plaintext, using: SymmetricKey(data: nist_key), nonce: AES.GCM.Nonce(data: nist_iv), authenticating: nist_aad)
precondition(nistSealed.ciphertext == nist_ciphertext && nistSealed.tag == nist_tag)
let nistOpened = try AES.GCM.open(nistSealed, using: SymmetricKey(data: nist_key), authenticating: nist_aad)
precondition(nistOpened == nist_plaintext)
print("CryptoKit official NIST AES-256-GCM example 4 passed")
