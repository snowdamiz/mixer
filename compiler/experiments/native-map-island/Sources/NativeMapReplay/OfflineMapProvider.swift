@MainActor
final class OfflineMapProvider {
    private(set) var surfaces: [OfflineMapSurface] = []

    func makeSurface() -> any ProjectSiteMapSurface {
        let surface = OfflineMapSurface()
        surfaces.append(surface)
        return surface
    }
}

@MainActor
final class OfflineMapSurface: ProjectSiteMapSurface {
    private(set) var placements: [ProjectSiteMapPlacement] = []

    func apply(_ placement: ProjectSiteMapPlacement) {
        placements.append(placement)
    }
}
