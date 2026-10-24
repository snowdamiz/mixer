// Fault injection compiled only in the independent adversarial test overlay.
#[cfg(test)]
impl RuntimeControl {
    pub(crate) fn review_replace_memory_pages_limit(&mut self,limit:u32)->u32 {
        std::mem::replace(&mut self.budget.memory_pages,limit)
    }
    pub(crate) fn review_refund_corruption(&mut self,fault:u8,restore:Option<(u64,usize,usize,usize)>)->(u64,usize,usize,usize) {
        let saved=(self.owner,self.reservations.state.current,self.reservations.combined.current,self.reservations.live_tickets);
        if let Some((owner,state,combined,tickets))=restore {
            self.owner=owner;self.reservations.state.current=state;self.reservations.combined.current=combined;self.reservations.live_tickets=tickets;
        } else {
            match fault {0=>self.owner=0,1=>self.reservations.state.current=0,2=>self.reservations.combined.current=0,3=>self.reservations.live_tickets=0,_=>panic!("bounded corruption selector")}
        }
        saved
    }
}
