#if MIXER_LOCAL_STORE_FIXTURE
import Foundation

package enum LocalStoreFixture {
    private static let environment = ProcessInfo.processInfo.environment
    static let token = "l05-local-fixture-token"
    private static let port = environment["MIXER_LOCAL_STORE_FIXTURE_PORT"].flatMap(UInt16.init)

    package static func validate() throws {
        guard let port, port > 0,
              ["MIXER_ASC_BEARER_TOKEN", "MIXER_PLAY_BEARER_TOKEN"].allSatisfy({
                  let value = environment[$0] ?? ""
                  return value.isEmpty || value == token
              }) else {
            throw MixerFailure("store.fixture-configuration", "Fixture mode requires a loopback port and accepts only the fixed fixture token.")
        }
    }

    static func url(for providerURL: URL) throws -> URL {
        try loopback(URLComponents(url: providerURL, resolvingAgainstBaseURL: false)!)
    }

    static func submissionURL(target: String) throws -> URL {
        var components = URLComponents()
        components.path = "/mixer-store-fixture/v1/submissions" + target
        return try loopback(components)
    }

    private static func loopback(_ original: URLComponents) throws -> URL {
        try validate()
        var components = original
        components.scheme = "http"
        components.host = "127.0.0.1"
        components.port = port.map(Int.init)
        return components.url!
    }

    static func configure(_ configuration: URLSessionConfiguration) {
        configuration.connectionProxyDictionary = [
            "HTTPEnable": 0, "HTTPSEnable": 0, "SOCKSEnable": 0, "ProxyAutoConfigEnable": 0,
            "ProxyAutoDiscoveryEnable": 0
        ]
    }
}
#endif
