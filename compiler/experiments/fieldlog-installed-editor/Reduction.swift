// Foundation-free successful subset of the pinned TaskEditor reducer.
extension TitleState {
    mutating func changeTitle(_ title: String) {
        guard !saving && !saved else { return }
        self.title = title
        failure = nil
    }

    mutating func beginSave() -> SaveTaskEffect {
        saving = true
        failure = nil
        return SaveTaskEffect(title: title, responsible: responsible)
    }

    mutating func finishSave() {
        guard saving else { return }
        saving = false
        saved = true
        failure = nil
    }
}
