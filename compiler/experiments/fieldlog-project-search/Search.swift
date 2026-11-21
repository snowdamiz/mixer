import Foundation

@main
struct ProjectSearchReplay {
  static func main() throws {
    var workspace = Workspace()
    for (title, site, day) in [
      ("Inspection", "Cafe\u{0301} Annex", 1.0),
      ("Remote", "South Pump", 2.0),
      ("Café Service", "North Dock", 3.0),
      ("الورشة", "الميناء", 4.0),
    ] {
      try workspace.createProject(
        title: title, site: site, now: Date(timeIntervalSince1970: day * 86_400))
    }
    let queries = [" \ncAfE\t", "NORTH D", "الميناء", "لا وجود", "\n \t", "Annex"]
    let before = workspace
    let encoder = JSONEncoder()
    encoder.outputFormatting = .sortedKeys
    let stored = try encoder.encode(workspace)
    let reopened = try JSONDecoder().decode(Workspace.self, from: stored)
    let keys = Dictionary(uniqueKeysWithValues: workspace.projects.map { ($0.id, $0.title) })
    for argument in CommandLine.arguments.dropFirst() {
      guard let index = Int(argument), queries.indices.contains(index) else {
        throw FieldLogError.validation("Unknown query case.")
      }
      let query = queries[index]
      let matches = workspace.matchingProjects(query).map(\.id)
      guard matches == reopened.matchingProjects(query).map(\.id),
        matches.allSatisfy({ keys[$0] != nil })
      else {
        throw FieldLogError.validation("Search result changed after reopening the workspace.")
      }
      print(matches.compactMap { keys[$0] }.joined(separator: "|"))
    }
    guard workspace == before, try encoder.encode(workspace) == stored else {
      throw FieldLogError.validation("Search changed workspace state.")
    }
  }
}
