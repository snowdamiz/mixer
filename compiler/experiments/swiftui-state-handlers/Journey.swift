struct Checkpoint {
    let action: String?
    let labels: [String]

    init(_ action: String?, _ values: String, _ row1: String, _ row2: String, _ branch: String) {
        self.action = action
        labels = ["Values " + values, "Row " + row1, "Row " + row2, branch]
    }

    static let journey = [
        Self(nil,                     "1 / 10", "1 = 0", "2 = 0", "Branch = 0"),
        Self("Bump first",            "2 / 10", "1 = 0", "2 = 0", "Branch = 0"),
        Self("Reverse reads",         "10 / 2", "1 = 0", "2 = 0", "Branch = 0"),
        Self("Write captured binding","20 / 2", "1 = 0", "2 = 0", "Branch = 0"),
        Self("Bump row 1",            "20 / 2", "1 = 1", "2 = 0", "Branch = 0"),
        Self("Bump row 2",            "20 / 2", "1 = 1", "2 = 1", "Branch = 0"),
        Self("Bump row 2",            "20 / 2", "1 = 1", "2 = 2", "Branch = 0"),
        Self("Move rows",             "20 / 2", "2 = 2", "1 = 1", "Branch = 0"),
        Self("Bump row 1",            "20 / 2", "2 = 2", "1 = 2", "Branch = 0"),
        Self("Bump branch",           "20 / 2", "2 = 2", "1 = 2", "Branch = 1"),
        Self("Toggle branch",         "20",     "2 = 2", "1 = 2", "Branch hidden"),
        Self("Toggle branch",         "20 / 2", "2 = 2", "1 = 2", "Branch = 0"),
        Self("Reverse reads",         "2 / 20", "2 = 2", "1 = 2", "Branch = 0"),
        Self("Write captured binding","2 / 30", "2 = 2", "1 = 2", "Branch = 0"),
    ]
}
