import Foundation

public func presentationReadback(_ index: Int32) -> String {
    let input = presentationCase(index)
    let locale = Locale(identifier: input.locale == 0 ? "en_US" : "fr_FR")
    let zone = TimeZone(secondsFromGMT: Int(input.offset))!
    var style: Date.FormatStyle = .dateTime.month(.abbreviated).day().locale(locale)
    style.timeZone = zone
    style.calendar = Calendar(identifier: .gregorian)
    return style.format(Date(timeIntervalSinceReferenceDate: input.seconds))
}
