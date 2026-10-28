impl<'a> ReservationV1<'a> {
    pub(super) fn dispatch_v1<T>(self, action: impl FnOnce() -> T)
        -> PrepaidOwnedV1<'a, T>
    {
        // If action unwinds, no release runs. Work and storage stay charged.
        let owned = action();
        PrepaidOwnedV1 { owned: Some(owned), reservation: Some(self) }
    }
}
