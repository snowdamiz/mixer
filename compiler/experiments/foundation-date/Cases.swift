func epochSeconds(_ index: Int32) -> Double {
    switch index {
    case 0: -0.5
    case 1: 0
    case 2: 978_307_200
    case 3: 1_704_241_800.25
    default: preconditionFailure()
    }
}

func presentationCase(_ index: Int32) -> (seconds: Double, locale: Int32, offset: Int32) {
    switch index {
    case 0: (725_761_800, 0, 0)       // 2024-01-01 00:30 UTC, en_US
    case 1: (725_761_800, 1, 0)       // same instant, fr_FR
    case 2: (725_761_800, 0, -28_800) // same instant, en_US, UTC-08:00
    case 3: (731_346_300, 0, 0)       // 2024-03-05 15:45 UTC, en_US
    default: preconditionFailure()
    }
}
