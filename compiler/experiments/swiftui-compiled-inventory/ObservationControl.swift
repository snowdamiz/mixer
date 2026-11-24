import Observation

@Observable
final class InventoryObservation {
    var record: TaskRecord?
}

func observeInventoryRecord(_ value: InventoryObservation) -> (any Observable, TaskRecord?) {
    (value, value.record)
}
