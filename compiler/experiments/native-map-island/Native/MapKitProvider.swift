import MapKit
import Observation
import SwiftUI

@MainActor
@Observable
final class MapKitProvider {
    private(set) var surface: MapKitSurface?

    func makeSurface() -> any ProjectSiteMapSurface {
        let surface = MapKitSurface()
        self.surface = surface
        return surface
    }
}

@MainActor
@Observable
final class MapKitSurface: ProjectSiteMapSurface {
    let token = UUID()
    private(set) var placement: ProjectSiteMapPlacement?
    private(set) var applications = 0

    func apply(_ placement: ProjectSiteMapPlacement) {
        self.placement = placement
        applications += 1
    }
}

struct ProjectSiteMapView: View {
    let surface: MapKitSurface
    let placement: ProjectSiteMapPlacement
    @State private var viewToken = UUID()
    @State private var cameraPosition: MapCameraPosition
    @State private var observedCenter: CLLocationCoordinate2D?

    init(surface: MapKitSurface, placement: ProjectSiteMapPlacement) {
        self.surface = surface
        self.placement = placement
        _cameraPosition = State(initialValue: Self.camera(at: placement.coordinate))
    }

    var body: some View {
        VStack(spacing: 6) {
            Map(position: $cameraPosition, interactionModes: []) {
                Annotation("Project site pin", coordinate: placement.coordinate, anchor: .bottom) {
                    Image(systemName: "mappin.circle.fill")
                        .font(.largeTitle)
                        .foregroundStyle(.white, .red)
                        .accessibilityLabel("Project site pin")
                        .accessibilityValue(coordinateText(placement.coordinate))
                        .accessibilityIdentifier("site-pin")
                }
            }
            .mapStyle(placement.style == .standard ? .standard : .imagery)
            .onMapCameraChange(frequency: .continuous) { context in
                observedCenter = context.camera.centerCoordinate
            }
            .onChange(of: surface.applications) {
                cameraPosition = Self.camera(at: placement.coordinate)
            }
            .frame(height: 220)

            // The camera value comes from MapKit's callback. SwiftUI state supplies the mount token.
            Text(observedCenter.map(coordinateText) ?? "Waiting for map camera")
                .accessibilityIdentifier("map-camera-center")
            Text("Map surface")
                .accessibilityValue("\(surface.token.uuidString)/\(viewToken.uuidString)/\(placement.identity.id)/\(placement.identity.generation)")
                .accessibilityIdentifier("map-surface-identity")
            Text("\(placement.style.rawValue) · \(surface.applications)")
                .accessibilityIdentifier("map-accepted-state")
        }
    }

    private static func camera(at coordinate: CLLocationCoordinate2D) -> MapCameraPosition {
        .camera(MapCamera(centerCoordinate: coordinate, distance: 2_000, heading: 0, pitch: 0))
    }

    private func coordinateText(_ coordinate: CLLocationCoordinate2D) -> String {
        String(format: "%.6f,%.6f", locale: Locale(identifier: "en_US_POSIX"),
               coordinate.latitude, coordinate.longitude)
    }
}
