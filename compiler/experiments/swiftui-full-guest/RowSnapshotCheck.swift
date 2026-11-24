#if os(WASI)
import FoundationEssentials
#else
import Foundation
#endif

@main
enum RowSnapshotCheck {
    @MainActor
    static func main() async {
        let workspace = Workspace()
        let list = FieldLogList(workspace: workspace)
        let empty = list.frame().rows
        await list.body.appear()
        let loaded = list.frame().rows
        precondition(empty.count == 0 && loaded.count == 1_000)
        let sites = ["North yard", "Pump station", "Loading bay"]
        for step in 0..<1_000 {
            let index = (step * 527) % 1_000
            let title = "Inspection \(index)"
            let row = loaded[index]
            precondition(row.title == "\(title) · \(sites[index % sites.count])")
            row.action()
            let id = UUID(uuid: (0, 0, 0, 0, 0, 0, 0x40, 0, 0x80, 0, 0, 0, 0, 0,
                                 UInt8(index >> 8), UInt8(truncatingIfNeeded: index)))
            precondition(workspace.selected == id && workspace.draft == title)
        }

        let oldRow = loaded[527]
        oldRow.action()
        workspace.draft = "Pompé inspection 東京"
        workspace.save()
        let updated = list.frame().rows
        precondition(updated.count == loaded.count)
        precondition(loaded[527].title == "Inspection 527 · Loading bay")
        precondition(updated[527].title == "Pompé inspection 東京 · Loading bay")
        oldRow.action()
        precondition(workspace.draft == "Pompé inspection 東京")
        print("verified 1000 row titles and actions, plus snapshot and action behavior after Save")
    }
}
