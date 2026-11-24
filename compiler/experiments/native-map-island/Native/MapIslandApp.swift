import Foundation
import MixerUI
import Observation
import SwiftUI

@MainActor
@Observable
private final class MapScenario {
    enum Action: String, CaseIterable, Identifiable {
        case update = "Apply signed update"
        case unknown = "Try unknown island"
        case missing = "Try missing grant"
        case mismatch = "Try wrong schema"

        var id: Self { self }
    }

    let provider = MapKitProvider()
    private let signer = SignedFixture()
    private let host: MapIslandHost
    private let digest: String
    private let sourceRevision: String
    private(set) var status = "Initial site accepted"

    init(sourceRevision: String) throws {
        self.sourceRevision = sourceRevision
        let registry = try InstalledMapRegistry(makeSurface: provider.makeSurface)
        digest = registry.schemaSHA256
        host = try MapIslandHost(scope: SignedFixture.scope, roots: [signer.root],
                                 identity: UINodeIdentity(id: "project-site-map", generation: 1),
                                 registry: registry)
        let initial = PlacementFixture(schema: digest, slot: .aboveDetails,
                                       latitude: "37.774900", longitude: "-122.419400", style: .standard)
        try apply(initial, grants: [ProjectSiteMapSchema.id: digest])
    }

    func run(_ action: Action) {
        do {
            var fixture = PlacementFixture(schema: digest)
            var grants = [ProjectSiteMapSchema.id: digest]
            if action != .update {
                // A denied placement would visibly move the pin, camera, and slot if it leaked.
                fixture.latitude = "51.500700"
                fixture.longitude = "-0.124600"
                fixture.slot = .aboveDetails
                fixture.style = .standard
            }
            switch action {
            case .update: break
            case .unknown:
                fixture.islandID = "fieldlog.other-map"
                grants = [fixture.islandID: digest]
            case .missing:
                grants = [:]
            case .mismatch:
                fixture.schema = String(repeating: "0", count: 64)
            }
            try apply(fixture, grants: grants)
            status = action == .update ? "Signed update accepted" : "Unexpected acceptance"
        } catch MapPlacementError.unknownIsland {
            status = "Refused unknown island"
        } catch MapPlacementError.ungrantedIsland {
            status = "Refused missing grant"
        } catch MapPlacementError.schemaMismatch {
            status = "Refused schema mismatch"
        } catch {
            status = "Unexpected fixture failure: \(error)"
        }
    }

    private func apply(_ fixture: PlacementFixture, grants: [String: String]) throws {
        let bytes = try fixture.encode(grants: grants)
        let manifest = try signer.sign(bytes, for: host.installedRuntime, sourceRevision: sourceRevision)
        try host.apply(signedManifest: manifest, payload: bytes, now: SignedFixture.now)
    }
}

private struct MapScenarioView: View {
    let scenario: MapScenario

    var body: some View {
        VStack(spacing: 12) {
            if let surface = scenario.provider.surface, let placement = surface.placement {
                if placement.slot == .belowDetails { details }
                ProjectSiteMapView(surface: surface, placement: placement)
                    .id(placement.identity)
                if placement.slot == .aboveDetails { details }
            }

            Text(scenario.status)
                .accessibilityIdentifier("release-result")

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())]) {
                ForEach(MapScenario.Action.allCases) { action in
                    Button(action.rawValue) { scenario.run(action) }
                        .buttonStyle(.bordered)
                }
            }
        }
        .padding()
    }

    private var details: some View {
        Text("Project site details")
            .font(.headline)
            .accessibilityIdentifier("site-details")
    }
}

@main
struct MapIslandApp: App {
    @State private var fixture = Result {
        let revision = Bundle.main.object(forInfoDictionaryKey: "GC3SourceRevision") as? String ?? ""
        return try MapScenario(sourceRevision: revision)
    }

    var body: some Scene {
        WindowGroup {
            switch fixture {
            case .success(let scenario):
                MapScenarioView(scenario: scenario)
            case .failure(let error):
                Text("Fixture setup failed: \(error)")
            }
        }
    }
}
